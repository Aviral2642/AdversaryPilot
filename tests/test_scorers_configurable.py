"""Tests for configurable scorer thresholds (WS2)."""

import pytest

from adversarypilot.models.enums import (
    AccessLevel,
    Goal,
    StealthLevel,
    Surface,
    TargetType,
)
from adversarypilot.models.target import ConstraintSpec, DefenseProfile, TargetProfile
from adversarypilot.models.technique import AttackTechnique
from adversarypilot.prioritizer.scorers import (
    DEFAULT_THRESHOLDS,
    _get,
    score_access_fit,
    score_compatibility,
    score_defense_bypass_likelihood,
    score_detection_risk_penalty,
    score_signal_gain,
)
from adversarypilot.taxonomy.registry import TechniqueRegistry


@pytest.fixture
def registry():
    r = TechniqueRegistry()
    r.load_catalog()
    return r


@pytest.fixture
def chatbot_target():
    return TargetProfile(
        name="test-chatbot",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK, Goal.EXFIL_SIM],
    )


@pytest.fixture
def dan_technique(registry):
    return registry.get("AP-TX-LLM-JAILBREAK-DAN")


class TestGetHelper:
    def test_returns_default_when_no_thresholds(self):
        val = _get(None, "compatibility", "exact_match")
        assert val == 1.0

    def test_returns_default_when_key_missing(self):
        val = _get({"compatibility": {}}, "compatibility", "exact_match")
        assert val == 1.0

    def test_returns_override_value(self):
        val = _get({"compatibility": {"exact_match": 0.9}}, "compatibility", "exact_match")
        assert val == 0.9

    def test_returns_default_when_section_missing(self):
        val = _get({"other": {"x": 1}}, "compatibility", "exact_match")
        assert val == 1.0

    def test_coerces_to_float(self):
        val = _get({"compatibility": {"exact_match": "0.75"}}, "compatibility", "exact_match")
        assert val == 0.75
        assert isinstance(val, float)


class TestDefaultThresholds:
    def test_all_sections_present(self):
        expected = {"defense_bypass", "signal_gain", "compatibility", "access_fit", "stealth_penalty", "detection_risk"}
        assert expected == set(DEFAULT_THRESHOLDS.keys())

    def test_all_values_are_floats(self):
        for section in DEFAULT_THRESHOLDS.values():
            for val in section.values():
                assert isinstance(val, float)


class TestCompatibilityConfigurable:
    def test_default_exact_match(self, dan_technique, chatbot_target):
        score = score_compatibility(dan_technique, chatbot_target)
        assert score == 1.0

    def test_custom_exact_match(self, dan_technique, chatbot_target):
        th = {"compatibility": {"exact_match": 0.85}}
        score = score_compatibility(dan_technique, chatbot_target, th)
        assert score == 0.85

    def test_custom_no_types_listed(self, chatbot_target):
        t = AttackTechnique(
            id="test", name="test", description="", domain="llm",
            surface="model", phase="exploit", access_required="black_box",
            goals_supported=["jailbreak"], target_types=[],
        )
        th = {"compatibility": {"no_types_listed": 0.3}}
        score = score_compatibility(t, chatbot_target, th)
        assert score == 0.3


class TestAccessFitConfigurable:
    def test_default_exact_match(self, dan_technique, chatbot_target):
        score = score_access_fit(dan_technique, chatbot_target)
        assert score == 1.0

    def test_custom_exact_match(self, dan_technique, chatbot_target):
        th = {"access_fit": {"exact_match": 0.95}}
        score = score_access_fit(dan_technique, chatbot_target, th)
        assert score == 0.95

    def test_custom_overqualified_params(self, registry):
        # white_box target + black_box technique = overqualified
        target = TargetProfile(
            name="test", target_type=TargetType.CHATBOT,
            access_level=AccessLevel.WHITE_BOX, goals=[Goal.JAILBREAK],
        )
        t = registry.get("AP-TX-LLM-JAILBREAK-DAN")  # black_box
        th = {"access_fit": {"overqualified_floor": 0.3, "overqualified_decay": 0.1}}
        score = score_access_fit(t, target, th)
        assert score >= 0.3  # floor respected


