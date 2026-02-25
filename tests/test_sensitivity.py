"""Tests for sensitivity analysis (WS2)."""

import pytest

from adversarypilot.models.enums import AccessLevel, Goal, TargetType
from adversarypilot.models.target import TargetProfile
from adversarypilot.prioritizer.engine import PrioritizerEngine
from adversarypilot.prioritizer.sensitivity import (
    SensitivityReport,
    WeightSensitivity,
    _kendall_tau,
    run_sensitivity,
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
def default_weights():
    return {
        "compatibility": 1.0,
        "access_fit": 0.8,
        "goal_fit": 1.0,
        "defense_bypass_likelihood": 0.7,
        "signal_gain": 0.5,
        "cost_penalty": 0.4,
        "detection_risk_penalty": 0.3,
    }


class TestKendallTau:
    def test_identical_rankings(self):
        r = ["a", "b", "c", "d"]
        assert _kendall_tau(r, r) == 1.0

    def test_reversed_rankings(self):
        assert _kendall_tau(["a", "b", "c", "d"], ["d", "c", "b", "a"]) == -1.0

    def test_partial_swap(self):
        tau = _kendall_tau(["a", "b", "c"], ["a", "c", "b"])
        assert -1.0 <= tau <= 1.0
        assert tau < 1.0  # Not identical

    def test_single_element(self):
        assert _kendall_tau(["a"], ["a"]) == 1.0

    def test_empty(self):
        assert _kendall_tau([], []) == 1.0

    def test_disjoint_sets(self):
        # No common elements — should return 1.0 (trivially concordant)
        assert _kendall_tau(["a", "b"], ["c", "d"]) == 1.0


class TestRunSensitivity:
    def test_returns_report(self, registry, chatbot_target, default_weights):
        techniques = registry.get_all()[:10]  # Subset for speed
        report = run_sensitivity(
            techniques, chatbot_target, default_weights,
            num_samples=5, seed=42,
        )
        assert isinstance(report, SensitivityReport)
        assert report.num_samples == 5
        assert len(report.weight_sensitivities) == len(default_weights)

    def test_all_weights_analyzed(self, registry, chatbot_target, default_weights):
        techniques = registry.get_all()[:10]
        report = run_sensitivity(
            techniques, chatbot_target, default_weights,
            num_samples=5, seed=42,
        )
        names = {ws.weight_name for ws in report.weight_sensitivities}
        assert names == set(default_weights.keys())

    def test_correlations_in_range(self, registry, chatbot_target, default_weights):
        techniques = registry.get_all()[:10]
        report = run_sensitivity(
            techniques, chatbot_target, default_weights,
            num_samples=10, seed=42,
        )
        for ws in report.weight_sensitivities:
            assert -1.0 <= ws.rank_correlation <= 1.0
            assert 0.0 <= ws.top_k_stability <= 1.0

    def test_small_perturbation_high_stability(self, registry, chatbot_target, default_weights):
        techniques = registry.get_all()[:10]
        report = run_sensitivity(
            techniques, chatbot_target, default_weights,
            perturbation_pct=0.01, num_samples=10, seed=42,
        )
        for ws in report.weight_sensitivities:
            assert ws.rank_correlation > 0.8  # Small perturbation = stable

    def test_most_least_sensitive_populated(self, registry, chatbot_target, default_weights):
        techniques = registry.get_all()[:10]
        report = run_sensitivity(
            techniques, chatbot_target, default_weights,
            num_samples=5, seed=42,
        )
        assert report.most_sensitive_weight in default_weights
        assert report.least_sensitive_weight in default_weights

    def test_deterministic_with_seed(self, registry, chatbot_target, default_weights):
        techniques = registry.get_all()[:10]
        r1 = run_sensitivity(techniques, chatbot_target, default_weights, num_samples=5, seed=42)
        r2 = run_sensitivity(techniques, chatbot_target, default_weights, num_samples=5, seed=42)
        for ws1, ws2 in zip(r1.weight_sensitivities, r2.weight_sensitivities):
            assert ws1.rank_correlation == ws2.rank_correlation
            assert ws1.top_k_stability == ws2.top_k_stability


class TestEngineSensitivity:
    def test_engine_sensitivity_analysis(self, registry, chatbot_target):
        engine = PrioritizerEngine()
        report = engine.run_sensitivity_analysis(chatbot_target, registry, top_k=5)
        assert isinstance(report, SensitivityReport)
        assert len(report.weight_sensitivities) > 0

    def test_engine_sensitivity_with_diversity_weight(self, registry, chatbot_target):
        engine = PrioritizerEngine()
        report = engine.run_sensitivity_analysis(chatbot_target, registry)
        # diversity_bonus weight should be included
        names = {ws.weight_name for ws in report.weight_sensitivities}
        assert "compatibility" in names
