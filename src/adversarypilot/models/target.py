"""Target profile models — what you're attacking."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from adversarypilot.models.enums import AccessLevel, Goal, StealthLevel, TargetType


class ConstraintSpec(BaseModel):
    """Operational constraints on the attack campaign."""

    max_queries: int | None = Field(None, description="Total query budget")
    rate_limit_rpm: int | None = Field(None, description="Max requests per minute")
    max_time_seconds: int | None = Field(None, description="Time budget in seconds")
    stealth_priority: StealthLevel = Field(
        StealthLevel.OVERT, description="How stealthy the campaign should be"
    )
    custom_constraints: dict[str, Any] = Field(default_factory=dict)


class DefenseProfile(BaseModel):
    """Observed defenses on the target system."""

    has_moderation: bool = False
    has_input_filtering: bool = False
    has_output_filtering: bool = False
    has_schema_validation: bool = False
    has_rate_limiting: bool = False
    has_prompt_injection_detection: bool = False
    known_defenses: list[str] = Field(default_factory=list, description="Free-form defense list")
    notes: str = ""


class TargetProfile(BaseModel):
    """Complete description of the attack target."""

    schema_version: str = "1.0"
    name: str
    target_type: TargetType
    access_level: AccessLevel
    description: str = ""
    constraints: ConstraintSpec = Field(default_factory=ConstraintSpec)
    defenses: DefenseProfile = Field(default_factory=DefenseProfile)
    goals: list[Goal] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
