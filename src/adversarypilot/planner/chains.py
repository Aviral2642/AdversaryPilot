"""Multi-stage attack chain planning.

Implements prerequisite-aware technique composition, escalation paths,
and defense-adaptive strategy construction.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from adversarypilot.models.enums import Goal, Phase, Surface
from adversarypilot.models.plan import AttackPlan, PlanEntry
from adversarypilot.models.results import EvaluationResult
from adversarypilot.models.target import TargetProfile
from adversarypilot.models.technique import AttackTechnique
from adversarypilot.taxonomy.registry import TechniqueRegistry

logger = logging.getLogger(__name__)


class AttackChain:
    """An ordered sequence of techniques forming a multi-stage attack.

    Each stage can have prerequisites that must succeed before proceeding.
    """

    def __init__(
        self,
        chain_id: str,
        name: str,
        stages: list[ChainStage] | None = None,
        target_goal: Goal | None = None,
    ) -> None:
        self.chain_id = chain_id
        self.name = name
        self.stages = stages or []
        self.target_goal = target_goal

    @property
    def total_cost(self) -> float:
        """Sum of all stage costs."""
        return sum(s.estimated_cost for s in self.stages)

    @property
    def phase_sequence(self) -> list[Phase]:
        """Ordered phases in this chain."""
        return [s.phase for s in self.stages]

    def to_dict(self) -> dict[str, Any]:
        return {
            "chain_id": self.chain_id,
            "name": self.name,
            "stages": [s.to_dict() for s in self.stages],
            "target_goal": self.target_goal,
            "total_cost": self.total_cost,
        }


class ChainStage:
    """A single stage in an attack chain."""

    def __init__(
        self,
        stage_number: int,
        technique_id: str,
        technique_name: str,
        phase: Phase,
        surface: Surface,
        estimated_cost: float,
        rationale: str = "",
        depends_on: list[int] | None = None,
        fallback_techniques: list[str] | None = None,
    ) -> None:
        self.stage_number = stage_number
        self.technique_id = technique_id
        self.technique_name = technique_name
        self.phase = phase
        self.surface = surface
        self.estimated_cost = estimated_cost
        self.rationale = rationale
        self.depends_on = depends_on or []
        self.fallback_techniques = fallback_techniques or []

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage_number,
            "technique_id": self.technique_id,
            "technique_name": self.technique_name,
            "phase": self.phase,
            "surface": self.surface,
            "estimated_cost": self.estimated_cost,
            "rationale": self.rationale,
            "depends_on": self.depends_on,
            "fallback_techniques": self.fallback_techniques,
        }


# Canonical kill chain phase ordering
KILL_CHAIN_ORDER = {
    Phase.RECON: 0,
    Phase.PROBE: 1,
    Phase.EXPLOIT: 2,
    Phase.PERSISTENCE: 3,
    Phase.EVALUATION: 4,
}

# Attack escalation paths: maps (initial_surface, goal) to preferred next surfaces
ESCALATION_PATHS: dict[tuple[str, str], list[Surface]] = {
    # After recon on guardrails, escalate to model-layer exploits
    ("guardrail", "jailbreak"): [Surface.MODEL, Surface.GUARDRAIL],
    # After probing the model, escalate to data extraction
    ("model", "extraction"): [Surface.DATA, Surface.RETRIEVAL],
    # After tool probing, escalate to action-layer attacks
    ("tool", "tool_misuse"): [Surface.ACTION, Surface.TOOL],
    # For exfiltration, progress through retrieval → data → action
    ("retrieval", "exfil_sim"): [Surface.DATA, Surface.ACTION],
    # For poisoning, escalate from data to model
    ("data", "poisoning"): [Surface.MODEL],
}


class ChainPlanner:
    """Plans multi-stage attack chains with prerequisite awareness.

    Constructs kill-chain-ordered attack sequences that:
    1. Start with recon/probe techniques
    2. Escalate through surfaces based on goal
    3. Adapt based on observed defense responses
    4. Include fallback alternatives at each stage
    """

    def __init__(
        self,
        registry: TechniqueRegistry,
        max_chain_length: int = 5,
        max_chains: int = 3,
    ) -> None:
        """Initialize chain planner.

        Args:
            registry: Technique registry
            max_chain_length: Maximum stages per chain
            max_chains: Maximum chains to generate
        """
        self.registry = registry
        self.max_chain_length = max_chain_length
        self.max_chains = max_chains

        # Build technique index by (phase, surface)
        self._tech_by_phase_surface: dict[tuple[Phase, Surface], list[AttackTechnique]] = (
            defaultdict(list)
        )
        for t in registry.get_all():
            self._tech_by_phase_surface[(t.phase, t.surface)].append(t)

    def plan_chains(
        self,
        target: TargetProfile,
        plan: AttackPlan,
        prior_results: list[EvaluationResult] | None = None,
    ) -> list[AttackChain]:
        """Generate multi-stage attack chains for each target goal.

        Args:
            target: Target profile
            plan: Base attack plan (from prioritizer/adaptive planner)
            prior_results: Prior evaluation results for adaptation

        Returns:
            List of attack chains, one per primary goal
        """
        chains: list[AttackChain] = []
        prior_results = prior_results or []

        # Build a set of failed surfaces from prior results for adaptation
        failed_surfaces = self._identify_defended_surfaces(prior_results)

        for goal in target.goals:
            chain = self._build_chain_for_goal(
                target, goal, plan, failed_surfaces
            )
            if chain and chain.stages:
                chains.append(chain)

        # Sort by expected success (fewer defended surfaces = better chance)
        chains.sort(key=lambda c: c.total_cost)

        return chains[: self.max_chains]

    def _build_chain_for_goal(
        self,
        target: TargetProfile,
        goal: Goal,
        plan: AttackPlan,
        failed_surfaces: set[Surface],
    ) -> AttackChain:
        """Build a kill-chain-ordered attack sequence for a specific goal.

        Args:
            target: Target profile
            goal: Target goal
            plan: Base plan with ranked techniques
            failed_surfaces: Surfaces where attacks have failed

        Returns:
            Attack chain
        """
        # Get plan entries relevant to this goal
        goal_techniques = [
            e for e in plan.entries
            if any(
                goal in (self.registry.get(e.technique_id) or AttackTechnique(
                    id="", name="", domain="llm", phase="exploit",
                    surface="model", access_required="black_box",
                )).goals_supported
                for _ in [None]
            )
        ]

        # Also find techniques from catalog for this goal
        catalog_for_goal = [
            t for t in self.registry.get_all()
            if goal in t.goals_supported
            and target.target_type in t.target_types
        ]

        stages: list[ChainStage] = []
        stage_num = 0
        used_techniques: set[str] = set()

        # Phase 1: RECON — identify surfaces and defenses
        recon_tech = self._find_best_technique(
            Phase.RECON, None, goal, catalog_for_goal, used_techniques, failed_surfaces
        )
        if recon_tech:
            stages.append(ChainStage(
                stage_number=stage_num,
                technique_id=recon_tech.id,
                technique_name=recon_tech.name,
                phase=Phase.RECON,
                surface=recon_tech.surface,
                estimated_cost=recon_tech.base_cost,
                rationale=f"Reconnaissance: map {recon_tech.surface} layer defenses",
                fallback_techniques=self._find_fallbacks(
                    Phase.RECON, recon_tech.surface, goal, catalog_for_goal, {recon_tech.id}
                ),
            ))
            used_techniques.add(recon_tech.id)
            stage_num += 1

        # Phase 2: PROBE — test specific weaknesses
        probe_tech = self._find_best_technique(
            Phase.PROBE, None, goal, catalog_for_goal, used_techniques, failed_surfaces
        )
        if probe_tech:
            stages.append(ChainStage(
                stage_number=stage_num,
                technique_id=probe_tech.id,
                technique_name=probe_tech.name,
                phase=Phase.PROBE,
                surface=probe_tech.surface,
                estimated_cost=probe_tech.base_cost,
                rationale=f"Probe: test {probe_tech.surface} layer for {goal} vectors",
                depends_on=[0] if recon_tech else [],
                fallback_techniques=self._find_fallbacks(
                    Phase.PROBE, probe_tech.surface, goal, catalog_for_goal, {probe_tech.id}
                ),
            ))
            used_techniques.add(probe_tech.id)
            stage_num += 1

        # Phase 3+: EXPLOIT — primary attack, adapting around defended surfaces
        exploit_techs = sorted(
            [t for t in catalog_for_goal if t.phase == Phase.EXPLOIT and t.id not in used_techniques],
            key=lambda t: (t.surface in failed_surfaces, t.base_cost),
        )

        for exploit_tech in exploit_techs[:2]:  # Up to 2 exploit stages
            if stage_num >= self.max_chain_length:
                break

            avoid_msg = ""
            if exploit_tech.surface in failed_surfaces:
                avoid_msg = f" (NOTE: {exploit_tech.surface} showed defenses, consider fallbacks)"

            stages.append(ChainStage(
                stage_number=stage_num,
                technique_id=exploit_tech.id,
                technique_name=exploit_tech.name,
                phase=Phase.EXPLOIT,
                surface=exploit_tech.surface,
                estimated_cost=exploit_tech.base_cost,
                rationale=f"Exploit: {exploit_tech.name} targeting {exploit_tech.surface}{avoid_msg}",
                depends_on=list(range(stage_num)),
                fallback_techniques=self._find_fallbacks(
                    Phase.EXPLOIT, exploit_tech.surface, goal, catalog_for_goal, {exploit_tech.id}
                ),
            ))
            used_techniques.add(exploit_tech.id)
            stage_num += 1

        chain = AttackChain(
            chain_id=f"chain-{goal}-{len(stages)}",
            name=f"{goal.value} kill chain ({len(stages)} stages)",
            stages=stages,
            target_goal=goal,
        )

        logger.info(
            "Built attack chain '%s' with %d stages, total_cost=%.2f",
            chain.name, len(chain.stages), chain.total_cost,
        )

        return chain

    def _find_best_technique(
        self,
        phase: Phase,
        preferred_surface: Surface | None,
        goal: Goal,
        candidates: list[AttackTechnique],
        exclude: set[str],
        failed_surfaces: set[Surface],
    ) -> AttackTechnique | None:
        """Find the best technique for a given phase/surface/goal.

        Prefers untried surfaces over surfaces where attacks failed.

        Args:
            phase: Attack phase
            preferred_surface: Preferred surface (None = any)
            goal: Target goal
            candidates: Available techniques
            exclude: Technique IDs to exclude
            failed_surfaces: Surfaces where attacks failed

        Returns:
            Best technique or None
        """
        filtered = [
            t for t in candidates
            if t.phase == phase
            and t.id not in exclude
            and (preferred_surface is None or t.surface == preferred_surface)
        ]

        if not filtered:
            # Relax surface constraint
            filtered = [
                t for t in candidates
                if t.phase == phase and t.id not in exclude
            ]

        if not filtered:
            return None

        # Sort: prefer surfaces NOT in failed_surfaces, then by cost
        filtered.sort(key=lambda t: (t.surface in failed_surfaces, t.base_cost))
        return filtered[0]

    def _find_fallbacks(
        self,
        phase: Phase,
        surface: Surface,
        goal: Goal,
        candidates: list[AttackTechnique],
        exclude: set[str],
        max_fallbacks: int = 2,
    ) -> list[str]:
        """Find fallback technique IDs for a stage.

        Args:
            phase: Attack phase
            surface: Target surface
            goal: Target goal
            candidates: Available techniques
            exclude: Technique IDs to exclude
            max_fallbacks: Maximum fallbacks to return

        Returns:
            List of fallback technique IDs
        """
        fallbacks = [
            t.id for t in candidates
            if t.phase == phase and t.id not in exclude
        ]
        return fallbacks[:max_fallbacks]

    def _identify_defended_surfaces(
        self, prior_results: list[EvaluationResult]
    ) -> set[Surface]:
        """Identify surfaces where attacks consistently failed.

        Args:
            prior_results: Prior evaluation results

        Returns:
            Set of surfaces with strong defenses
        """
        surface_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"success": 0, "total": 0})

        for result in prior_results:
            tech_id = result.comparability.technique_id
            if not tech_id:
                continue
            technique = self.registry.get(tech_id)
            if technique is None:
                continue

            surface_key = technique.surface.value
            surface_stats[surface_key]["total"] += 1
            if result.success:
                surface_stats[surface_key]["success"] += 1

        defended: set[Surface] = set()
        for surface_key, stats in surface_stats.items():
            if stats["total"] >= 2 and stats["success"] == 0:
                try:
                    defended.add(Surface(surface_key))
                except ValueError:
                    pass

        if defended:
            logger.info("Defended surfaces detected: %s", defended)

        return defended


def suggest_escalation(
    current_surface: Surface,
    goal: Goal,
) -> list[Surface]:
    """Suggest next surfaces to target based on current position and goal.

    Args:
        current_surface: Current attack surface
        goal: Target goal

    Returns:
        List of recommended next surfaces, ordered by priority
    """
    key = (current_surface.value, goal.value)
    if key in ESCALATION_PATHS:
        return ESCALATION_PATHS[key]

    # Default escalation: try adjacent surfaces
    surface_order = [Surface.GUARDRAIL, Surface.MODEL, Surface.DATA, Surface.RETRIEVAL, Surface.TOOL, Surface.ACTION]
    current_idx = surface_order.index(current_surface) if current_surface in surface_order else 0
    return [s for s in surface_order if s != current_surface][current_idx:]
