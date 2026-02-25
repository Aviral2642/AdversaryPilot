"""Prioritizer engine — orchestrates filter → score → rank → plan."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from adversarypilot.models.plan import AttackPlan, PlanEntry, ScoreBreakdown
from adversarypilot.models.results import EvaluationResult
from adversarypilot.models.target import TargetProfile
from adversarypilot.models.technique import AttackTechnique
from adversarypilot.prioritizer.filters import passes_all_filters
from adversarypilot.prioritizer.sensitivity import SensitivityReport, run_sensitivity
from adversarypilot.prioritizer.scorers import (
    score_access_fit,
    score_compatibility,
    score_cost_penalty,
    score_defense_bypass_likelihood,
    score_detection_risk_penalty,
    score_goal_fit,
    score_signal_gain,
)
from adversarypilot.taxonomy.registry import TechniqueRegistry

_DEFAULT_CONFIG = Path(__file__).parent / "config.yaml"


class ScoredTechnique:
    """Internal wrapper pairing a technique with its score breakdown."""

    __slots__ = ("technique", "breakdown")

    def __init__(self, technique: AttackTechnique, breakdown: ScoreBreakdown) -> None:
        self.technique = technique
        self.breakdown = breakdown


class PrioritizerEngine:
    """Rule-based attack prioritizer: filter → score → rank → plan."""

    def __init__(self, config_path: Path | None = None) -> None:
        config_path = config_path or _DEFAULT_CONFIG
        with open(config_path) as f:
            self._config: dict[str, Any] = yaml.safe_load(f)
        self._weights = self._config.get("weights", {})
        self._scorer_thresholds = self._config.get("scorer_thresholds", None)
        self._score_lo, self._score_hi = self._compute_score_range()

    def _compute_score_range(self) -> tuple[float, float]:
        """Compute theoretical min/max of the weighted scoring formula from config weights.

        Each scorer returns 0.0-1.0. The formula is:
          sum(positive_weights * scorer) - sum(penalty_weights * scorer)
        Min = 0 for all positive terms, 1.0 for all penalty terms.
        Max = 1.0 for all positive terms, 0 for all penalty terms.
        """
        w = self._weights
        positive_keys = ["compatibility", "access_fit", "goal_fit", "defense_bypass_likelihood", "signal_gain"]
        penalty_keys = ["cost_penalty", "detection_risk_penalty"]

        pos_sum = sum(w.get(k, 0.0) for k in positive_keys)
        neg_sum = sum(w.get(k, 0.0) for k in penalty_keys)

        return -neg_sum, pos_sum

    def normalize_score(self, raw: float) -> float:
        """Normalize a raw weighted score to [0, 1] using weight-derived bounds."""
        span = self._score_hi - self._score_lo
        if span <= 0:
            return 0.5
        return max(0.0, min(1.0, (raw - self._score_lo) / span))

    def plan(
        self,
        target: TargetProfile,
        registry: TechniqueRegistry,
        prior_results: list[EvaluationResult] | None = None,
        max_techniques: int | None = None,
    ) -> AttackPlan:
        """Generate a ranked attack plan for the given target."""
        candidates = registry.get_all()
        filtered = self._apply_hard_filters(candidates, target)
        scored = self._score_techniques(filtered, target, prior_results)
        scored = self._apply_diversity_bonus(scored)

        # Sort by total score descending
        scored.sort(key=lambda s: s.breakdown.total, reverse=True)

        if max_techniques:
            scored = scored[:max_techniques]

        return self._build_plan(scored, target)

    def apply_hard_filters(
        self, techniques: list[AttackTechnique], target: TargetProfile
    ) -> list[AttackTechnique]:
        """Public method to apply hard filters to techniques.

        Filters out techniques that don't meet basic requirements.

        Args:
            techniques: List of techniques to filter
            target: Target profile

        Returns:
            List of techniques that pass all hard filters
        """
        return self._apply_hard_filters(techniques, target)

    def score_technique(
        self,
        technique: AttackTechnique,
        target: TargetProfile,
        prior_results: list[EvaluationResult] | None = None,
    ) -> ScoreBreakdown:
        """Public method to score a single technique.

        Args:
            technique: Technique to score
            target: Target profile
            prior_results: Prior evaluation results

        Returns:
            Score breakdown for this technique
        """
        th = self._scorer_thresholds
        compatibility = score_compatibility(technique, target, th)
        access_fit = score_access_fit(technique, target, th)
        goal_fit = score_goal_fit(technique, target)
        defense_bypass = score_defense_bypass_likelihood(technique, target, th)
        signal = score_signal_gain(technique, prior_results, th)
        cost = score_cost_penalty(technique)
        detection = score_detection_risk_penalty(technique, target, th)

        w = self._weights
        total = (
            w.get("compatibility", 1.0) * compatibility
            + w.get("access_fit", 0.8) * access_fit
            + w.get("goal_fit", 1.0) * goal_fit
            + w.get("defense_bypass_likelihood", 0.7) * defense_bypass
            + w.get("signal_gain", 0.5) * signal
            - w.get("cost_penalty", 0.4) * cost
            - w.get("detection_risk_penalty", 0.3) * detection
        )

        return ScoreBreakdown(
            compatibility=compatibility,
            access_fit=access_fit,
            goal_fit=goal_fit,
            defense_bypass_likelihood=defense_bypass,
            signal_gain=signal,
            cost_penalty=cost,
            detection_risk_penalty=detection,
            total=total,
        )

    def _apply_hard_filters(
        self, techniques: list[AttackTechnique], target: TargetProfile
    ) -> list[AttackTechnique]:
        """Eliminate techniques that fail hard filter predicates."""
        max_cost = self._config.get("filters", {}).get("max_cost", 1.0)
        return [
            t
            for t in techniques
            if passes_all_filters(t, target) and t.base_cost <= max_cost
        ]

    def _score_techniques(
        self,
        techniques: list[AttackTechnique],
        target: TargetProfile,
        prior_results: list[EvaluationResult] | None,
    ) -> list[ScoredTechnique]:
        """Compute weighted additive score for each technique."""
        scored = []
        th = self._scorer_thresholds
        for technique in techniques:
            compatibility = score_compatibility(technique, target, th)
            access_fit = score_access_fit(technique, target, th)
            goal_fit = score_goal_fit(technique, target)
            defense_bypass = score_defense_bypass_likelihood(technique, target, th)
            signal = score_signal_gain(technique, prior_results, th)
            cost = score_cost_penalty(technique)
            detection = score_detection_risk_penalty(technique, target, th)

            w = self._weights
            total = (
                w.get("compatibility", 1.0) * compatibility
                + w.get("access_fit", 0.8) * access_fit
                + w.get("goal_fit", 1.0) * goal_fit
                + w.get("defense_bypass_likelihood", 0.7) * defense_bypass
                + w.get("signal_gain", 0.5) * signal
                - w.get("cost_penalty", 0.4) * cost
                - w.get("detection_risk_penalty", 0.3) * detection
            )

            breakdown = ScoreBreakdown(
                compatibility=compatibility,
                access_fit=access_fit,
                goal_fit=goal_fit,
                defense_bypass_likelihood=defense_bypass,
                signal_gain=signal,
                cost_penalty=cost,
                detection_risk_penalty=detection,
                total=total,
            )
            scored.append(ScoredTechnique(technique, breakdown))

        return scored

    def _apply_diversity_bonus(
        self, scored: list[ScoredTechnique]
    ) -> list[ScoredTechnique]:
        """Penalize techniques that share (domain, phase, surface) with higher-ranked ones."""
        penalty = self._config.get("diversity", {}).get("same_triple_penalty", 0.15)

        # Sort by current total to determine priority
        scored.sort(key=lambda s: s.breakdown.total, reverse=True)

        seen_triples: dict[tuple[str, str, str], int] = {}
        for s in scored:
            triple = (
                s.technique.domain.value,
                s.technique.phase.value,
                s.technique.surface.value,
            )
            count = seen_triples.get(triple, 0)
            if count > 0:
                s.breakdown.diversity_bonus = -penalty * count
                s.breakdown.total += s.breakdown.diversity_bonus
            seen_triples[triple] = count + 1

        return scored

    def run_sensitivity_analysis(
        self,
        target: TargetProfile,
        registry: TechniqueRegistry,
        prior_results: list[EvaluationResult] | None = None,
        top_k: int = 10,
    ) -> SensitivityReport:
        """Run sensitivity analysis on current weight configuration.

        Perturbs each weight independently and measures ranking stability.
        """
        candidates = registry.get_all()
        filtered = self._apply_hard_filters(candidates, target)
        sens_config = self._config.get("sensitivity", {})
        return run_sensitivity(
            techniques=filtered,
            target=target,
            weights=self._weights,
            perturbation_pct=sens_config.get("perturbation_pct", 0.20),
            num_samples=sens_config.get("num_samples", 50),
            top_k=top_k,
            prior_results=prior_results,
            thresholds=self._scorer_thresholds,
        )

    def _build_plan(
        self, scored: list[ScoredTechnique], target: TargetProfile
    ) -> AttackPlan:
        """Construct an AttackPlan with rationale for each entry."""
        entries = []
        for rank, s in enumerate(scored, 1):
            rationale = self._generate_rationale(s, target)
            entry = PlanEntry(
                rank=rank,
                technique_id=s.technique.id,
                technique_name=s.technique.name,
                score=s.breakdown,
                rationale=rationale,
                tags=s.technique.tags,
            )
            entries.append(entry)

        return AttackPlan(
            target=target,
            entries=entries,
            config_used=self._config,
        )

    def _generate_rationale(
        self, scored: ScoredTechnique, target: TargetProfile
    ) -> str:
        """Generate a human-readable rationale for why this technique was ranked here."""
        t = scored.technique
        b = scored.breakdown
        parts = []

        if b.compatibility >= 0.8:
            parts.append(f"strong fit for {target.target_type.value} targets")
        if b.goal_fit >= 0.8:
            goals = ", ".join(g.value for g in t.goals_supported if g in target.goals)
            parts.append(f"directly addresses goal(s): {goals}")
        if b.defense_bypass_likelihood >= 0.7:
            parts.append(f"likely to bypass observed defenses on {t.surface.value} layer")
        if b.signal_gain >= 0.8:
            parts.append("high information gain (untried technique)")
        if b.cost_penalty <= 0.3:
            parts.append("low cost")
        if b.cost_penalty >= 0.7:
            parts.append("high cost — consider budget")

        if not parts:
            parts.append("moderate fit across scoring dimensions")

        return "; ".join(parts) + f" [total={b.total:.2f}]"
