"""Attack technique models — static technique metadata + per-run execution specs."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from adversarypilot.models.enums import (
    AccessLevel,
    Domain,
    ExecutionMode,
    Goal,
    Phase,
    StealthLevel,
    Surface,
    TargetType,
)


class AtlasReference(BaseModel):
    """Cross-reference to a MITRE ATLAS technique."""

    atlas_id: str = Field(description="e.g. AML.T0051")
    atlas_name: str = ""
    tactic: str = ""


class ComplianceReference(BaseModel):
    """Cross-reference to a compliance framework control."""

    framework: str = Field(description="owasp_llm_top10, nist_ai_rmf, eu_ai_act")
    control_id: str = Field(description="e.g. LLM01, MAP-1.1, Art.9(1)")
    control_name: str = ""
    relevance: str = ""


class AttackTechnique(BaseModel):
    """Canonical attack technique with multi-axis taxonomy tags."""

    id: str = Field(description="e.g. AP-TX-LLM-JAILBREAK-DAN")
    name: str
    description: str = ""
    domain: Domain
    phase: Phase
    surface: Surface
    access_required: AccessLevel
    goals_supported: list[Goal] = Field(default_factory=list)
    target_types: list[TargetType] = Field(default_factory=list)
    atlas_refs: list[AtlasReference] = Field(default_factory=list)
    compliance_refs: list[ComplianceReference] = Field(default_factory=list)
    other_refs: list[str] = Field(default_factory=list)
    base_cost: float = Field(0.5, ge=0.0, le=1.0, description="Normalized cost 0-1")
    stealth_profile: StealthLevel = StealthLevel.OVERT
    execution_mode: ExecutionMode = ExecutionMode.MANUAL
    prerequisites: list[str] = Field(
        default_factory=list, description="Technique IDs or capabilities required"
    )
    tags: list[str] = Field(default_factory=list)
    tool_support: list[str] = Field(
        default_factory=list, description="Tools that can execute this: garak, promptfoo, art"
    )


class TechniqueExecutionSpec(BaseModel):
    """Per-run parameters for executing a technique in a campaign."""

    technique_id: str
    query_budget: int | None = None
    prompt_set: str | None = None
    seed: int | None = None
    timeout_seconds: int | None = None
    judge_config: dict[str, Any] = Field(default_factory=dict)
    custom_params: dict[str, Any] = Field(default_factory=dict)
