"""Coverage gap detection for attack assessments."""

from __future__ import annotations

from dataclasses import dataclass, field

from adversarypilot.models.enums import Goal, Phase, Surface
from adversarypilot.taxonomy.registry import TechniqueRegistry


@dataclass
class CoverageGap:
    """A detected gap in assessment coverage."""

    gap_type: str  # "surface", "goal", "phase", "atlas"
    identifier: str
    severity: str  # "high", "medium", "low"
    description: str
    suggested_techniques: list[str] = field(default_factory=list)


@dataclass
class CoverageReport:
    """Summary of assessment coverage across all dimensions."""

    atlas_coverage: float = 0.0
    surface_coverage: dict[str, float] = field(default_factory=dict)
    goal_coverage: dict[str, float] = field(default_factory=dict)
    phase_coverage: dict[str, float] = field(default_factory=dict)
    gaps: list[CoverageGap] = field(default_factory=list)


class CoverageAnalyzer:
    """Analyzes assessment coverage across surfaces, goals, phases, and ATLAS mappings."""

    def __init__(self, registry: TechniqueRegistry | None = None) -> None:
        self.registry = registry or TechniqueRegistry()
        if not self.registry.get_all():
            self.registry.load_catalog()

    def analyze(
        self,
        techniques_tried: list[str],
        target_goals: list[Goal] | None = None,
    ) -> CoverageReport:
        """Analyze coverage gaps.

        Args:
            techniques_tried: List of technique IDs that were tested
            target_goals: Goals the assessment should cover (all if None)

        Returns:
            CoverageReport with gaps sorted by severity
        """
        catalog = self.registry.get_all()
        tried_set = set(techniques_tried)
        gaps: list[CoverageGap] = []

        # Surface coverage
        surface_coverage = self._check_surface_coverage(catalog, tried_set, gaps)

        # Goal coverage
        goals = target_goals or list(Goal)
        goal_coverage = self._check_goal_coverage(catalog, tried_set, goals, gaps)

        # Phase coverage
        phase_coverage = self._check_phase_coverage(catalog, tried_set, gaps)

        # ATLAS coverage
        atlas_coverage = self._check_atlas_coverage(catalog, tried_set, gaps)

        # Sort gaps: high > medium > low
        severity_order = {"high": 0, "medium": 1, "low": 2}
        gaps.sort(key=lambda g: severity_order.get(g.severity, 3))

        return CoverageReport(
            atlas_coverage=atlas_coverage,
            surface_coverage=surface_coverage,
            goal_coverage=goal_coverage,
            phase_coverage=phase_coverage,
            gaps=gaps,
        )

    def _check_surface_coverage(
        self,
        catalog: list,
        tried: set[str],
        gaps: list[CoverageGap],
    ) -> dict[str, float]:
        """Check which surfaces have been tested."""
        surface_techniques: dict[str, list[str]] = {s.value: [] for s in Surface}
        surface_tested: dict[str, int] = {s.value: 0 for s in Surface}

        for t in catalog:
            surface_techniques[t.surface.value].append(t.id)
            if t.id in tried:
                surface_tested[t.surface.value] += 1

        coverage = {}
        for surface in Surface:
            s = surface.value
            total = len(surface_techniques[s])
            tested = surface_tested[s]
            coverage[s] = tested / max(total, 1)

            if tested == 0 and total > 0:
                suggestions = surface_techniques[s][:3]
                gaps.append(CoverageGap(
                    gap_type="surface",
                    identifier=s,
                    severity="high",
                    description=f"Surface '{s}' has {total} techniques but none were tested",
                    suggested_techniques=suggestions,
                ))

        return coverage

    def _check_goal_coverage(
        self,
        catalog: list,
        tried: set[str],
        goals: list[Goal],
        gaps: list[CoverageGap],
    ) -> dict[str, float]:
        """Check which goals have been tested."""
        goal_techniques: dict[str, list[str]] = {g.value: [] for g in goals}
        goal_tested: dict[str, int] = {g.value: 0 for g in goals}

        for t in catalog:
            for g in t.goals_supported:
                if g in goals:
                    goal_techniques[g.value].append(t.id)
                    if t.id in tried:
                        goal_tested[g.value] += 1

        coverage = {}
        for goal in goals:
            g = goal.value
            total = len(goal_techniques[g])
            tested = goal_tested[g]
            coverage[g] = tested / max(total, 1)

            if tested == 0 and total > 0:
                suggestions = goal_techniques[g][:3]
                gaps.append(CoverageGap(
                    gap_type="goal",
                    identifier=g,
                    severity="high",
                    description=f"Goal '{g}' has {total} applicable techniques but none were tested",
                    suggested_techniques=suggestions,
                ))

        return coverage

    def _check_phase_coverage(
        self,
        catalog: list,
        tried: set[str],
        gaps: list[CoverageGap],
    ) -> dict[str, float]:
        """Check which phases have been tested."""
        phase_techniques: dict[str, list[str]] = {p.value: [] for p in Phase}
        phase_tested: dict[str, int] = {p.value: 0 for p in Phase}

        for t in catalog:
            phase_techniques[t.phase.value].append(t.id)
            if t.id in tried:
                phase_tested[t.phase.value] += 1

        coverage = {}
        for phase in Phase:
            p = phase.value
            total = len(phase_techniques[p])
            tested = phase_tested[p]
            coverage[p] = tested / max(total, 1)

            if tested == 0 and total > 0:
                gaps.append(CoverageGap(
                    gap_type="phase",
                    identifier=p,
                    severity="low",
                    description=f"Phase '{p}' has {total} techniques but none were tested",
                    suggested_techniques=phase_techniques[p][:3],
                ))

        return coverage

    def _check_atlas_coverage(
        self,
        catalog: list,
        tried: set[str],
        gaps: list[CoverageGap],
    ) -> float:
        """Check ATLAS technique coverage."""
        all_atlas_ids = set()
        tested_atlas_ids = set()

        for t in catalog:
            for ref in t.atlas_refs:
                all_atlas_ids.add(ref.atlas_id)
                if t.id in tried:
                    tested_atlas_ids.add(ref.atlas_id)

        if not all_atlas_ids:
            return 1.0

        coverage = len(tested_atlas_ids) / len(all_atlas_ids)

        untested = all_atlas_ids - tested_atlas_ids
        if untested:
            gaps.append(CoverageGap(
                gap_type="atlas",
                identifier=f"{len(untested)} untested ATLAS techniques",
                severity="medium",
                description=f"{len(tested_atlas_ids)}/{len(all_atlas_ids)} ATLAS techniques covered ({coverage:.0%})",
            ))

        return coverage
