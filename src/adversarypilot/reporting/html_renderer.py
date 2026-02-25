"""HTML report renderer for attack graph visualization."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from adversarypilot.models.campaign import Campaign
from adversarypilot.models.enums import Surface
from adversarypilot.models.report import DefenderReport
from adversarypilot.reporting.html_template import HTML_TEMPLATE
from adversarypilot.taxonomy.registry import TechniqueRegistry


class HtmlReportRenderer:
    """Renders defender reports as self-contained HTML with attack graph visualization."""

    def __init__(self, registry: TechniqueRegistry | None = None) -> None:
        self.registry = registry or TechniqueRegistry()
        if not self.registry.get_all():
            self.registry.load_catalog()

    def render(
        self,
        report: DefenderReport,
        campaign: Campaign,
        output_path: Path | str | None = None,
    ) -> str:
        """Render report as self-contained HTML.

        Args:
            report: Defender report to render
            campaign: Campaign with attempt/evaluation data
            output_path: Optional path to write HTML file

        Returns:
            HTML string
        """
        data = self._build_data_payload(report, campaign)
        html = HTML_TEMPLATE.replace("{{DATA_JSON}}", json.dumps(data, indent=2, default=str))

        if output_path:
            Path(output_path).write_text(html)

        return html

    def _build_data_payload(
        self, report: DefenderReport, campaign: Campaign
    ) -> dict:
        """Build comprehensive data payload for visualization."""
        techniques_data = self._build_techniques(report, campaign)
        graph_data = self._build_graph(techniques_data)
        layers_data = self._build_layers(report)
        heatmap_data = self._build_heatmap(campaign)
        atlas_data = self._build_atlas_mapping(techniques_data)
        statistics = self._build_statistics(report, campaign, techniques_data)

        sensitivity_data = self._build_sensitivity(campaign)
        posterior_evolution = self._build_posterior_evolution(campaign)

        return {
            "report": {
                "title": f"Defender Report: {report.target_profile.name}",
                "campaign_id": report.campaign_id,
                "target_name": report.target_profile.name,
                "target_type": report.target_profile.target_type.value,
                "generated_at": report.generated_at.isoformat(),
                "primary_weak_layer": report.primary_weak_layer.value if report.primary_weak_layer else None,
                "secondary_weak_layers": [s.value for s in report.secondary_weak_layers],
                "overall_risk_summary": report.overall_risk_summary,
                "comparability_warnings": report.comparability_warnings,
                "next_recommended_tests": report.next_recommended_tests,
            },
            "graph": graph_data,
            "layers": layers_data,
            "heatmap": heatmap_data,
            "techniques": techniques_data,
            "atlas_mapping": atlas_data,
            "statistics": statistics,
            "sensitivity": sensitivity_data,
            "posterior_evolution": posterior_evolution,
            "coverage": {
                "atlas_coverage": report.atlas_coverage,
                "gaps": report.coverage_gaps,
            },
            "compliance": self._build_compliance(report),
        }

    def _build_techniques(self, report: DefenderReport, campaign: Campaign) -> list[dict]:
        """Build detailed technique list with outcomes."""
        techniques = []
        seen_ids = set()

        for assessment in report.layer_assessments:
            for tech_id in assessment.techniques_tested:
                if tech_id in seen_ids:
                    continue
                seen_ids.add(tech_id)

                technique = self.registry.get(tech_id)
                if not technique:
                    continue

                evaluation = self._find_evaluation(campaign, tech_id)

                tech_data = {
                    "id": tech_id,
                    "name": technique.name,
                    "description": technique.description,
                    "domain": technique.domain.value,
                    "surface": technique.surface.value,
                    "phase": technique.phase.value,
                    "access_required": technique.access_required.value,
                    "goals_supported": [g.value for g in technique.goals_supported],
                    "target_types": [t.value for t in technique.target_types],
                    "atlas_refs": [ref.atlas_id for ref in technique.atlas_refs],
                    "atlas_details": [
                        {"id": ref.atlas_id, "name": ref.atlas_name, "tactic": ref.tactic}
                        for ref in technique.atlas_refs
                    ],
                    "base_cost": technique.base_cost,
                    "stealth_profile": technique.stealth_profile.value,
                    "execution_mode": technique.execution_mode.value,
                    "tool_support": technique.tool_support,
                    "tags": technique.tags,
                    "success": evaluation.success if evaluation else None,
                    "score": evaluation.score if evaluation else None,
                    "confidence": evaluation.confidence if evaluation else None,
                    "evidence_quality": evaluation.evidence_quality if evaluation else None,
                    "judge_type": evaluation.judge_type.value if evaluation else None,
                    "layer": assessment.layer.value,
                    "confidence_interval": evaluation.confidence_interval if evaluation and hasattr(evaluation, 'confidence_interval') else None,
                }
                techniques.append(tech_data)

        return techniques

    def _build_graph(self, techniques: list[dict]) -> dict:
        """Build graph nodes and edges from techniques."""
        nodes = []
        for t in techniques:
            nodes.append({
                "id": t["id"],
                "label": t["name"],
                "domain": t["domain"],
                "surface": t["surface"],
                "layer": t["layer"],
                "phase": t["phase"],
                "success": t["success"],
                "score": t["score"],
                "atlas_refs": t["atlas_refs"],
            })

        # Build edges: connect techniques that share ATLAS refs
        # Use directed edges based on phase ordering for meaningful flow
        phase_order = {"recon": 0, "probe": 1, "exploit": 2, "persistence": 3, "evaluation": 4}
        edges = []
        edge_id = 0
        edge_set = set()

        for i, n1 in enumerate(nodes):
            for j, n2 in enumerate(nodes):
                if i >= j:
                    continue
                shared_atlas = set(n1["atlas_refs"]) & set(n2["atlas_refs"])
                if shared_atlas:
                    # Direct edge from earlier phase to later phase
                    p1 = phase_order.get(n1.get("phase", ""), 2)
                    p2 = phase_order.get(n2.get("phase", ""), 2)
                    src = n1["id"] if p1 <= p2 else n2["id"]
                    tgt = n2["id"] if p1 <= p2 else n1["id"]
                    key = f"{src}:{tgt}"
                    if key not in edge_set:
                        edge_set.add(key)
                        edges.append({
                            "id": f"edge-{edge_id}",
                            "source": src,
                            "target": tgt,
                            "atlas_id": sorted(shared_atlas)[0],
                        })
                        edge_id += 1

        return {"nodes": nodes, "edges": edges}

    def _build_layers(self, report: DefenderReport) -> list[dict]:
        """Build layer assessment data."""
        layers = []
        for assessment in report.layer_assessments:
            layers.append({
                "layer": assessment.layer.value,
                "risk_score": assessment.risk_score,
                "is_primary_weakness": assessment.is_primary_weakness,
                "success_rate": assessment.evidence.smoothed_success_rate,
                "confidence_interval": list(assessment.evidence.confidence_interval),
                "techniques_tested": len(assessment.techniques_tested),
                "technique_ids": assessment.techniques_tested,
                "evidence_quality": assessment.evidence.evidence_quality,
                "success_count": assessment.evidence.success_count,
                "total_attempts": assessment.evidence.total_attempts,
                "caveats": assessment.evidence.caveats,
                "recommendations": assessment.recommendations,
                "is_insufficient_evidence": assessment.is_insufficient_evidence,
            })
        return layers

    def _build_heatmap(self, campaign: Campaign) -> dict:
        """Build surface x goal heatmap matrix."""
        # Group evaluations by (surface, goal)
        tech_map = {}
        for t in self.registry.get_all():
            tech_map[t.id] = t

        # Count successes per (surface, goal)
        matrix: dict[str, dict[str, dict]] = defaultdict(lambda: defaultdict(lambda: {"count": 0, "successes": 0, "rate": 0}))
        surfaces_seen = set()
        goals_seen = set()

        for evaluation in campaign.state.evaluations:
            tech_id = evaluation.comparability.technique_id
            technique = tech_map.get(tech_id)
            if not technique:
                continue

            surface = technique.surface.value
            surfaces_seen.add(surface)

            for goal in technique.goals_supported:
                goal_val = goal.value
                goals_seen.add(goal_val)
                cell = matrix[surface][goal_val]
                cell["count"] += 1
                if evaluation.success is True:
                    cell["successes"] += 1

        # Calculate rates
        for surface in matrix:
            for goal in matrix[surface]:
                cell = matrix[surface][goal]
                if cell["count"] > 0:
                    cell["rate"] = cell["successes"] / cell["count"]

        # Include all surfaces for completeness
        all_surfaces = [s.value for s in Surface]
        all_goals = sorted(goals_seen) if goals_seen else []

        return {
            "surfaces": all_surfaces,
            "goals": all_goals,
            "matrix": {s: dict(matrix[s]) for s in all_surfaces},
        }

    def _build_atlas_mapping(self, techniques: list[dict]) -> dict:
        """Build ATLAS ID to techniques mapping."""
        atlas_map: dict[str, dict] = {}

        for t in techniques:
            for detail in t.get("atlas_details", []):
                atlas_id = detail["id"]
                if atlas_id not in atlas_map:
                    atlas_map[atlas_id] = {
                        "name": detail.get("name", ""),
                        "tactic": detail.get("tactic", ""),
                        "techniques": [],
                    }
                atlas_map[atlas_id]["techniques"].append({
                    "id": t["id"],
                    "name": t["name"],
                    "success": t["success"],
                    "score": t["score"],
                })

        return atlas_map

    def _build_statistics(
        self, report: DefenderReport, campaign: Campaign, techniques: list[dict]
    ) -> dict:
        """Build comprehensive statistics."""
        total_attempts = len(campaign.state.evaluations)
        success_count = sum(1 for e in campaign.state.evaluations if e.success is True)
        failure_count = sum(1 for e in campaign.state.evaluations if e.success is False)
        inconclusive_count = sum(1 for e in campaign.state.evaluations if e.success is None)

        tested_techniques = [t for t in techniques if t["success"] is not None]
        layers_tested = len([l for l in report.layer_assessments if len(l.techniques_tested) > 0])
        max_risk = max((l.risk_score for l in report.layer_assessments), default=0)

        # Per-domain stats
        per_domain: dict[str, dict] = defaultdict(lambda: {"total": 0, "successes": 0, "techniques": 0})
        for t in techniques:
            d = per_domain[t["domain"]]
            d["techniques"] += 1
            if t["success"] is not None:
                d["total"] += 1
                if t["success"]:
                    d["successes"] += 1
        for d in per_domain.values():
            d["success_rate"] = f"{d['successes']}/{d['total']} ({d['successes']/max(d['total'],1)*100:.0f}%)"

        # Per-surface stats
        per_surface: dict[str, dict] = defaultdict(lambda: {"total": 0, "successes": 0, "techniques": 0})
        for t in techniques:
            s = per_surface[t["surface"]]
            s["techniques"] += 1
            if t["success"] is not None:
                s["total"] += 1
                if t["success"]:
                    s["successes"] += 1
        for s in per_surface.values():
            s["success_rate"] = f"{s['successes']}/{s['total']} ({s['successes']/max(s['total'],1)*100:.0f}%)"

        # Per-phase stats
        per_phase: dict[str, dict] = {}
        for t in techniques:
            phase = t.get("phase", "unknown")
            if phase not in per_phase:
                per_phase[phase] = {"total": 0, "success": 0, "rate": 0}
            if t["success"] is not None:
                per_phase[phase]["total"] += 1
                if t["success"]:
                    per_phase[phase]["success"] += 1
        for p in per_phase.values():
            p["rate"] = p["success"] / max(p["total"], 1)

        # Coverage analysis
        all_catalog = self.registry.get_all()
        coverage = {
            "catalog_size": len(all_catalog),
            "techniques_tested": len(tested_techniques),
            "coverage_rate": f"{len(tested_techniques)/max(len(all_catalog),1)*100:.1f}%",
            "layers_tested": f"{layers_tested}/6",
            "unique_atlas_ids": len(set(
                ref for t in techniques for ref in t.get("atlas_refs", [])
            )),
        }

        # Adaptive planning info
        adaptive_stats = {}
        if campaign.metadata.get("adaptive"):
            adaptive_stats = {
                "mode": "Adaptive (Thompson Sampling)",
                "campaign_seed": campaign.metadata.get("campaign_seed", "N/A"),
                "posterior_techniques": len(campaign.posterior_state.posteriors) if campaign.posterior_state else 0,
            }

        # Campaign overview
        campaign_overview = {
            "campaign_id": campaign.id,
            "campaign_name": campaign.name,
            "status": campaign.status.value,
            "target": report.target_profile.name,
            "target_type": report.target_profile.target_type.value,
            "access_level": report.target_profile.access_level.value,
            "total_attempts": total_attempts,
            "techniques_tried": len(campaign.state.techniques_tried),
        }

        return {
            "total_techniques_tested": len(tested_techniques),
            "total_attempts": total_attempts,
            "success_count": success_count,
            "failure_count": failure_count,
            "inconclusive_count": inconclusive_count,
            "overall_success_rate": success_count / max(total_attempts, 1),
            "layers_tested": layers_tested,
            "max_risk_score": max_risk,
            "campaign_overview": campaign_overview,
            "per_domain": dict(per_domain),
            "per_surface": dict(per_surface),
            "per_phase": per_phase,
            "coverage": coverage,
            "adaptive": adaptive_stats if adaptive_stats else None,
        }

    def _build_posterior_evolution(self, campaign: Campaign) -> list[dict] | None:
        """Build posterior evolution timeline data."""
        if not campaign.posterior_history:
            return None
        return campaign.posterior_history

    def _build_sensitivity(self, campaign: Campaign) -> dict | None:
        """Build sensitivity analysis data if available."""
        if not hasattr(campaign, 'sensitivity_report') or not campaign.sensitivity_report:
            return None
        report = campaign.sensitivity_report
        return {
            "num_samples": report.num_samples,
            "perturbation_pct": report.perturbation_pct,
            "most_sensitive": report.most_sensitive_weight,
            "least_sensitive": report.least_sensitive_weight,
            "weights": [
                {
                    "name": ws.weight_name,
                    "rank_correlation": ws.rank_correlation,
                    "top_k_stability": ws.top_k_stability,
                    "displaced": ws.displaced_techniques,
                }
                for ws in report.weight_sensitivities
            ],
        }

    def _build_compliance(self, report: DefenderReport) -> list[dict]:
        """Build compliance framework data from report summaries."""
        return report.compliance_summaries

    def _find_evaluation(self, campaign: Campaign, technique_id: str):
        """Find the best evaluation result for a technique."""
        best = None
        for evaluation in campaign.state.evaluations:
            if evaluation.comparability.technique_id == technique_id:
                if best is None:
                    best = evaluation
                elif evaluation.success is True and best.success is not True:
                    best = evaluation
                elif (evaluation.score or 0) > (best.score or 0):
                    best = evaluation
        return best
