"""Defender report models — synthesized findings with evidence bundles."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from adversarypilot.models.enums import Surface
from adversarypilot.models.target import TargetProfile
from adversarypilot.utils.timestamps import utc_now


class EvidenceBundle(BaseModel):
    """Evidence supporting a claim about a specific layer's weakness."""

    supporting_attempt_ids: list[str] = Field(default_factory=list)
    success_count: int = 0
    total_attempts: int = 0
    smoothed_success_rate: float = 0.0
    confidence_interval: tuple[float, float] = (0.0, 1.0)
    confidence_method: str = "wilson"
    evidence_quality: float = Field(0.0, ge=0.0, le=1.0)
    caveats: list[str] = Field(default_factory=list)


class LayerAssessment(BaseModel):
    """Assessment of a single attack surface layer."""

    layer: Surface
    evidence: EvidenceBundle = Field(default_factory=EvidenceBundle)
    risk_score: float = Field(0.0, ge=0.0, le=1.0)
    is_primary_weakness: bool = False
    is_insufficient_evidence: bool = True
    techniques_tested: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    calibrated_z_score: float | None = None
    baseline_reference: dict[str, Any] = Field(default_factory=dict)


class AuditTrail(BaseModel):
    """Audit trail metadata for reproducibility."""

    operator: str = ""
    tool_version: str = ""
    run_timestamp: datetime = Field(default_factory=utc_now)
    config_hash: str = ""
    catalog_hash: str = ""
    target_profile_hash: str = ""
    command_line: str = ""
    environment: dict[str, str] = Field(default_factory=dict)


class ReproducibilityMetadata(BaseModel):
    """Metadata for reproducing a campaign run."""

    campaign_seed: int | None = None
    deterministic: bool = False
    catalog_version: str = ""
    config_version: str = ""
    reproducibility_token: str = ""


class AssessmentQuality(BaseModel):
    """Overall quality score for the assessment."""

    overall_score: float = Field(0.0, ge=0.0, le=1.0)
    evidence_depth: float = Field(0.0, ge=0.0, le=1.0)
    coverage_breadth: float = Field(0.0, ge=0.0, le=1.0)
    statistical_power: float = Field(0.0, ge=0.0, le=1.0)
    comparability_score: float = Field(0.0, ge=0.0, le=1.0)
    factors: dict[str, Any] = Field(default_factory=dict)


class DefenderReport(BaseModel):
    """Complete defender-facing report with weakest layer hypothesis."""

    schema_version: str = "1.1"
    target_profile: TargetProfile
    campaign_id: str
    generated_at: datetime = Field(default_factory=utc_now)
    layer_assessments: list[LayerAssessment] = Field(default_factory=list)
    primary_weak_layer: Surface | None = None
    secondary_weak_layers: list[Surface] = Field(default_factory=list)
    overall_risk_summary: str = ""
    comparability_warnings: list[str] = Field(default_factory=list)
    next_recommended_tests: list[str] = Field(default_factory=list)
    atlas_coverage: float = 0.0
    coverage_gaps: list[dict[str, Any]] = Field(default_factory=list)
    compliance_summaries: list[dict[str, Any]] = Field(default_factory=list)
    attack_paths: list[dict[str, Any]] = Field(default_factory=list)
    audit_trail: AuditTrail | None = None
    reproducibility: ReproducibilityMetadata | None = None
    assessment_quality: AssessmentQuality | None = None
    raw_statistics: dict[str, Any] = Field(default_factory=dict)
