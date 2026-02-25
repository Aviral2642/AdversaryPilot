"""Tests for the prioritizer engine."""

from adversarypilot.models.enums import AccessLevel, Goal, TargetType
from adversarypilot.models.target import DefenseProfile, TargetProfile
from adversarypilot.prioritizer.engine import PrioritizerEngine
from adversarypilot.prioritizer.filters import (
    is_access_sufficient,
    is_goal_relevant,
    is_target_type_compatible,
    passes_all_filters,
)
from adversarypilot.prioritizer.scorers import (
    score_access_fit,
    score_compatibility,
    score_cost_penalty,
    score_defense_bypass_likelihood,
    score_goal_fit,
    score_signal_gain,
)
from adversarypilot.taxonomy.registry import TechniqueRegistry


# ─── Filter tests ──────────────────────────────────────────────────────


def test_filter_target_type_compatible(registry, chatbot_target):
    dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
    assert is_target_type_compatible(dan, chatbot_target) is True


def test_filter_target_type_incompatible(registry, chatbot_target):
    fgsm = registry.get("AP-TX-AML-EVASION-FGSM")
    assert is_target_type_compatible(fgsm, chatbot_target) is False


def test_filter_access_sufficient_exact(registry, chatbot_target):
    dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
    assert is_access_sufficient(dan, chatbot_target) is True


def test_filter_access_insufficient(registry):
    target = TargetProfile(
        name="test", target_type="classifier", access_level="black_box", goals=[Goal.EVASION]
    )
    fgsm = registry.get("AP-TX-AML-EVASION-FGSM")  # requires white_box
    assert is_access_sufficient(fgsm, target) is False


def test_filter_goal_relevant(registry, chatbot_target):
    dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
    assert is_goal_relevant(dan, chatbot_target) is True


def test_filter_goal_irrelevant(registry, chatbot_target):
    poison = registry.get("AP-TX-AML-POISON-BACKDOOR")
    assert is_goal_relevant(poison, chatbot_target) is False


def test_passes_all_filters_accept(registry, chatbot_target):
    dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
    assert passes_all_filters(dan, chatbot_target) is True


def test_passes_all_filters_reject(registry, chatbot_target):
    fgsm = registry.get("AP-TX-AML-EVASION-FGSM")
    assert passes_all_filters(fgsm, chatbot_target) is False


# ─── Scorer tests ──────────────────────────────────────────────────────


def test_score_compatibility_match(registry, chatbot_target):
    dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
    assert score_compatibility(dan, chatbot_target) == 1.0


def test_score_compatibility_no_match(registry, chatbot_target):
    fgsm = registry.get("AP-TX-AML-EVASION-FGSM")
    assert score_compatibility(fgsm, chatbot_target) == 0.0


def test_score_access_fit_exact(registry, chatbot_target):
    dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
    assert score_access_fit(dan, chatbot_target) == 1.0


def test_score_goal_fit(registry, chatbot_target):
    dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
    assert score_goal_fit(dan, chatbot_target) > 0


def test_score_defense_bypass(registry, chatbot_target):
    dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
    score = score_defense_bypass_likelihood(dan, chatbot_target)
    assert 0.0 <= score <= 1.0


def test_score_signal_gain_no_prior():
    from adversarypilot.models.technique import AttackTechnique

    t = AttackTechnique(
        id="test", name="test", domain="llm", phase="exploit",
        surface="model", access_required="black_box",
    )
    assert score_signal_gain(t, None) == 0.7


def test_score_cost_penalty(registry):
    dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
    assert score_cost_penalty(dan) == dan.base_cost


# ─── Engine tests ──────────────────────────────────────────────────────


def test_plan_chatbot(registry, chatbot_target):
    engine = PrioritizerEngine()
    plan = engine.plan(chatbot_target, registry)
    assert len(plan.entries) > 0
    # All techniques should be compatible with chatbot + black_box + jailbreak
    for entry in plan.entries:
        t = registry.get(entry.technique_id)
        assert t is not None
        assert passes_all_filters(t, chatbot_target)


def test_plan_classifier(registry, classifier_target):
    engine = PrioritizerEngine()
    plan = engine.plan(classifier_target, registry)
    assert len(plan.entries) > 0
    for entry in plan.entries:
        t = registry.get(entry.technique_id)
        assert t is not None


def test_plan_ranking_order(registry, chatbot_target):
    engine = PrioritizerEngine()
    plan = engine.plan(chatbot_target, registry)
    scores = [e.score.total for e in plan.entries]
    assert scores == sorted(scores, reverse=True)


def test_plan_max_techniques(registry, chatbot_target):
    engine = PrioritizerEngine()
    plan = engine.plan(chatbot_target, registry, max_techniques=3)
    assert len(plan.entries) <= 3


def test_plan_has_rationale(registry, chatbot_target):
    engine = PrioritizerEngine()
    plan = engine.plan(chatbot_target, registry)
    for entry in plan.entries:
        assert entry.rationale != ""
        assert "total=" in entry.rationale
