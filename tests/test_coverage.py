"""Tests for coverage gap detection (WS5)."""

import pytest

from adversarypilot.models.enums import Goal
from adversarypilot.reporting.coverage import CoverageAnalyzer, CoverageGap, CoverageReport
from adversarypilot.taxonomy.registry import TechniqueRegistry


@pytest.fixture
def registry():
    r = TechniqueRegistry()
    r.load_catalog()
    return r


@pytest.fixture
def analyzer(registry):
    return CoverageAnalyzer(registry=registry)


class TestCoverageAnalyzer:
    def test_empty_tried_has_many_gaps(self, analyzer):
        report = analyzer.analyze([])
        assert len(report.gaps) > 0
        assert report.atlas_coverage == 0.0

    def test_partial_coverage(self, analyzer, registry):
        some_ids = [t.id for t in registry.get_all()[:5]]
        report = analyzer.analyze(some_ids)
        assert 0.0 < report.atlas_coverage < 1.0
        assert len(report.gaps) > 0

    def test_full_coverage_no_surface_gaps(self, analyzer, registry):
        all_ids = [t.id for t in registry.get_all()]
        report = analyzer.analyze(all_ids)
        surface_gaps = [g for g in report.gaps if g.gap_type == "surface"]
        assert len(surface_gaps) == 0

    def test_untested_surface_is_high_severity(self, analyzer):
        report = analyzer.analyze([])
        surface_gaps = [g for g in report.gaps if g.gap_type == "surface"]
        for g in surface_gaps:
            assert g.severity == "high"

    def test_untested_goal_is_high_severity(self, analyzer):
        report = analyzer.analyze([], target_goals=[Goal.JAILBREAK])
        goal_gaps = [g for g in report.gaps if g.gap_type == "goal"]
        for g in goal_gaps:
            assert g.severity == "high"

    def test_atlas_gap_is_medium_severity(self, analyzer):
        report = analyzer.analyze([])
        atlas_gaps = [g for g in report.gaps if g.gap_type == "atlas"]
        for g in atlas_gaps:
            assert g.severity == "medium"

    def test_phase_gap_is_low_severity(self, analyzer):
        report = analyzer.analyze([])
        phase_gaps = [g for g in report.gaps if g.gap_type == "phase"]
        for g in phase_gaps:
            assert g.severity == "low"

    def test_gaps_sorted_by_severity(self, analyzer):
        report = analyzer.analyze([])
        severity_order = {"high": 0, "medium": 1, "low": 2}
        for i in range(len(report.gaps) - 1):
            curr = severity_order[report.gaps[i].severity]
            next_ = severity_order[report.gaps[i + 1].severity]
            assert curr <= next_

    def test_surface_coverage_dict(self, analyzer, registry):
        all_ids = [t.id for t in registry.get_all()]
        report = analyzer.analyze(all_ids)
        assert "model" in report.surface_coverage
        assert "guardrail" in report.surface_coverage

    def test_suggested_techniques_populated(self, analyzer):
        report = analyzer.analyze([])
        surface_gaps = [g for g in report.gaps if g.gap_type == "surface"]
        for g in surface_gaps:
            assert len(g.suggested_techniques) > 0

    def test_goal_coverage_with_specific_goals(self, analyzer, registry):
        some_ids = [t.id for t in registry.get_all()[:3]]
        report = analyzer.analyze(some_ids, target_goals=[Goal.JAILBREAK, Goal.EVASION])
        assert "jailbreak" in report.goal_coverage
        assert "evasion" in report.goal_coverage

    def test_phase_coverage_dict(self, analyzer):
        report = analyzer.analyze([])
        assert "recon" in report.phase_coverage
        assert "exploit" in report.phase_coverage
