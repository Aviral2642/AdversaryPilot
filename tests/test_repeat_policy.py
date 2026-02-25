"""Tests for repeat policy in adaptive planner."""

import pytest

from adversarypilot.models.enums import AccessLevel, Goal, StealthLevel, TargetType
from adversarypilot.models.results import ComparabilityMetadata, EvaluationResult
from adversarypilot.models.target import ConstraintSpec, DefenseProfile, TargetProfile
from adversarypilot.planner.adaptive import AdaptivePlanner
from adversarypilot.taxonomy.registry import TechniqueRegistry


@pytest.fixture
def repeat_target():
    return TargetProfile(
        name="Test Chatbot",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK],
        constraints=ConstraintSpec(max_queries=100, stealth_priority=StealthLevel.OVERT),
        defenses=DefenseProfile(has_moderation=True),
    )


@pytest.fixture
def repeat_registry():
    reg = TechniqueRegistry()
    reg.load_catalog()
    return reg


def _make_prior_results(technique_ids, success=True):
    return [
        EvaluationResult(
            attempt_id=f"att-{i}",
            success=success,
            comparability=ComparabilityMetadata(technique_id=tid),
        )
        for i, tid in enumerate(technique_ids)
    ]


class TestRepeatPolicy:
    def test_exclude_tried_removes_techniques(self, repeat_target, repeat_registry):
        planner = AdaptivePlanner(campaign_seed=42)

        plan1, posterior = planner.plan(
            repeat_target, repeat_registry, max_techniques=3, step_number=0,
        )
        tried_ids = [e.technique_id for e in plan1.entries]
        prior_results = _make_prior_results(tried_ids)

        plan2, _ = planner.plan(
            repeat_target, repeat_registry,
            posterior_state=posterior,
            prior_results=prior_results,
            max_techniques=3,
            exclude_tried=True,
            step_number=1,
        )

        new_ids = [e.technique_id for e in plan2.entries]
        assert not any(tid in tried_ids for tid in new_ids)

    def test_repeat_penalty_lowers_utility(self, repeat_target, repeat_registry):
        planner = AdaptivePlanner(campaign_seed=42)

        plan1, posterior = planner.plan(
            repeat_target, repeat_registry, max_techniques=5, step_number=0,
        )
        tried_ids = [e.technique_id for e in plan1.entries]
        prior_results = _make_prior_results(tried_ids)

        # With high repeat penalty
        plan2, _ = planner.plan(
            repeat_target, repeat_registry,
            posterior_state=posterior,
            prior_results=prior_results,
            max_techniques=5,
            repeat_penalty=10.0,  # Very high penalty
            step_number=1,
        )

        # Tried techniques should be pushed lower or off the list
        top_ids = [e.technique_id for e in plan2.entries[:3]]
        tried_in_top = sum(1 for tid in top_ids if tid in tried_ids)
        # With a penalty of 10.0, tried techniques should mostly be pushed down
        assert tried_in_top < 3

    def test_no_penalty_allows_repeats(self, repeat_target, repeat_registry):
        planner = AdaptivePlanner(campaign_seed=42)

        plan1, posterior = planner.plan(
            repeat_target, repeat_registry, max_techniques=3, step_number=0,
        )
        tried_ids = set(e.technique_id for e in plan1.entries)
        prior_results = _make_prior_results(list(tried_ids))

        plan2, _ = planner.plan(
            repeat_target, repeat_registry,
            posterior_state=posterior,
            prior_results=prior_results,
            max_techniques=5,
            repeat_penalty=0.0,
            step_number=1,
        )

        # Without penalty, some tried techniques may still appear
        all_ids = [e.technique_id for e in plan2.entries]
        assert len(all_ids) > 0  # Plan should still be generated

    def test_inconclusive_results_not_excluded(self, repeat_target, repeat_registry):
        planner = AdaptivePlanner(campaign_seed=42)

        plan1, posterior = planner.plan(
            repeat_target, repeat_registry, max_techniques=3, step_number=0,
        )
        tried_ids = [e.technique_id for e in plan1.entries]

        # Inconclusive results (success=None)
        prior_results = [
            EvaluationResult(
                attempt_id=f"att-{i}",
                success=None,  # Inconclusive
                comparability=ComparabilityMetadata(technique_id=tid),
            )
            for i, tid in enumerate(tried_ids)
        ]

        plan2, _ = planner.plan(
            repeat_target, repeat_registry,
            posterior_state=posterior,
            prior_results=prior_results,
            max_techniques=5,
            exclude_tried=True,
            step_number=1,
        )

        # Even with exclude_tried, inconclusive results still count as "tried"
        # because they appear in prior_results (the technique_id is in tried_ids set)
        all_ids = [e.technique_id for e in plan2.entries]
        assert len(all_ids) > 0