class TestSignalGainConfigurable:
    def test_default_no_priors(self, dan_technique):
        score = score_signal_gain(dan_technique)
        assert score == 0.7  # default_score

    def test_custom_default_score(self, dan_technique):
        th = {"signal_gain": {"default_score": 0.9}}
        score = score_signal_gain(dan_technique, thresholds=th)
        assert score == 0.9


class TestDefenseBypassConfigurable:
    def test_default_no_defenses(self, dan_technique, chatbot_target):
        score = score_defense_bypass_likelihood(dan_technique, chatbot_target)
        # With no defenses on model surface, should return baseline or high
        assert score > 0.0

    def test_custom_no_defenses_baseline(self, dan_technique, chatbot_target):
        th = {"defense_bypass": {"no_defenses_baseline": 0.6}}
        # Need a technique where no defenses match the surface
        t = AttackTechnique(
            id="test", name="test", description="", domain="llm",
            surface="data", phase="exploit", access_required="black_box",
            goals_supported=["exfil_sim"], target_types=[],
        )
        score = score_defense_bypass_likelihood(t, chatbot_target, th)
        assert score == 0.6


class TestDetectionRiskConfigurable:
    def test_overt_priority_always_zero(self, dan_technique):
        target = TargetProfile(
            name="test", target_type=TargetType.CHATBOT,
            access_level=AccessLevel.BLACK_BOX, goals=[Goal.JAILBREAK],
            constraints=ConstraintSpec(stealth_priority=StealthLevel.OVERT),
        )
        score = score_detection_risk_penalty(dan_technique, target)
        assert score == 0.0

    def test_custom_moderate_multiplier(self, dan_technique):
        target = TargetProfile(
            name="test", target_type=TargetType.CHATBOT,
            access_level=AccessLevel.BLACK_BOX, goals=[Goal.JAILBREAK],
            constraints=ConstraintSpec(stealth_priority=StealthLevel.MODERATE),
        )
        th = {"detection_risk": {"moderate_multiplier": 0.8}}
        score_custom = score_detection_risk_penalty(dan_technique, target, th)
        score_default = score_detection_risk_penalty(dan_technique, target)
        # Custom multiplier is higher, so penalty should be larger
        assert score_custom >= score_default


class TestEnginePassesThresholds:
    def test_engine_loads_scorer_thresholds(self):
        from adversarypilot.prioritizer.engine import PrioritizerEngine
        engine = PrioritizerEngine()
        assert engine._scorer_thresholds is not None
        assert "compatibility" in engine._scorer_thresholds

    def test_engine_score_uses_thresholds(self, dan_technique, chatbot_target):
        from adversarypilot.prioritizer.engine import PrioritizerEngine
        engine = PrioritizerEngine()
        breakdown = engine.score_technique(dan_technique, chatbot_target)
        assert breakdown.compatibility == 1.0  # chatbot in DAN's target_types

    def test_engine_plan_with_thresholds(self, chatbot_target, registry):
        from adversarypilot.prioritizer.engine import PrioritizerEngine
        engine = PrioritizerEngine()
        plan = engine.plan(chatbot_target, registry, max_techniques=5)
        assert len(plan.entries) > 0
        for entry in plan.entries:
            assert entry.score.total != 0.0


class TestBackwardCompatibility:
    def test_no_thresholds_matches_defaults(self, dan_technique, chatbot_target):
        """Passing None for thresholds should give same results as defaults."""
        s1 = score_compatibility(dan_technique, chatbot_target, None)
        s2 = score_compatibility(dan_technique, chatbot_target, DEFAULT_THRESHOLDS)
        assert s1 == s2

    def test_empty_thresholds_uses_defaults(self, dan_technique, chatbot_target):
        s1 = score_compatibility(dan_technique, chatbot_target, {})
        s2 = score_compatibility(dan_technique, chatbot_target, None)
        assert s1 == s2
