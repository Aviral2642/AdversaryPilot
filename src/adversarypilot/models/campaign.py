"""Campaign models — runtime state tracking for attack campaigns."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from adversarypilot.models.enums import CampaignPhase, CampaignStatus
from adversarypilot.models.plan import AttackPlan
from adversarypilot.models.results import AttemptResult, EvaluationResult
from adversarypilot.models.target import TargetProfile
from adversarypilot.planner.posterior import PosteriorState
from adversarypilot.utils.timestamps import utc_now


class CampaignState(BaseModel):
    """Mutable state of a running campaign."""

    attempts: list[AttemptResult] = Field(default_factory=list)
    evaluations: list[EvaluationResult] = Field(default_factory=list)
    techniques_tried: list[str] = Field(default_factory=list)
    queries_used: int = 0
    last_updated: datetime = Field(default_factory=utc_now)


class Campaign(BaseModel):
    """A complete attack campaign: target + plan + results + state."""

    model_config = {"arbitrary_types_allowed": True}

    id: str
    name: str = ""
    status: CampaignStatus = CampaignStatus.PLANNING
    phase: CampaignPhase = CampaignPhase.PROBE
    target: TargetProfile
    plan: AttackPlan | None = None
    state: CampaignState = Field(default_factory=CampaignState)
    posterior_state: PosteriorState | None = None  # Adaptive planner state
    posterior_history: list[dict[str, Any]] = Field(default_factory=list)
    sensitivity_report: Any = None  # SensitivityReport from prioritizer
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_attempts(self) -> int:
        return len(self.state.attempts)

    @property
    def successful_attempts(self) -> int:
        return sum(
            1
            for e in self.state.evaluations
            if e.success is True
        )
