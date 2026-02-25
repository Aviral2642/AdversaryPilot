"""Reward policies for adaptive planning."""

from abc import ABC, abstractmethod

from adversarypilot.models.results import EvaluationResult


class RewardPolicy(ABC):
    """Abstract reward policy for converting evaluation results to rewards.

    Rewards are values between 0.0 and 1.0 used to update Beta posteriors.
    """

    @abstractmethod
    def compute_reward(self, evaluation: EvaluationResult) -> float | None:
        """Compute reward from evaluation result.

        Args:
            evaluation: Evaluation result to convert

        Returns:
            Reward value (0.0-1.0) or None if inconclusive
        """
        ...


class BinaryRewardPolicy(RewardPolicy):
    """Binary reward: 1.0 for success, 0.0 for failure, None for inconclusive.

    This is the default and fully tested policy.
    """

    def compute_reward(self, evaluation: EvaluationResult) -> float | None:
        """Compute binary reward from success field.

        Args:
            evaluation: Evaluation result

        Returns:
            1.0 if success=True, 0.0 if success=False, None if success=None
        """
        if evaluation.success is None:
            return None
        return 1.0 if evaluation.success else 0.0


class WeightedRewardPolicy(RewardPolicy):
    """EXPERIMENTAL: Weighted reward using score field when available.

    Falls back to binary reward if score is unavailable.
    This policy is experimental and not fully tested.

    Warning: Using score as reward may introduce bias if scores are not
    calibrated consistently across different judge types.
    """

    def compute_reward(self, evaluation: EvaluationResult) -> float | None:
        """Compute weighted reward from score or success field.

        Args:
            evaluation: Evaluation result

        Returns:
            score if available, else binary reward, else None
        """
        if evaluation.score is not None:
            return max(0.0, min(1.0, evaluation.score))
        if evaluation.success is None:
            return None
        return 1.0 if evaluation.success else 0.0
