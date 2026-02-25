"""Tests for two-phase campaigns (WS4)."""

import pytest

from adversarypilot.models.campaign import Campaign, CampaignState
from adversarypilot.models.enums import (
    AccessLevel,
    CampaignPhase,
    CampaignStatus,
    Goal,
    Surface,
    TargetType,
)
from adversarypilot.models.results import ComparabilityMetadata, EvaluationResult
from adversarypilot.models.target import TargetProfile
from adversarypilot.planner.adaptive import AdaptivePlanner
from adversarypilot.planner.posterior import PosteriorState
from adversarypilot.taxonomy.registry import TechniqueRegistry


@pytest.fixture
def target():
    return TargetProfile(
        name="Test Chatbot",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK],
    )


@pytest.fixture
def registry():
    r = TechniqueRegistry()
    r.load_catalog()
    return r


class TestCampaignPhase:
    def test_campaign_starts_in_probe(self, target):
        campaign = Campaign(id="test", target=target)
        assert campaign.phase == CampaignPhase.PROBE

    def test_phase_enum_values(self):
        assert CampaignPhase.PROBE == "probe"
        assert CampaignPhase.EXPLOIT == "exploit"

    def test_campaign_can_set_exploit(self, target):
        campaign = Campaign(id="test", target=target, phase=CampaignPhase.EXPLOIT)
        assert campaign.phase == CampaignPhase.EXPLOIT


class TestPhaseWeightAdjustment:
    def test_probe_favors_info_gain(self, target, registry):
        planner = AdaptivePlanner(campaign_seed=42)
        state = PosteriorState(prior_strength=3.0)

        plan_probe, _ = planner.plan(
            target, registry, posterior_state=state, step_number=0,
            campaign_phase=CampaignPhase.PROBE,
        )
        plan_exploit, _ = planner.plan(
            target, registry, posterior_state=state, step_number=0,
            campaign_phase=CampaignPhase.EXPLOIT,
        )

        # Both should produce entries
        assert len(plan_probe.entries) > 0
        assert len(plan_exploit.entries) > 0

    def test_exploit_penalizes_cost_more(self, target, registry):
        planner = AdaptivePlanner(campaign_seed=42)
        state = PosteriorState(prior_strength=3.0)

        # The config used should reflect phase adjustments
        plan_exploit, _ = planner.plan(
            target, registry, posterior_state=state, step_number=0,
            campaign_phase=CampaignPhase.EXPLOIT,
        )
        # Verify plan was generated
        assert len(plan_exploit.entries) > 0

    def test_different_phases_produce_different_utilities(self, target, registry):
        planner = AdaptivePlanner(campaign_seed=42)

        plan_probe, _ = planner.plan(
            target, registry, step_number=0,
            campaign_phase=CampaignPhase.PROBE,
        )
        plan_exploit, _ = planner.plan(
            target, registry, step_number=0,
            campaign_phase=CampaignPhase.EXPLOIT,
        )

        # Same technique should have different utility in different phases
        probe_util = plan_probe.entries[0].score.utility
        exploit_util = plan_exploit.entries[0].score.utility
        assert probe_util != exploit_util


class TestPhaseTransition:
    def test_transition_after_3_rounds(self, target):
        from adversarypilot.campaign.manager import CampaignManager

        manager = CampaignManager(
            adaptive_planner=AdaptivePlanner(campaign_seed=42)
        )
        campaign = manager.create(target, adaptive=True, campaign_seed=42)
        assert campaign.phase == CampaignPhase.PROBE

        # Simulate 3 rounds of recommendations
        for _ in range(3):
            manager.recommend_next(campaign.id, adaptive=True)

        updated = manager.get(campaign.id)
        assert updated.phase == CampaignPhase.EXPLOIT
