"""Posterior state for adaptive planning with Thompson Sampling."""

from __future__ import annotations

from pydantic import BaseModel


class TechniquePosterior(BaseModel):
    """Beta distribution posterior for a single technique.

    Tracks success/failure observations for Thompson Sampling.
    """

    technique_id: str
    alpha: float = 1.0  # Success pseudo-count
    beta: float = 1.0  # Failure pseudo-count
    observations: int = 0

    @property
    def mean(self) -> float:
        """Expected success probability (Beta mean)."""
        return self.alpha / (self.alpha + self.beta)

    def update(self, reward: float) -> None:
        """Update posterior with new observation.

        Args:
            reward: Value between 0.0 and 1.0

        Raises:
            ValueError: If reward is outside [0.0, 1.0]
        """
        if not 0.0 <= reward <= 1.0:
            raise ValueError(f"Reward must be in [0.0, 1.0], got {reward}")
        self.alpha += reward
        self.beta += 1.0 - reward
        self.observations += 1


class PosteriorState(BaseModel):
    """Collection of technique posteriors for a campaign.

    Manages Beta priors/posteriors for all techniques, initialized
    from V1 base scores and updated with observations.
    """

    posteriors: dict[str, TechniquePosterior] = {}
    prior_strength: float = 8.0  # k parameter for prior weight

    def get_or_init(
        self,
        technique_id: str,
        base_score: float = 0.5,
        benchmark_prior: float | None = None,
    ) -> TechniquePosterior:
        """Get existing posterior or initialize from base score.

        When benchmark_prior is provided, it is used as the prior probability
        instead of the V1 base_score, giving calibrated priors from published data.
        """
        if technique_id not in self.posteriors:
            p = benchmark_prior if benchmark_prior is not None else base_score
            k = self.prior_strength
            alpha = 1.0 + k * p
            beta = 1.0 + k * (1.0 - p)
            self.posteriors[technique_id] = TechniquePosterior(
                technique_id=technique_id, alpha=alpha, beta=beta
            )
        return self.posteriors[technique_id]
