"""Adaptive planner with Thompson Sampling overlay on V1 rule-based engine."""

from __future__ import annotations

import hashlib
import logging
import math
import random
from pathlib import Path
from typing import Any

import yaml

from adversarypilot.models.enums import CampaignPhase
from adversarypilot.models.plan import AttackPlan, PlanEntry, ScoreBreakdown
from adversarypilot.models.results import EvaluationResult
from adversarypilot.models.target import TargetProfile
from adversarypilot.models.technique import AttackTechnique
from adversarypilot.planner.correlation import FamilyCorrelation
from adversarypilot.planner.cost_aware import compute_cost, compute_impact_weight, compute_utility
from adversarypilot.planner.diversity import FamilyTracker
from adversarypilot.planner.posterior import PosteriorState, TechniquePosterior
from adversarypilot.planner.priors import get_benchmark_prior
from adversarypilot.planner.reward import BinaryRewardPolicy, RewardPolicy
from adversarypilot.prioritizer.engine import PrioritizerEngine
from adversarypilot.prioritizer.filters import passes_all_filters
from adversarypilot.taxonomy.registry import TechniqueRegistry

logger = logging.getLogger(__name__)


class AdaptivePlanner:
    """Hybrid Thompson Sampling + V1 rule-based planner.

    Uses V1 filtering and scoring as informative priors, then samples
    from Beta posteriors updated with campaign observations.
    """

    def __init__(
        self,
        config_path: Path | str | None = None,
        engine: PrioritizerEngine | None = None,
        reward_policy: RewardPolicy | None = None,
        campaign_seed: int | None = None,
        correlation: FamilyCorrelation | None = None,
    ) -> None:
        """Initialize adaptive planner.

        Args:
            config_path: Path to config YAML (uses prioritizer config if None)
            engine: V1 prioritizer engine (creates default if None)
            reward_policy: Reward policy (uses BinaryRewardPolicy if None)
            campaign_seed: Random seed for campaign (generated if None)
        """
        self.engine = engine or PrioritizerEngine(config_path)
        self.reward_policy = reward_policy or BinaryRewardPolicy()
        self.campaign_seed = campaign_seed or random.randint(0, 2**31 - 1)

        # Load config
        if config_path is None:
            from importlib import resources

            with resources.files("adversarypilot.prioritizer").joinpath("config.yaml").open() as f:
                self.config = yaml.safe_load(f)
        else:
            with open(config_path) as f:
                self.config = yaml.safe_load(f)

        # Extract adaptive config section
        adaptive_cfg = self.config.get("adaptive", {})
        self.prior_strength = adaptive_cfg.get("prior_strength", 3.0)
        self.info_gain_weight = adaptive_cfg.get("info_gain_weight", 0.3)
        self.detection_penalty_weight = adaptive_cfg.get("detection_penalty_weight", 0.2)
        self.cost_weight = adaptive_cfg.get("cost_weight", 0.4)
        self.use_benchmark_priors = adaptive_cfg.get("use_benchmark_priors", True)
        self.benchmark_blend_weight = adaptive_cfg.get("benchmark_blend_weight", 0.6)

        # Extract cost-aware config
        cost_cfg = self.config.get("cost_aware", {})
        self.goal_severity = cost_cfg.get("goal_severity", {})
        self.surface_criticality = cost_cfg.get("surface_criticality", {})

        # Extract correlation config
        corr_cfg = self.config.get("correlation", {})
        if correlation is not None:
            self.correlation = correlation
        elif corr_cfg.get("enabled", True):
            self.correlation = FamilyCorrelation(
                spillover_rate=corr_cfg.get("spillover_rate", 0.3)
            )
        else:
            self.correlation = None

        # Extract diversity config
        diversity_cfg = self.config.get("diversity_v2", {})
        self.diversity_config = diversity_cfg

    def plan(
        self,
        target: TargetProfile,
        registry: TechniqueRegistry,
        posterior_state: PosteriorState | None = None,
        prior_results: list[EvaluationResult] | None = None,
        max_techniques: int = 10,
        exclude_tried: bool = False,
        repeat_penalty: float = 0.0,
        family_tracker: FamilyTracker | None = None,
        step_number: int = 0,
        campaign_phase: CampaignPhase = CampaignPhase.PROBE,
    ) -> tuple[AttackPlan, PosteriorState]:
        """Generate adaptive attack plan with Thompson Sampling.

        Args:
            target: Target profile
            registry: Technique registry
            posterior_state: Current posterior state (creates new if None)
            prior_results: Previous evaluation results
            max_techniques: Maximum techniques to return
            exclude_tried: If True, exclude techniques already tried
            repeat_penalty: Penalty for repeat techniques (0.0 = no penalty)
            family_tracker: Diversity tracker (creates new if None)
            step_number: Current decision step (for deterministic seeding)

        Returns:
            Tuple of (AttackPlan, updated_posterior_state)
        """
        # Initialize state
        if posterior_state is None:
            posterior_state = PosteriorState(prior_strength=self.prior_strength)
        if family_tracker is None:
            family_tracker = FamilyTracker(**self.diversity_config)
        if prior_results is None:
            prior_results = []

        # Derive deterministic step seed
        step_seed = self._derive_step_seed(step_number)
        rng = random.Random(step_seed)
        logger.debug(
            "Adaptive plan: step=%d, seed=%d, exclude_tried=%s, repeat_penalty=%.2f",
            step_number, step_seed, exclude_tried, repeat_penalty,
        )

        # Adjust weights based on campaign phase
        info_gain_weight = self.info_gain_weight
        cost_weight = self.cost_weight
        if campaign_phase == CampaignPhase.PROBE:
            info_gain_weight *= 1.5
            cost_weight *= 0.7
        elif campaign_phase == CampaignPhase.EXPLOIT:
            info_gain_weight *= 0.3
            cost_weight *= 1.2

        # Register catalog for family correlation
        all_techniques = registry.get_all()
        if self.correlation is not None:
            self.correlation.register_techniques(all_techniques)

        # Apply V1 hard filters
        max_cost = self.config.get("filters", {}).get("max_cost", 1.0)

        filtered = [
            t
            for t in all_techniques
            if passes_all_filters(t, target) and t.base_cost <= max_cost
        ]

        # Track tried technique IDs for exclusion/penalty
        tried_ids = {r.comparability.technique_id for r in prior_results if r.comparability}

        # Compute V1 base scores for each filtered technique
        scored_candidates: list[dict[str, Any]] = []

        for technique in filtered:
            # Exclude tried techniques if requested
            if exclude_tried and technique.id in tried_ids:
                continue

            # Compute V1 base score using engine's internal scoring
            base_score = self._compute_v1_base_score(technique, target, prior_results)

            # Compute blended prior from benchmark data + V1 score
            blended_prior = self._compute_blended_prior(technique, base_score)

            # Get or initialize posterior
            posterior = posterior_state.get_or_init(technique.id, base_score, blended_prior)

            # Sample from Beta posterior
            thompson_sample = rng.betavariate(posterior.alpha, posterior.beta)

            # Compute impact weight
            impact = compute_impact_weight(
                technique,
                target.goals,
                self.goal_severity or None,
                self.surface_criticality or None,
            )

            # Compute cost
            cost = compute_cost(technique, max_cost)

            # Compute info gain bonus (higher uncertainty = higher gain)
            info_gain = self._compute_info_gain(posterior) * info_gain_weight

            # Compute detection penalty
            detection = self._compute_detection_penalty(technique) * self.detection_penalty_weight

            # Compute diversity bonus
            diversity = family_tracker.compute_diversity_bonus(technique)

            # Apply repeat penalty if technique was tried
            repeat_pen = repeat_penalty if technique.id in tried_ids else 0.0

            # Compute final utility
            utility = compute_utility(
                thompson_sample,
                impact,
                cost,
                cost_weight,
                info_gain,
                detection,
                diversity,
            ) - repeat_pen

            scored_candidates.append(
                {
                    "technique": technique,
                    "base_score": base_score,
                    "thompson_sample": thompson_sample,
                    "impact": impact,
                    "cost": cost,
                    "info_gain": info_gain,
                    "detection": detection,
                    "diversity": diversity,
                    "repeat_penalty": repeat_pen,
                    "utility": utility,
                    "posterior": posterior,
                }
            )

        # Sort by utility (descending)
        scored_candidates.sort(key=lambda x: x["utility"], reverse=True)
        logger.info(
            "Adaptive plan: %d candidates scored, top utility=%.3f",
            len(scored_candidates),
            scored_candidates[0]["utility"] if scored_candidates else 0.0,
        )

        # Build plan entries
        entries: list[PlanEntry] = []
        for rank, candidate in enumerate(scored_candidates[:max_techniques], start=1):
            technique = candidate["technique"]
            posterior = candidate["posterior"]

            # Build rationale
            rationale = self._build_rationale(candidate, target)

            # Compute confidence interval
            ci = self._beta_ci(posterior.alpha, posterior.beta)
            variance = (posterior.alpha * posterior.beta) / (
                (posterior.alpha + posterior.beta) ** 2
                * (posterior.alpha + posterior.beta + 1)
            )

            # Build score breakdown
            score_breakdown = ScoreBreakdown(
                total=candidate["base_score"],
                thompson_sample=candidate["thompson_sample"],
                utility=candidate["utility"],
                cost_penalty=candidate["cost"],
                detection_risk_penalty=candidate["detection"],
                diversity_bonus=candidate["diversity"],
                confidence_interval=ci,
                posterior_variance=variance,
                observations=posterior.observations,
            )

            # Build structured rationale
            family = self._family_key(technique)
            siblings_observed = 0
            if self.correlation:
                for sib_id in self.correlation.get_siblings(technique.id):
                    if sib_id in posterior_state.posteriors:
                        siblings_observed += posterior_state.posteriors[sib_id].observations

            structured = {
                "prior_source": "benchmark" if self.use_benchmark_priors else "v1_heuristic",
                "prior_asr": candidate["base_score"],
                "observations": posterior.observations,
                "posterior_mean": posterior.mean,
                "confidence_interval": list(ci),
                "family": family,
                "siblings_observed": siblings_observed,
                "key_factors": self._extract_key_factors(candidate),
            }

            entry = PlanEntry(
                rank=rank,
                technique_id=technique.id,
                technique_name=technique.name,
                score=score_breakdown,
                rationale=rationale,
                tags=technique.tags,
                structured_rationale=structured,
            )
            entries.append(entry)

        # Build plan
        plan = AttackPlan(
            target=target,
            entries=entries,
            config_used={
                "adaptive": True,
                "step_number": step_number,
                "step_seed": step_seed,
                "prior_strength": self.prior_strength,
                "cost_weight": self.cost_weight,
                "exclude_tried": exclude_tried,
                "repeat_penalty": repeat_penalty,
                "campaign_phase": campaign_phase.value,
            },
        )

        return plan, posterior_state

    def update_posteriors(
        self,
        posterior_state: PosteriorState,
        results: list[EvaluationResult],
        registry: TechniqueRegistry,
        target: TargetProfile,
    ) -> PosteriorState:
        """Update posteriors with new observations.

        Args:
            posterior_state: Current posterior state
            results: New evaluation results
            registry: Technique registry (for base scores)
            target: Target profile (for base scores)

        Returns:
            Updated posterior state
        """
        for evaluation in results:
            technique_id = evaluation.comparability.technique_id
            if not technique_id:
                continue

            # Compute reward
            reward = self.reward_policy.compute_reward(evaluation)
            if reward is None:
                # Inconclusive result, skip update
                continue

            # Get base score for initialization if needed
            technique = registry.get(technique_id)
            if technique is None:
                continue

            base_score = self._compute_v1_base_score(technique, target, [])
            blended_prior = self._compute_blended_prior(technique, base_score)

            posterior = posterior_state.get_or_init(technique_id, base_score, blended_prior)

            # Update with reward
            posterior.update(reward)

            # Propagate to correlated siblings
            if self.correlation is not None:
                self.correlation.propagate_update(technique_id, reward, posterior_state)

        return posterior_state

    def _derive_step_seed(self, step_number: int) -> int:
        """Derive deterministic per-step seed.

        Args:
            step_number: Current step number

        Returns:
            Deterministic seed for this step
        """
        seed_str = f"{self.campaign_seed}:{step_number}"
        return int(hashlib.sha256(seed_str.encode()).hexdigest()[:8], 16)

    def _compute_v1_base_score(
        self,
        technique: AttackTechnique,
        target: TargetProfile,
        prior_results: list[EvaluationResult],
    ) -> float:
        """Compute V1 base score using engine's public scoring API.

        Uses the full weighted scoring formula from PrioritizerEngine.

        Args:
            technique: Technique to score
            target: Target profile
            prior_results: Prior evaluation results

        Returns:
            Base score (normalized 0.0-1.0)
        """
        breakdown = self.engine.score_technique(technique, target, prior_results)
        return self.engine.normalize_score(breakdown.total)

    def _compute_info_gain(self, posterior: TechniquePosterior) -> float:
        """Compute information gain bonus.

        Higher variance = higher uncertainty = higher gain.

        Args:
            posterior: TechniquePosterior

        Returns:
            Info gain bonus (0.0-1.0)
        """
        # Beta distribution variance: (alpha*beta) / ((alpha+beta)^2 * (alpha+beta+1))
        a, b = posterior.alpha, posterior.beta
        variance = (a * b) / ((a + b) ** 2 * (a + b + 1))
        # Normalize: max variance is 1/12 at alpha=beta=1
        return min(variance * 12, 1.0)

    def _compute_detection_penalty(self, technique: AttackTechnique) -> float:
        """Compute detection risk penalty.

        Args:
            technique: Attack technique

        Returns:
            Detection penalty (0.0-1.0)
        """
        # Map stealth level to penalty (lower stealth = higher penalty)
        stealth_penalties = {
            "overt": 0.5,
            "moderate": 0.2,
            "covert": 0.0,
        }
        return stealth_penalties.get(str(technique.stealth_profile), 0.3)

    @staticmethod
    def _beta_ci(alpha: float, beta: float, z: float = 1.96) -> tuple[float, float]:
        """Compute confidence interval for Beta distribution using normal approximation."""
        total = alpha + beta
        mean = alpha / total
        variance = (alpha * beta) / (total ** 2 * (total + 1))
        std = math.sqrt(variance)
        lo = max(0.0, mean - z * std)
        hi = min(1.0, mean + z * std)
        return (lo, hi)

    @staticmethod
    def _extract_key_factors(candidate: dict[str, Any]) -> list[str]:
        """Extract human-readable key factors from a scored candidate."""
        factors = []
        if candidate["diversity"] > 0.2:
            factors.append("targets untested attack surface")
        if candidate["info_gain"] > 0.15:
            factors.append("high information gain (uncertain outcome)")
        if candidate["cost"] < 0.3:
            factors.append("low execution cost")
        if candidate["cost"] > 0.7:
            factors.append("high execution cost")
        if candidate["thompson_sample"] > 0.7:
            factors.append("high estimated success probability")
        if candidate["thompson_sample"] < 0.3:
            factors.append("low estimated success probability")
        if candidate["repeat_penalty"] > 0:
            factors.append("repeat technique (penalty applied)")
        return factors

    @staticmethod
    def _family_key(technique: AttackTechnique) -> str:
        """Build family key from technique metadata: domain:surface:primary_tag."""
        primary_tag = technique.tags[0] if technique.tags else technique.surface.value
        return f"{technique.domain.value}:{technique.surface.value}:{primary_tag}"

    def _compute_blended_prior(
        self, technique: AttackTechnique, base_score: float
    ) -> float | None:
        """Blend benchmark ASR with V1 base score for prior initialization."""
        if not self.use_benchmark_priors:
            return None
        family = self._family_key(technique)
        benchmark = get_benchmark_prior(family)
        w = self.benchmark_blend_weight
        return w * benchmark + (1.0 - w) * base_score

    def _build_rationale(
        self, candidate: dict[str, Any], target: TargetProfile
    ) -> str:
        """Build human-readable rationale for technique ranking.

        Args:
            candidate: Scored candidate dict
            target: Target profile

        Returns:
            Rationale string
        """
        technique = candidate["technique"]
        utility = candidate["utility"]
        thompson = candidate["thompson_sample"]
        observations = candidate["posterior"].observations

        parts = []

        # Observations context
        if observations == 0:
            parts.append(f"sampled p={thompson:.2f} from prior")
        else:
            parts.append(f"sampled p={thompson:.2f} ({observations} obs)")

        # Utility breakdown
        parts.append(f"utility={utility:.2f}")

        # Key factors
        if candidate["diversity"] > 0.2:
            parts.append("untested surface")
        if candidate["repeat_penalty"] > 0:
            parts.append("repeat penalty applied")
        if candidate["info_gain"] > 0.2:
            parts.append("high info gain")

        return "; ".join(parts)
