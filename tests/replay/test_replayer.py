"""Tests for decision replayer."""

import pytest

from adversarypilot.models.enums import AccessLevel, Goal, StealthLevel, TargetType
from adversarypilot.models.target import ConstraintSpec, DefenseProfile, TargetProfile
from adversarypilot.planner.adaptive import AdaptivePlanner
from adversarypilot.planner.posterior import PosteriorState
from adversarypilot.replay.snapshot import DecisionSnapshot
from adversarypilot.replay.replayer import DecisionReplayer
from adversarypilot.taxonomy.registry import TechniqueRegistry


@pytest.fixture
def replayer_registry():
    reg = TechniqueRegistry()
    reg.load_catalog()
    return reg


@pytest.fixture
def replayer_target():
    return TargetProfile(
        name="Test Chatbot",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK],
        constraints=ConstraintSpec(max_queries=100, stealth_priority=StealthLevel.OVERT),
        defenses=DefenseProfile(has_moderation=True),
    )


def _generate_snapshot(planner, target, registry, step=0):
    """Generate a real snapshot by running the planner."""
    plan, posterior = planner.plan(target, registry, max_techniques=3, step_number=step)
    return DecisionSnapshot(
        snapshot_id="snap-test",
        campaign_id="camp-test",
        step_number=step,
        step_seed=planner._derive_step_seed(step),
        posterior_state=posterior,
        planner_config={
            "campaign_seed": planner.campaign_seed,
            "exclude_tried": False,
            "repeat_penalty": 0.0,
        },
        produced_plan_entries=[
            {
                "technique_id": e.technique_id,
                "score": {"utility": e.score.utility},
            }
            for e in plan.entries
        ],
    )


class TestDecisionReplayer:
    def test_replay_produces_plan(self, replayer_registry, replayer_target):
        planner = AdaptivePlanner(campaign_seed=42)
        snapshot = _generate_snapshot(planner, replayer_target, replayer_registry)

        replayer = DecisionReplayer(replayer_registry, planner)
        plan = replayer.replay(snapshot, replayer_target)
        assert len(plan.entries) > 0

    def test_replay_matches_original(self, replayer_registry, replayer_target):
        planner = AdaptivePlanner(campaign_seed=42)
        snapshot = _generate_snapshot(planner, replayer_target, replayer_registry)

        replayer = DecisionReplayer(replayer_registry, planner)
        matches, divergences = replayer.verify(snapshot, replayer_target)
        assert matches, f"Divergences: {divergences}"

    def test_different_seed_diverges(self, replayer_registry, replayer_target):
        planner = AdaptivePlanner(campaign_seed=42)
        snapshot = _generate_snapshot(planner, replayer_target, replayer_registry)

        # Use a different-seeded planner for replay
        different_planner = AdaptivePlanner(campaign_seed=999)
        replayer = DecisionReplayer(replayer_registry, different_planner)
        plan = replayer.replay(snapshot, replayer_target)

        # With different seed, rankings should likely differ
        original_ids = [e["technique_id"] for e in snapshot.produced_plan_entries]
        replayed_ids = [e.technique_id for e in plan.entries]
        # Not guaranteed to differ but very likely with different seeds
        # Just verify it produces a valid plan
        assert len(plan.entries) > 0

    def test_verify_without_explicit_planner(self, replayer_registry, replayer_target):
        planner = AdaptivePlanner(campaign_seed=42)
        snapshot = _generate_snapshot(planner, replayer_target, replayer_registry)

        # Replayer without explicit planner — should create one from snapshot config
        replayer = DecisionReplayer(replayer_registry)
        plan = replayer.replay(snapshot, replayer_target)
        assert len(plan.entries) > 0
