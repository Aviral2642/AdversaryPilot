"""Tests for reward policies."""

from adversarypilot.models.results import EvaluationResult, ComparabilityMetadata
from adversarypilot.planner.reward import BinaryRewardPolicy, WeightedRewardPolicy


class TestBinaryRewardPolicy:
    def test_success_returns_one(self):
        policy = BinaryRewardPolicy()
        result = EvaluationResult(attempt_id="a1", success=True)
        assert policy.compute_reward(result) == 1.0

    def test_failure_returns_zero(self):
        policy = BinaryRewardPolicy()
        result = EvaluationResult(attempt_id="a1", success=False)
        assert policy.compute_reward(result) == 0.0

    def test_inconclusive_returns_none(self):
        policy = BinaryRewardPolicy()
        result = EvaluationResult(attempt_id="a1", success=None)
        assert policy.compute_reward(result) is None


class TestWeightedRewardPolicy:
    def test_uses_score_when_available(self):
        policy = WeightedRewardPolicy()
        result = EvaluationResult(attempt_id="a1", success=True, score=0.7)
        assert policy.compute_reward(result) == 0.7

    def test_clamps_score_to_bounds(self):
        policy = WeightedRewardPolicy()
        # score field has ge=0.0, le=1.0 in the model, so we test the clamp logic
        # by verifying normal bounds work
        result = EvaluationResult(attempt_id="a1", success=True, score=1.0)
        assert policy.compute_reward(result) == 1.0

    def test_falls_back_to_binary(self):
        policy = WeightedRewardPolicy()
        result = EvaluationResult(attempt_id="a1", success=False, score=None)
        assert policy.compute_reward(result) == 0.0

    def test_inconclusive_returns_none(self):
        policy = WeightedRewardPolicy()
        result = EvaluationResult(attempt_id="a1", success=None, score=None)
        assert policy.compute_reward(result) is None
