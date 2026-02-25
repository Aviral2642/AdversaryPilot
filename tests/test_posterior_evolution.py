"""Tests for posterior evolution visualization (WS8)."""

import pytest

from adversarypilot.models.campaign import Campaign, CampaignState
from adversarypilot.models.enums import AccessLevel, CampaignPhase, Goal, TargetType
from adversarypilot.models.target import TargetProfile


@pytest.fixture
def target():
    return TargetProfile(
        name="test",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK],
    )


@pytest.fixture
def sample_history():
    return [
        {
            "step": 0,
            "phase": "probe",
            "posteriors": {
                "T1": {"alpha": 1.0, "beta": 1.0, "mean": 0.5},
                "T2": {"alpha": 1.0, "beta": 1.0, "mean": 0.5},
            },
        },
        {
            "step": 1,
            "phase": "probe",
            "posteriors": {
                "T1": {"alpha": 2.0, "beta": 1.0, "mean": 0.667},
                "T2": {"alpha": 1.0, "beta": 2.0, "mean": 0.333},
            },
        },
        {
            "step": 2,
            "phase": "exploit",
            "posteriors": {
                "T1": {"alpha": 3.0, "beta": 1.0, "mean": 0.75},
                "T2": {"alpha": 1.0, "beta": 3.0, "mean": 0.25},
            },
        },
    ]


class TestCampaignPosteriorHistory:
    def test_campaign_has_posterior_history(self, target):
        c = Campaign(id="test", target=target)
        assert c.posterior_history == []

    def test_campaign_with_history(self, target, sample_history):
        c = Campaign(id="test", target=target, posterior_history=sample_history)
        assert len(c.posterior_history) == 3

    def test_history_snapshot_structure(self, target, sample_history):
        c = Campaign(id="test", target=target, posterior_history=sample_history)
        snap = c.posterior_history[0]
        assert "step" in snap
        assert "phase" in snap
        assert "posteriors" in snap

    def test_posteriors_have_stats(self, target, sample_history):
        c = Campaign(id="test", target=target, posterior_history=sample_history)
        post = c.posterior_history[1]["posteriors"]["T1"]
        assert "alpha" in post
        assert "beta" in post
        assert "mean" in post

    def test_history_evolution(self, target, sample_history):
        c = Campaign(id="test", target=target, posterior_history=sample_history)
        # T1's mean should increase over steps (successes)
        means = [
            snap["posteriors"]["T1"]["mean"]
            for snap in c.posterior_history
        ]
        assert means[0] < means[-1]

    def test_phase_transitions_tracked(self, target, sample_history):
        c = Campaign(id="test", target=target, posterior_history=sample_history)
        phases = [snap["phase"] for snap in c.posterior_history]
        assert "probe" in phases
        assert "exploit" in phases


class TestHtmlRendererPosteriorEvolution:
    def test_build_posterior_evolution_empty(self, target):
        from adversarypilot.reporting.html_renderer import HtmlReportRenderer
        renderer = HtmlReportRenderer()
        campaign = Campaign(id="test", target=target)
        result = renderer._build_posterior_evolution(campaign)
        assert result is None

    def test_build_posterior_evolution_with_data(self, target, sample_history):
        from adversarypilot.reporting.html_renderer import HtmlReportRenderer
        renderer = HtmlReportRenderer()
        campaign = Campaign(id="test", target=target, posterior_history=sample_history)
        result = renderer._build_posterior_evolution(campaign)
        assert result is not None
        assert len(result) == 3

    def test_data_payload_includes_evolution(self, target, sample_history):
        from adversarypilot.models.report import DefenderReport
        from adversarypilot.reporting.html_renderer import HtmlReportRenderer
        renderer = HtmlReportRenderer()
        report = DefenderReport(target_profile=target, campaign_id="test")
        campaign = Campaign(id="test", target=target, posterior_history=sample_history)
        data = renderer._build_data_payload(report, campaign)
        assert "posterior_evolution" in data
        assert data["posterior_evolution"] is not None
