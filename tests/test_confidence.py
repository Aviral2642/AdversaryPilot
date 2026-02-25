"""Tests for confidence quantification and explainability (WS6)."""

import pytest

from adversarypilot.models.enums import AccessLevel, Goal, TargetType
from adversarypilot.models.target import TargetProfile
from adversarypilot.planner.adaptive import AdaptivePlanner
from adversarypilot.planner.posterior import PosteriorState
from adversarypilot.taxonomy.registry import TechniqueRegistry


@pytest.fixture
def target():
    return TargetProfile(
        name="Test Target",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK],
    )


@pytest.fixture
def registry():
    r = TechniqueRegistry()
    r.load_catalog()
    return r


class TestBetaCI:
    def test_uniform_prior_wide_ci(self):
        lo, hi = AdaptivePlanner._beta_ci(1.0, 1.0)
        assert hi - lo > 0.5

    def test_strong_prior_narrow_ci(self):
        lo, hi = AdaptivePlanner._beta_ci(50.0, 50.0)
        assert hi - lo < 0.2

    def test_ci_contains_mean(self):
        alpha, beta = 3.0, 7.0
        lo, hi = AdaptivePlanner._beta_ci(alpha, beta)
        mean = alpha / (alpha + beta)
        assert lo <= mean <= hi

    def test_ci_bounds_valid(self):
        lo, hi = AdaptivePlanner._beta_ci(2.0, 5.0)
        assert 0.0 <= lo < hi <= 1.0

    def test_asymmetric_ci(self):
        lo, hi = AdaptivePlanner._beta_ci(9.0, 1.0)
        mean = 9.0 / 10.0
        assert hi - mean < mean - lo  # Right-skewed, CI compressed near 1.0


class TestConfidenceInPlan:
    def test_plan_entries_have_ci(self, target, registry):
        planner = AdaptivePlanner(campaign_seed=42)
        plan, _ = planner.plan(target, registry, max_techniques=5)
        for entry in plan.entries:
            assert entry.score.confidence_interval is not None
            lo, hi = entry.score.confidence_interval
            assert 0.0 <= lo < hi <= 1.0

    def test_plan_entries_have_variance(self, target, registry):
        planner = AdaptivePlanner(campaign_seed=42)
        plan, _ = planner.plan(target, registry, max_techniques=5)
        for entry in plan.entries:
            assert entry.score.posterior_variance is not None
            assert entry.score.posterior_variance > 0

    def test_plan_entries_have_observations(self, target, registry):
        planner = AdaptivePlanner(campaign_seed=42)
        plan, _ = planner.plan(target, registry, max_techniques=5)
        for entry in plan.entries:
            assert entry.score.observations == 0  # No observations yet


class TestStructuredRationale:
    def test_rationale_has_required_keys(self, target, registry):
        planner = AdaptivePlanner(campaign_seed=42)
        plan, _ = planner.plan(target, registry, max_techniques=3)
        for entry in plan.entries:
            r = entry.structured_rationale
            assert "prior_source" in r
            assert "posterior_mean" in r
            assert "confidence_interval" in r
            assert "family" in r
            assert "key_factors" in r

    def test_rationale_prior_source_is_benchmark(self, target, registry):
        planner = AdaptivePlanner(campaign_seed=42)
        plan, _ = planner.plan(target, registry, max_techniques=3)
        for entry in plan.entries:
            assert entry.structured_rationale["prior_source"] == "benchmark"

    def test_key_factors_is_list(self, target, registry):
        planner = AdaptivePlanner(campaign_seed=42)
        plan, _ = planner.plan(target, registry, max_techniques=3)
        for entry in plan.entries:
            assert isinstance(entry.structured_rationale["key_factors"], list)

    def test_family_key_format(self, target, registry):
        planner = AdaptivePlanner(campaign_seed=42)
        plan, _ = planner.plan(target, registry, max_techniques=3)
        for entry in plan.entries:
            family = entry.structured_rationale["family"]
            parts = family.split(":")
            assert len(parts) == 3
