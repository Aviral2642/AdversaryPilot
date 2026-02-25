"""Decision snapshot model for replay system."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from adversarypilot.planner.posterior import PosteriorState
from adversarypilot.utils.timestamps import utc_now


class DecisionSnapshot(BaseModel):
    """Complete snapshot of a planning decision for replay.

    Stores all inputs, intermediate scoring, and output to enable
    deterministic replay and divergence explanation.
    """

    # Identity
    snapshot_id: str
    campaign_id: str
    step_number: int
    timestamp: datetime = Field(default_factory=utc_now)
    decision_type: str = Field("plan_generation", description="Type of decision")
    step_seed: int = Field(description="Deterministic seed for this step")

    # Frozen campaign state
    techniques_tried: list[str] = Field(default_factory=list)
    evaluation_count: int = 0
    queries_used: int = 0

    # Frozen planner state
    posterior_state: PosteriorState
    planner_config: dict[str, Any] = Field(default_factory=dict)

    # Full scoring inputs (for divergence explanation)
    filtered_candidates: list[str] = Field(
        default_factory=list, description="Technique IDs that passed hard filters"
    )
    filter_rejections: dict[str, str] = Field(
        default_factory=dict, description="Rejected technique_id -> reason"
    )
    base_scores: dict[str, float] = Field(
        default_factory=dict, description="Technique_id -> V1 base score"
    )
    thompson_samples: dict[str, float] = Field(
        default_factory=dict, description="Technique_id -> sampled Beta value"
    )
    utility_components: dict[str, dict[str, float]] = Field(
        default_factory=dict,
        description="Technique_id -> {impact, cost, info_gain, detection, diversity, utility}",
    )

    # Output (for verification)
    produced_plan_entries: list[dict[str, Any]] = Field(
        default_factory=list, description="Serialized PlanEntry dicts"
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary.

        Returns:
            Dictionary representation
        """
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DecisionSnapshot:
        """Deserialize from dictionary.

        Args:
            data: Dictionary representation

        Returns:
            DecisionSnapshot instance
        """
        return cls.model_validate(data)
