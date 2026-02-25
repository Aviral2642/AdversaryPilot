"""Correlated arms via technique family grouping.

When a technique is observed, siblings in the same family receive a
fractional posterior update (spillover). This captures the intuition
that techniques sharing domain, surface, and primary tag are likely
to have correlated success rates against the same target.
"""

from __future__ import annotations

from collections import defaultdict

from adversarypilot.models.technique import AttackTechnique
from adversarypilot.planner.posterior import PosteriorState


class FamilyCorrelation:
    """Manages family-level posterior correlation between sibling techniques."""

    def __init__(self, spillover_rate: float = 0.3) -> None:
        self.spillover_rate = spillover_rate
        self._families: dict[str, set[str]] = defaultdict(set)
        self._id_to_family: dict[str, str] = {}

    def register_techniques(self, catalog: list[AttackTechnique]) -> None:
        """Build family index from technique catalog."""
        self._families.clear()
        self._id_to_family.clear()
        for technique in catalog:
            family = self._family_key(technique)
            self._families[family].add(technique.id)
            self._id_to_family[technique.id] = family

    def get_siblings(self, technique_id: str) -> set[str]:
        """Return sibling technique IDs (same family, excluding self)."""
        family = self._id_to_family.get(technique_id)
        if not family:
            return set()
        return self._families[family] - {technique_id}

    def propagate_update(
        self,
        observed_id: str,
        reward: float,
        posterior_state: PosteriorState,
    ) -> None:
        """Propagate a fractional reward to sibling techniques.

        Applies spillover_rate * reward to siblings' alpha/beta without
        incrementing their observation count, preserving the distinction
        between direct and inferred evidence.
        """
        siblings = self.get_siblings(observed_id)
        if not siblings:
            return

        spillover = reward * self.spillover_rate
        for sibling_id in siblings:
            if sibling_id not in posterior_state.posteriors:
                posterior_state.get_or_init(sibling_id, 0.5)
            posterior = posterior_state.posteriors[sibling_id]
            posterior.alpha += spillover
            posterior.beta += (1.0 - reward) * self.spillover_rate

    @staticmethod
    def _family_key(technique: AttackTechnique) -> str:
        primary_tag = technique.tags[0] if technique.tags else technique.surface.value
        return f"{technique.domain.value}:{technique.surface.value}:{primary_tag}"
