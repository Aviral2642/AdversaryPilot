"""Diversity tracking for adaptive planning."""

from collections import defaultdict

from adversarypilot.models.enums import Surface
from adversarypilot.models.technique import AttackTechnique


class FamilyTracker:
    """Tracks tried attack families and surface coverage for diversity bonuses.

    A family is defined by (domain, surface, primary_tag) tuple.
    """

    def __init__(
        self,
        min_surface_coverage: int = 1,
        untested_layer_bonus: float = 0.3,
        repeat_family_penalty: float = 0.15,
        below_coverage_bonus: float = 0.15,
    ) -> None:
        """Initialize family tracker.

        Args:
            min_surface_coverage: Minimum attempts per surface before penalties
            untested_layer_bonus: Bonus for techniques on untested surfaces
            repeat_family_penalty: Penalty for techniques from tried families
            below_coverage_bonus: Bonus for surfaces below min coverage
        """
        self.min_surface_coverage = min_surface_coverage
        self.untested_layer_bonus = untested_layer_bonus
        self.repeat_family_penalty = repeat_family_penalty
        self.below_coverage_bonus = below_coverage_bonus

        self._tried_families: set[str] = set()
        self._surface_counts: dict[Surface, int] = defaultdict(int)

    def mark_tried(self, technique: AttackTechnique) -> None:
        """Mark a technique family as tried.

        Args:
            technique: Technique that was executed
        """
        family_key = self._get_family_key(technique)
        self._tried_families.add(family_key)
        self._surface_counts[technique.surface] += 1

    def compute_diversity_bonus(self, technique: AttackTechnique) -> float:
        """Compute diversity bonus for a technique.

        Bonuses:
        - +untested_layer_bonus for techniques on completely untested surfaces
        - +below_coverage_bonus for surfaces below min coverage threshold
        - -repeat_family_penalty for techniques from already-tried families

        Args:
            technique: Technique to score

        Returns:
            Diversity bonus (can be positive or negative)
        """
        bonus = 0.0
        surface = technique.surface
        family_key = self._get_family_key(technique)

        # Bonus for untested surface layer
        if surface not in self._surface_counts:
            bonus += self.untested_layer_bonus

        # Bonus for surfaces below minimum coverage
        elif self._surface_counts[surface] < self.min_surface_coverage:
            bonus += self.below_coverage_bonus

        # Penalty for repeat families
        if family_key in self._tried_families:
            bonus -= self.repeat_family_penalty

        return bonus

    def _get_family_key(self, technique: AttackTechnique) -> str:
        """Generate family key from technique.

        Family = (domain, surface, primary_tag).
        Primary tag is the first tag if available.

        Args:
            technique: Technique to get family for

        Returns:
            Family key string
        """
        primary_tag = technique.tags[0] if technique.tags else "none"
        return f"{technique.domain}:{technique.surface}:{primary_tag}"

    def get_surface_coverage(self) -> dict[Surface, int]:
        """Get current coverage counts per surface.

        Returns:
            Mapping of surface to attempt count
        """
        return dict(self._surface_counts)

    def reset(self) -> None:
        """Reset all tracking state."""
        self._tried_families.clear()
        self._surface_counts.clear()
