"""Compliance framework coverage analysis.

Maps tested techniques to OWASP LLM Top 10, NIST AI RMF, and EU AI Act
controls. Computes per-framework coverage and identifies untested controls.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from adversarypilot.models.enums import Goal
from adversarypilot.taxonomy.registry import TechniqueRegistry


# Reference control sets for each framework
OWASP_LLM_TOP10: dict[str, str] = {
    "LLM01": "Prompt Injection",
    "LLM02": "Insecure Output Handling",
    "LLM03": "Training Data Poisoning",
    "LLM04": "Model Denial of Service",
    "LLM05": "Supply Chain Vulnerabilities",
    "LLM06": "Sensitive Information Disclosure",
    "LLM07": "Insecure Plugin Design",
    "LLM08": "Excessive Agency",
    "LLM09": "Overreliance",
    "LLM10": "Model Theft",
}

NIST_AI_RMF: dict[str, str] = {
    "MAP-1.1": "Intended purposes, context of use, and limitations identified",
    "MAP-1.5": "Organizational risk tolerance determined",
    "MAP-2.1": "Intended benefits and costs compared",
    "MAP-2.3": "Scientific integrity and data quality assessed",
    "MAP-3.1": "Potential benefits and positive impacts identified",
    "MAP-3.5": "Impacts to individuals and communities identified",
    "MEASURE-1.1": "AI risk measurement approaches employed",
    "MEASURE-2.1": "Evaluations performed for safety and bias",
    "MEASURE-2.3": "AI system performance tested under adversarial conditions",
    "MEASURE-2.5": "AI system evaluated for privacy risks",
    "MEASURE-2.6": "AI system evaluated for security risks",
    "MEASURE-2.7": "AI system evaluated for reliability",
    "MEASURE-2.9": "AI system evaluated for robustness",
    "MEASURE-3.1": "Risk tracking approaches established",
    "MANAGE-1.1": "AI risks prioritized and responded to",
    "MANAGE-2.1": "Resources allocated to manage AI risks",
    "MANAGE-2.4": "Mechanisms in place for feedback",
    "MANAGE-3.1": "AI risks and incidents managed",
    "MANAGE-4.1": "Risk treatments monitored",
    "GOVERN-1.1": "Legal and regulatory requirements identified",
}

EU_AI_ACT: dict[str, str] = {
    "Art.6": "Classification rules for high-risk AI systems",
    "Art.9": "Risk management system",
    "Art.10": "Data and data governance",
    "Art.13": "Transparency and provision of information",
    "Art.14": "Human oversight",
    "Art.15": "Accuracy, robustness and cybersecurity",
    "Art.52": "Transparency obligations for certain AI systems",
    "Art.55": "Obligations for providers of general-purpose AI models with systemic risk",
}

FRAMEWORK_CONTROLS: dict[str, dict[str, str]] = {
    "owasp_llm_top10": OWASP_LLM_TOP10,
    "nist_ai_rmf": NIST_AI_RMF,
    "eu_ai_act": EU_AI_ACT,
}


@dataclass
class ControlResult:
    """Per-control assessment result."""

    control_id: str
    control_name: str
    techniques_mapped: list[str] = field(default_factory=list)
    techniques_tested: list[str] = field(default_factory=list)
    success_count: int = 0
    total_tested: int = 0
    risk_level: str = "untested"  # untested, low, moderate, high


@dataclass
class ComplianceSummary:
    """Per-framework compliance coverage summary."""

    framework: str
    framework_name: str
    total_controls: int
    tested_controls: int
    coverage_pct: float
    control_results: list[ControlResult] = field(default_factory=list)


class ComplianceAnalyzer:
    """Analyzes technique coverage against compliance frameworks."""

    def __init__(self, registry: TechniqueRegistry | None = None) -> None:
        self.registry = registry or TechniqueRegistry()
        if not self.registry.get_all():
            self.registry.load_catalog()

    def analyze(
        self,
        techniques_tried: list[str],
        evaluations: list | None = None,
        frameworks: list[str] | None = None,
    ) -> list[ComplianceSummary]:
        """Analyze compliance coverage across frameworks.

        Args:
            techniques_tried: Technique IDs that were tested
            evaluations: Optional evaluation results for success counting
            frameworks: Which frameworks to analyze (all if None)

        Returns:
            List of ComplianceSummary per framework
        """
        tried_set = set(techniques_tried)
        target_frameworks = frameworks or list(FRAMEWORK_CONTROLS.keys())
        catalog = self.registry.get_all()

        # Build success map from evaluations
        success_map: dict[str, bool] = {}
        if evaluations:
            for ev in evaluations:
                tid = ev.comparability.technique_id
                if ev.success is True:
                    success_map[tid] = True
                elif tid not in success_map:
                    success_map[tid] = ev.success is True

        summaries = []
        for fw_key in target_frameworks:
            controls = FRAMEWORK_CONTROLS.get(fw_key, {})
            if not controls:
                continue
            summary = self._analyze_framework(
                fw_key, controls, catalog, tried_set, success_map
            )
            summaries.append(summary)

        return summaries

    def _analyze_framework(
        self,
        framework: str,
        controls: dict[str, str],
        catalog: list,
        tried: set[str],
        success_map: dict[str, bool],
    ) -> ComplianceSummary:
        """Analyze a single framework's coverage."""
        framework_names = {
            "owasp_llm_top10": "OWASP LLM Top 10",
            "nist_ai_rmf": "NIST AI Risk Management Framework",
            "eu_ai_act": "EU AI Act",
        }

        control_results = []
        tested_controls = 0

        for control_id, control_name in controls.items():
            # Find techniques mapped to this control
            mapped = []
            tested = []
            successes = 0
            total = 0

            for tech in catalog:
                for ref in tech.compliance_refs:
                    if ref.framework == framework and ref.control_id == control_id:
                        mapped.append(tech.id)
                        if tech.id in tried:
                            tested.append(tech.id)
                            total += 1
                            if success_map.get(tech.id):
                                successes += 1
                        break

            if tested:
                tested_controls += 1
                rate = successes / max(total, 1)
                if rate >= 0.5:
                    risk = "high"
                elif rate >= 0.2:
                    risk = "moderate"
                else:
                    risk = "low"
            else:
                risk = "untested"

            control_results.append(ControlResult(
                control_id=control_id,
                control_name=control_name,
                techniques_mapped=mapped,
                techniques_tested=tested,
                success_count=successes,
                total_tested=total,
                risk_level=risk,
            ))

        total_controls = len(controls)
        coverage = tested_controls / max(total_controls, 1)

        return ComplianceSummary(
            framework=framework,
            framework_name=framework_names.get(framework, framework),
            total_controls=total_controls,
            tested_controls=tested_controls,
            coverage_pct=coverage,
            control_results=control_results,
        )
