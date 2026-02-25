"""Meta-learning across campaigns — posterior caching and nearest-neighbor transfer.

Stores campaign posteriors indexed by target profile. When starting a new
campaign, finds the most similar prior campaign and uses its posteriors as
warm-start priors.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from adversarypilot.models.target import TargetProfile
from adversarypilot.utils.hashing import hash_target_profile

logger = logging.getLogger(__name__)


@dataclass
class CachedPosterior:
    """A stored posterior state from a completed campaign."""

    target_hash: str
    target_type: str
    access_level: str
    goals: list[str]
    campaign_id: str
    posteriors: dict[str, dict[str, float]]  # tech_id -> {alpha, beta, mean}
    metadata: dict[str, Any] = field(default_factory=dict)


class PosteriorCache:
    """Persistent cache of campaign posteriors for meta-learning."""

    def __init__(self, cache_dir: str | Path = ".adversarypilot/posterior_cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._entries: list[CachedPosterior] = []
        self._load_cache()

    def _load_cache(self) -> None:
        """Load cached posteriors from disk."""
        for path in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text())
                self._entries.append(CachedPosterior(**data))
            except (json.JSONDecodeError, TypeError, KeyError) as e:
                logger.warning("Skipping invalid cache file %s: %s", path, e)

    def store(
        self,
        target: TargetProfile,
        posteriors: dict[str, dict[str, float]],
        campaign_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Store a campaign's posteriors in the cache.

        Args:
            target: Target profile
            posteriors: Posterior state {tech_id: {alpha, beta, mean}}
            campaign_id: Campaign identifier
            metadata: Optional extra metadata
        """
        target_hash = hash_target_profile(target)
        entry = CachedPosterior(
            target_hash=target_hash,
            target_type=target.target_type.value,
            access_level=target.access_level.value,
            goals=[g.value for g in target.goals],
            campaign_id=campaign_id,
            posteriors=posteriors,
            metadata=metadata or {},
        )
        self._entries.append(entry)

        # Write to disk
        filename = f"{campaign_id}_{target_hash}.json"
        path = self.cache_dir / filename
        path.write_text(json.dumps({
            "target_hash": entry.target_hash,
            "target_type": entry.target_type,
            "access_level": entry.access_level,
            "goals": entry.goals,
            "campaign_id": entry.campaign_id,
            "posteriors": entry.posteriors,
            "metadata": entry.metadata,
        }, indent=2))

        logger.info("Stored posteriors for campaign %s (target: %s)", campaign_id, target_hash)

    def find_nearest(
        self,
        target: TargetProfile,
        max_distance: float = 0.3,
    ) -> dict[str, dict[str, float]] | None:
        """Find the nearest cached posterior state for a target profile.

        Uses weighted Jaccard distance over target_type, access_level, goals.

        Args:
            target: Target profile to match against
            max_distance: Maximum acceptable distance (0-1)

        Returns:
            Posterior dict if found within max_distance, else None
        """
        if not self._entries:
            return None

        target_hash = hash_target_profile(target)

        # Exact match first
        for entry in self._entries:
            if entry.target_hash == target_hash:
                logger.info("Found exact posterior match from campaign %s", entry.campaign_id)
                return entry.posteriors

        # Nearest-neighbor search
        best_entry = None
        best_distance = float("inf")

        for entry in self._entries:
            distance = self._compute_distance(target, entry)
            if distance < best_distance:
                best_distance = distance
                best_entry = entry

        if best_entry and best_distance <= max_distance:
            logger.info(
                "Found nearest posterior (distance=%.3f) from campaign %s",
                best_distance, best_entry.campaign_id,
            )
            return best_entry.posteriors

        return None

    def _compute_distance(self, target: TargetProfile, entry: CachedPosterior) -> float:
        """Compute weighted distance between a target and a cached entry.

        Weights: target_type=0.4, access_level=0.2, goals=0.4
        """
        # Target type match (0 or 1)
        type_distance = 0.0 if target.target_type.value == entry.target_type else 1.0

        # Access level distance (normalized)
        access_order = {"black_box": 0, "gray_box": 1, "white_box": 2}
        a1 = access_order.get(target.access_level.value, 0)
        a2 = access_order.get(entry.access_level, 0)
        access_distance = abs(a1 - a2) / 2.0

        # Goal Jaccard distance
        target_goals = set(g.value for g in target.goals)
        entry_goals = set(entry.goals)
        if target_goals or entry_goals:
            intersection = len(target_goals & entry_goals)
            union = len(target_goals | entry_goals)
            goal_distance = 1.0 - (intersection / union) if union > 0 else 1.0
        else:
            goal_distance = 0.0

        return 0.4 * type_distance + 0.2 * access_distance + 0.4 * goal_distance

    @property
    def size(self) -> int:
        """Number of cached entries."""
        return len(self._entries)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._entries.clear()
        for path in self.cache_dir.glob("*.json"):
            path.unlink()
