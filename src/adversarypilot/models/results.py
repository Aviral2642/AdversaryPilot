"""Result models — attempt outputs + evaluation with comparability metadata."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from adversarypilot.models.enums import JudgeType
from adversarypilot.utils.timestamps import utc_now


class AttemptResult(BaseModel):
    """Raw output from a single attack attempt."""

    id: str = Field(description="Unique attempt identifier (UUID)")
    technique_id: str
    timestamp: datetime = Field(default_factory=utc_now)
    prompt: str | None = None
    response: str | None = None
    raw_output: dict[str, Any] = Field(default_factory=dict)
    artifacts: list[str] = Field(default_factory=list, description="File paths, log references")
    duration_ms: int | None = None
    source_tool: str | None = Field(None, description="garak, promptfoo, manual, etc.")
    source_run_id: str | None = None


class ComparabilityMetadata(BaseModel):
    """Metadata enabling valid cross-result comparisons."""

    target_profile_hash: str = ""
    technique_id: str = ""
    technique_config_hash: str = ""
    judge_type: JudgeType = JudgeType.RULE_BASED
    judge_model_version: str | None = None
    input_slice_id: str | None = None
    dataset_version: str | None = None
    success_criteria_hash: str = ""
    num_trials: int = 1
    random_seed_policy: str = Field("unknown", description="fixed, swept, or unknown")
    decoding_config_hash: str | None = None
    rate_limit_conditions: str | None = None
    time_window: str | None = None
    comparable_group_key: str = Field("", description="Derived canonical hash for grouping")
    comparability_flags: list[str] = Field(
        default_factory=list, description="Reasons results may not be comparable"
    )


class EvaluationResult(BaseModel):
    """Judged outcome of an attempt, separated from raw output for measurement validity."""

    attempt_id: str
    success: bool | None = Field(None, description="None = inconclusive")
    score: float | None = Field(None, ge=0.0, le=1.0)
    judge_type: JudgeType = JudgeType.RULE_BASED
    judge_details: dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    evidence_quality: float = Field(0.5, ge=0.0, le=1.0)
    comparability: ComparabilityMetadata = Field(default_factory=ComparabilityMetadata)
    notes: str = ""
