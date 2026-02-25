"""Tests for compliance framework mappings and analysis (WS1)."""

import pytest

from adversarypilot.models.enums import AccessLevel, Goal, TargetType
from adversarypilot.models.target import TargetProfile
from adversarypilot.models.technique import ComplianceReference
from adversarypilot.reporting.compliance import (
    ComplianceAnalyzer,
    ComplianceSummary,
    ControlResult,
    EU_AI_ACT,
    FRAMEWORK_CONTROLS,
    NIST_AI_RMF,
    OWASP_LLM_TOP10,
)
from adversarypilot.taxonomy.registry import TechniqueRegistry


@pytest.fixture
def registry():
    r = TechniqueRegistry()
    r.load_catalog()
    return r


@pytest.fixture
def analyzer(registry):
    return ComplianceAnalyzer(registry=registry)


class TestComplianceReference:
    def test_model_creation(self):
        ref = ComplianceReference(
            framework="owasp_llm_top10",
            control_id="LLM01",
            control_name="Prompt Injection",
            relevance="Tests prompt injection defenses",
        )
        assert ref.framework == "owasp_llm_top10"
        assert ref.control_id == "LLM01"

    def test_model_defaults(self):
        ref = ComplianceReference(framework="nist_ai_rmf", control_id="MAP-1.1")
        assert ref.control_name == ""
        assert ref.relevance == ""


class TestFrameworkControlSets:
    def test_owasp_has_10_controls(self):
        assert len(OWASP_LLM_TOP10) == 10

    def test_nist_has_controls(self):
        assert len(NIST_AI_RMF) >= 15

    def test_eu_ai_act_has_controls(self):
        assert len(EU_AI_ACT) >= 5

    def test_all_frameworks_registered(self):
        assert "owasp_llm_top10" in FRAMEWORK_CONTROLS
        assert "nist_ai_rmf" in FRAMEWORK_CONTROLS
        assert "eu_ai_act" in FRAMEWORK_CONTROLS


class TestCatalogComplianceRefs:
    def test_all_techniques_have_compliance_refs(self, registry):
        catalog = registry.get_all()
        for tech in catalog:
            assert len(tech.compliance_refs) > 0, f"{tech.id} has no compliance_refs"

    def test_all_techniques_have_owasp_ref(self, registry):
        catalog = registry.get_all()
        for tech in catalog:
            owasp = [r for r in tech.compliance_refs if r.framework == "owasp_llm_top10"]
            assert len(owasp) > 0, f"{tech.id} has no OWASP ref"

    def test_all_techniques_have_nist_ref(self, registry):
        catalog = registry.get_all()
        for tech in catalog:
            nist = [r for r in tech.compliance_refs if r.framework == "nist_ai_rmf"]
            assert len(nist) > 0, f"{tech.id} has no NIST ref"

    def test_all_techniques_have_eu_ai_act_ref(self, registry):
        catalog = registry.get_all()
        for tech in catalog:
            eu = [r for r in tech.compliance_refs if r.framework == "eu_ai_act"]
            assert len(eu) > 0, f"{tech.id} has no EU AI Act ref"

    def test_filter_by_framework(self, registry):
        owasp_techs = registry.filter(framework="owasp_llm_top10")
        assert len(owasp_techs) == 70  # All should have OWASP refs


class TestComplianceAnalyzer:
    def test_empty_campaign(self, analyzer):
        summaries = analyzer.analyze(techniques_tried=[])
        assert len(summaries) == 3  # OWASP, NIST, EU AI Act
        for s in summaries:
            assert s.tested_controls == 0
            assert s.coverage_pct == 0.0

    def test_partial_coverage(self, analyzer, registry):
        # Try a few LLM injection techniques
        tried = ["AP-TX-LLM-JAILBREAK-DAN", "AP-TX-LLM-INJECT-DIRECT"]
        summaries = analyzer.analyze(techniques_tried=tried)
        owasp = next(s for s in summaries if s.framework == "owasp_llm_top10")
        assert owasp.tested_controls > 0
        assert owasp.coverage_pct > 0.0

    def test_specific_framework(self, analyzer):
        summaries = analyzer.analyze(
            techniques_tried=["AP-TX-LLM-JAILBREAK-DAN"],
            frameworks=["owasp_llm_top10"],
        )
        assert len(summaries) == 1
        assert summaries[0].framework == "owasp_llm_top10"

    def test_control_results_populated(self, analyzer, registry):
        tried = ["AP-TX-LLM-JAILBREAK-DAN"]
        summaries = analyzer.analyze(techniques_tried=tried)
        owasp = next(s for s in summaries if s.framework == "owasp_llm_top10")
        assert len(owasp.control_results) == 10  # All 10 OWASP controls
        lmm01 = next(c for c in owasp.control_results if c.control_id == "LLM01")
        assert len(lmm01.techniques_tested) > 0

    def test_untested_controls_flagged(self, analyzer):
        summaries = analyzer.analyze(techniques_tried=[])
        owasp = next(s for s in summaries if s.framework == "owasp_llm_top10")
        for ctrl in owasp.control_results:
            assert ctrl.risk_level == "untested"

    def test_summary_model(self):
        s = ComplianceSummary(
            framework="test",
            framework_name="Test Framework",
            total_controls=10,
            tested_controls=5,
            coverage_pct=0.5,
        )
        assert s.coverage_pct == 0.5

    def test_control_result_model(self):
        c = ControlResult(
            control_id="C1",
            control_name="Test Control",
            risk_level="high",
        )
        assert c.risk_level == "high"
        assert c.total_tested == 0
