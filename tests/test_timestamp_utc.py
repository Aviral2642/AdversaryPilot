"""Tests for UTC timestamp consistency across all models."""

from datetime import timezone

from adversarypilot.models.campaign import Campaign, CampaignState
from adversarypilot.models.enums import AccessLevel, Goal, TargetType
from adversarypilot.models.report import DefenderReport
from adversarypilot.models.results import AttemptResult, EvaluationResult
from adversarypilot.models.target import TargetProfile
from adversarypilot.planner.posterior import PosteriorState
from adversarypilot.replay.snapshot import DecisionSnapshot
from adversarypilot.utils.timestamps import utc_now


def _target():
    return TargetProfile(
        name="Test",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK],
    )


class TestUtcTimestamps:
    def test_utc_now_is_aware(self):
        now = utc_now()
        assert now.tzinfo is not None
        assert now.tzinfo == timezone.utc

    def test_attempt_result_timestamp(self):
        r = AttemptResult(id="a1", technique_id="t1")
        assert r.timestamp.tzinfo is not None

    def test_evaluation_result_no_timestamp(self):
        # EvaluationResult doesn't have a timestamp field, just verify it works
        e = EvaluationResult(attempt_id="a1")
        assert e.attempt_id == "a1"

    def test_campaign_created_at(self):
        c = Campaign(id="c1", target=_target())
        assert c.created_at.tzinfo is not None

    def test_campaign_state_last_updated(self):
        s = CampaignState()
        assert s.last_updated.tzinfo is not None

    def test_defender_report_generated_at(self):
        r = DefenderReport(target_profile=_target(), campaign_id="c1")
        assert r.generated_at.tzinfo is not None

    def test_snapshot_timestamp(self):
        s = DecisionSnapshot(
            snapshot_id="s1",
            campaign_id="c1",
            step_number=0,
            step_seed=42,
            posterior_state=PosteriorState(),
        )
        assert s.timestamp.tzinfo is not None
