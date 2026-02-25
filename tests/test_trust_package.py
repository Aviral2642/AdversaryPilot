"""Tests for trust package — audit trail, reproducibility, assessment quality (WS3)."""

import pytest

from adversarypilot.models.enums import AccessLevel, Goal, Surface, TargetType
from adversarypilot.models.report import (
    AssessmentQuality,
    AuditTrail,
    DefenderReport,
    EvidenceBundle,
    LayerAssessment,
    ReproducibilityMetadata,
)
from adversarypilot.models.target import TargetProfile
from adversarypilot.reporting.analyzer import compute_assessment_quality
from adversarypilot.utils.hashing import compute_reproducibility_token, hash_file


@pytest.fixture
def target():
    return TargetProfile(
        name="test",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK],
    )


@pytest.fixture
def sample_assessments():
    return [
        LayerAssessment(
            layer=Surface.MODEL,
            evidence=EvidenceBundle(
                success_count=3,
                total_attempts=5,
                smoothed_success_rate=0.6,
                evidence_quality=0.7,
            ),
            risk_score=0.4,
            is_insufficient_evidence=False,
            techniques_tested=["T1", "T2"],
        ),
        LayerAssessment(
            layer=Surface.GUARDRAIL,
            evidence=EvidenceBundle(
                success_count=1,
                total_attempts=8,
                smoothed_success_rate=0.12,
                evidence_quality=0.8,
            ),
            risk_score=0.1,
            is_insufficient_evidence=False,
            techniques_tested=["T3"],
        ),
        LayerAssessment(
            layer=Surface.DATA,
            evidence=EvidenceBundle(),
            is_insufficient_evidence=True,
        ),
    ]


class TestAuditTrail:
    def test_model_creation(self):
        audit = AuditTrail(
            operator="test-user",
            tool_version="1.0.0",
            config_hash="abc123",
            catalog_hash="def456",
        )
        assert audit.operator == "test-user"
        assert audit.tool_version == "1.0.0"

    def test_defaults(self):
        audit = AuditTrail()
        assert audit.operator == ""
        assert audit.run_timestamp is not None


class TestReproducibilityMetadata:
    def test_model_creation(self):
        repro = ReproducibilityMetadata(
            campaign_seed=42,
            deterministic=True,
            catalog_version="1.1",
            reproducibility_token="tok123",
        )
        assert repro.campaign_seed == 42
        assert repro.deterministic is True

    def test_defaults(self):
        repro = ReproducibilityMetadata()
        assert repro.campaign_seed is None
        assert repro.reproducibility_token == ""


class TestAssessmentQuality:
    def test_model_creation(self):
        q = AssessmentQuality(
            overall_score=0.75,
            evidence_depth=0.8,
            coverage_breadth=0.6,
            statistical_power=0.9,
            comparability_score=0.7,
        )
        assert q.overall_score == 0.75

    def test_defaults_to_zero(self):
        q = AssessmentQuality()
        assert q.overall_score == 0.0


class TestComputeAssessmentQuality:
    def test_empty_assessments(self):
        q = compute_assessment_quality([])
        assert q.overall_score == 0.0

    def test_with_assessments(self, sample_assessments):
        q = compute_assessment_quality(sample_assessments)
        assert 0.0 <= q.overall_score <= 1.0
        assert q.evidence_depth > 0
        assert q.coverage_breadth > 0
        assert q.statistical_power > 0

    def test_warnings_reduce_comparability(self, sample_assessments):
        q1 = compute_assessment_quality(sample_assessments, warnings=[])
        q2 = compute_assessment_quality(sample_assessments, warnings=["w1", "w2", "w3"])
        assert q2.comparability_score < q1.comparability_score

    def test_more_evidence_higher_power(self):
        high_evidence = [
            LayerAssessment(
                layer=Surface.MODEL,
                evidence=EvidenceBundle(total_attempts=20, evidence_quality=0.8),
                is_insufficient_evidence=False,
            ),
        ]
        low_evidence = [
            LayerAssessment(
                layer=Surface.MODEL,
                evidence=EvidenceBundle(total_attempts=2, evidence_quality=0.8),
                is_insufficient_evidence=True,
            ),
        ]
        q_high = compute_assessment_quality(high_evidence)
        q_low = compute_assessment_quality(low_evidence)
        assert q_high.statistical_power > q_low.statistical_power

    def test_factors_populated(self, sample_assessments):
        q = compute_assessment_quality(sample_assessments)
        assert "total_attempts" in q.factors
        assert "layers_sufficient" in q.factors


class TestDefenderReportTrustFields:
    def test_report_has_trust_fields(self, target):
        report = DefenderReport(
            target_profile=target,
            campaign_id="test-campaign",
            audit_trail=AuditTrail(operator="tester"),
            reproducibility=ReproducibilityMetadata(campaign_seed=42),
            assessment_quality=AssessmentQuality(overall_score=0.8),
        )
        assert report.audit_trail.operator == "tester"
        assert report.reproducibility.campaign_seed == 42
        assert report.assessment_quality.overall_score == 0.8

    def test_report_schema_version(self, target):
        report = DefenderReport(target_profile=target, campaign_id="test")
        assert report.schema_version == "1.1"


class TestHashFile:
    def test_hash_file(self, tmp_path):
        p = tmp_path / "test.txt"
        p.write_text("hello world")
        h = hash_file(str(p))
        assert len(h) == 16
        assert isinstance(h, str)

    def test_hash_deterministic(self, tmp_path):
        p = tmp_path / "test.txt"
        p.write_text("hello world")
        h1 = hash_file(str(p))
        h2 = hash_file(str(p))
        assert h1 == h2

    def test_different_content_different_hash(self, tmp_path):
        p1 = tmp_path / "a.txt"
        p2 = tmp_path / "b.txt"
        p1.write_text("hello")
        p2.write_text("world")
        assert hash_file(str(p1)) != hash_file(str(p2))


class TestReproducibilityToken:
    def test_compute_token(self):
        audit = {"config_hash": "abc", "catalog_hash": "def", "target_profile_hash": "ghi"}
        repro = {"campaign_seed": 42, "catalog_version": "1.1"}
        token = compute_reproducibility_token(audit, repro)
        assert len(token) == 16

    def test_token_deterministic(self):
        audit = {"config_hash": "abc", "catalog_hash": "def"}
        repro = {"campaign_seed": 42}
        t1 = compute_reproducibility_token(audit, repro)
        t2 = compute_reproducibility_token(audit, repro)
        assert t1 == t2

    def test_different_inputs_different_tokens(self):
        audit1 = {"config_hash": "abc"}
        audit2 = {"config_hash": "xyz"}
        repro = {"campaign_seed": 42}
        t1 = compute_reproducibility_token(audit1, repro)
        t2 = compute_reproducibility_token(audit2, repro)
        assert t1 != t2
