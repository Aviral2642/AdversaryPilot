"""Attack plan models — prioritized technique sequences with rationale."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from adversarypilot.models.target import TargetProfile
from adversarypilot.utils.timestamps import utc_now


class ScoreBreakdown(BaseModel):
    """Detailed scoring breakdown for a single technique in a plan."""

    compatibility: float = 0.0
    access_fit: float = 0.0
    goal_fit: float = 0.0
    defense_bypass_likelihood: float = 0.0
    signal_gain: float = 0.0
    cost_penalty: float = 0.0
    detection_risk_penalty: float = 0.0
    diversity_bonus: float = 0.0
    thompson_sample: float | None = None
    utility: float | None = None
    total: float = 0.0
    confidence_interval: tuple[float, float] | None = None
    posterior_variance: float | None = None
    observations: int = 0


class PlanEntry(BaseModel):
    """A single technique in the attack plan with rationale."""

    rank: int
    technique_id: str
    technique_name: str
    score: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    rationale: str = ""
    estimated_queries: int | None = None
    tags: list[str] = Field(default_factory=list)
    structured_rationale: dict[str, Any] = Field(default_factory=dict)
    execution_hooks: list[str] = Field(default_factory=list)


class AttackPlan(BaseModel):
    """Ordered, ranked attack plan for a target."""

    schema_version: str = "1.0"
    target: TargetProfile
    entries: list[PlanEntry] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    config_used: dict[str, Any] = Field(default_factory=dict)
    notes: str = ""

    @property
    def technique_ids(self) -> list[str]:
        return [e.technique_id for e in self.entries]
