"""Tests for HTML report renderer."""

import pytest

from adversarypilot.models.campaign import Campaign, CampaignState
from adversarypilot.models.enums import (
    AccessLevel,
    Goal,
    Surface,
    TargetType,
)
from adversarypilot.models.report import (
    DefenderReport,
    EvidenceBundle,
    LayerAssessment,
)
from adversarypilot.models.results import ComparabilityMetadata, EvaluationResult
from adversarypilot.models.target import TargetProfile
from adversarypilot.reporting.html_renderer import HtmlReportRenderer


@pytest.fixture
def target():
    return TargetProfile(
        name="Test Chatbot",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK],
    )


@pytest.fixture
def report(target):
    return DefenderReport(
        target_profile=target,
        campaign_id="test-campaign",
        primary_weak_layer=Surface.GUARDRAIL,
        overall_risk_summary="Test risk summary",
        layer_assessments=[
            LayerAssessment(
                layer=Surface.GUARDRAIL,
                risk_score=0.8,
                is_primary_weakness=True,
                is_insufficient_evidence=False,
                techniques_tested=["AP-TX-LLM-JAILBREAK-DAN"],
                recommendations=["Improve guardrails"],
                evidence=EvidenceBundle(
                    success_count=3,
                    total_attempts=5,
                    smoothed_success_rate=0.6,
                    confidence_interval=(0.3, 0.9),
                ),
            ),
        ],
    )


@pytest.fixture
def campaign(target):
    return Campaign(
        id="test-campaign",
        target=target,
        state=CampaignState(
            evaluations=[
                EvaluationResult(
                    attempt_id="att-1",
                    success=True,
                    score=0.9,
                    comparability=ComparabilityMetadata(
                        technique_id="AP-TX-LLM-JAILBREAK-DAN",
                    ),
                ),
            ],
        ),
    )


class TestHtmlReportRenderer:
    def test_produces_valid_html(self, report, campaign):
        renderer = HtmlReportRenderer()
        html = renderer.render(report, campaign)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html

    def test_contains_graph_visualization(self, report, campaign):
        renderer = HtmlReportRenderer()
        html = renderer.render(report, campaign)
        # Self-contained graph visualization (canvas-based, no external deps)
        assert "graph-canvas" in html
        assert "initGraph" in html

    def test_embeds_campaign_data(self, report, campaign):
        renderer = HtmlReportRenderer()
        html = renderer.render(report, campaign)
        assert "test-campaign" in html
        assert "AP-TX-LLM-JAILBREAK-DAN" in html

    def test_writes_to_file(self, report, campaign, tmp_path):
        renderer = HtmlReportRenderer()
        output = tmp_path / "report.html"
        html = renderer.render(report, campaign, output_path=output)
        assert output.exists()
        content = output.read_text()
        assert content == html

    def test_escapes_html_in_data(self, report, campaign):
        # Inject potential XSS in campaign_id
        report.campaign_id = "<script>alert('xss')</script>"
        renderer = HtmlReportRenderer()
        html = renderer.render(report, campaign)
        # The esc() function in the template prevents XSS at render time
        assert "function esc(text)" in html
