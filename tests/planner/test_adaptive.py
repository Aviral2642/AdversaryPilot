"""Tests for adaptive planner."""

from adversarypilot.models.enums import Goal
from adversarypilot.planner.adaptive import AdaptivePlanner
from adversarypilot.planner.posterior import PosteriorState
from adversarypilot.taxonomy.registry import TechniqueRegistry


def test_adaptive_planner_basic(chatbot_target):
    """Test basic adaptive planner functionality."""
    registry = TechniqueRegistry()
    registry.load_catalog()

    planner = AdaptivePlanner(campaign_seed=42)
    plan, posterior = planner.plan(
        chatbot_target, registry, max_techniques=5, step_number=0
    )

    assert len(plan.entries) <= 5
    assert posterior is not None
    assert len(posterior.posteriors) > 0


def test_adaptive_planner_deterministic(chatbot_target):
    """Test that same seed produces same results."""
    registry = TechniqueRegistry()
    registry.load_catalog()

    planner1 = AdaptivePlanner(campaign_seed=42)
    plan1, _ = planner1.plan(chatbot_target, registry, step_number=0)

    planner2 = AdaptivePlanner(campaign_seed=42)
    plan2, _ = planner2.plan(chatbot_target, registry, step_number=0)

    # Same seed should produce same rankings
    assert [e.technique_id for e in plan1.entries] == [
        e.technique_id for e in plan2.entries
    ]


def test_adaptive_planner_different_seeds(chatbot_target):
    """Test that different seeds produce different results."""
    registry = TechniqueRegistry()
    registry.load_catalog()

    planner1 = AdaptivePlanner(campaign_seed=42)
    plan1, _ = planner1.plan(chatbot_target, registry, step_number=0)

    planner2 = AdaptivePlanner(campaign_seed=123)
    plan2, _ = planner2.plan(chatbot_target, registry, step_number=0)

    # Different seeds should likely produce different rankings
    # (not guaranteed, but very likely for 5+ techniques)
    assert [e.technique_id for e in plan1.entries] != [
        e.technique_id for e in plan2.entries
    ]


def test_adaptive_planner_exclude_tried(chatbot_target):
    """Test exclude_tried parameter."""
    registry = TechniqueRegistry()
    registry.load_catalog()

    planner = AdaptivePlanner(campaign_seed=42)

    # First plan
    plan1, posterior = planner.plan(chatbot_target, registry, max_techniques=3, step_number=0)

    # Get IDs from first plan
    tried_ids = [e.technique_id for e in plan1.entries]

    # Second plan with exclude_tried and fake prior results
    from adversarypilot.models.results import EvaluationResult, ComparabilityMetadata

    fake_results = [
        EvaluationResult(
            attempt_id=f"att-{i}",
            success=True,
            comparability=ComparabilityMetadata(technique_id=tid),
        )
        for i, tid in enumerate(tried_ids)
    ]

    plan2, _ = planner.plan(
        chatbot_target,
        registry,
        posterior_state=posterior,
        prior_results=fake_results,
        max_techniques=3,
        exclude_tried=True,
        step_number=1,
    )

    # Should not repeat any techniques
    new_ids = [e.technique_id for e in plan2.entries]
    assert not any(tid in tried_ids for tid in new_ids)


def test_adaptive_planner_repeat_penalty(chatbot_target):
    """Test repeat_penalty parameter."""
    registry = TechniqueRegistry()
    registry.load_catalog()

    planner = AdaptivePlanner(campaign_seed=42)

    # First plan
    plan1, posterior = planner.plan(chatbot_target, registry, max_techniques=3, step_number=0)

    # Second plan with repeat penalty
    plan2, _ = planner.plan(
        chatbot_target,
        registry,
        posterior_state=posterior,
        max_techniques=3,
        repeat_penalty=0.5,
        step_number=1,
    )

    # Should produce a plan (may or may not repeat techniques depending on utility)
    assert len(plan2.entries) > 0


def test_update_posteriors(chatbot_target):
    """Test posterior update functionality."""
    registry = TechniqueRegistry()
    registry.load_catalog()

    planner = AdaptivePlanner()
    posterior = PosteriorState()

    # Create fake evaluation results
    from adversarypilot.models.results import EvaluationResult, ComparabilityMetadata

    results = [
        EvaluationResult(
            attempt_id="att-1",
            success=True,
            comparability=ComparabilityMetadata(technique_id="AP-TX-LLM-JAILBREAK-DAN"),
        ),
        EvaluationResult(
            attempt_id="att-2",
            success=False,
            comparability=ComparabilityMetadata(technique_id="AP-TX-LLM-JAILBREAK-DAN"),
        ),
    ]

    updated_posterior = planner.update_posteriors(posterior, results, registry, chatbot_target)

    # Should have updated the posterior for the technique
    assert "AP-TX-LLM-JAILBREAK-DAN" in updated_posterior.posteriors
    post = updated_posterior.posteriors["AP-TX-LLM-JAILBREAK-DAN"]
    assert post.observations == 2


def test_utility_fields_populated(chatbot_target):
    """Test that utility fields are populated in plan entries."""
    registry = TechniqueRegistry()
    registry.load_catalog()

    planner = AdaptivePlanner(campaign_seed=42)
    plan, _ = planner.plan(chatbot_target, registry, max_techniques=3, step_number=0)

    for entry in plan.entries:
        assert entry.score.thompson_sample is not None
        assert entry.score.utility is not None
