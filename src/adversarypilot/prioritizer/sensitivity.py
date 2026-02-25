"""Sensitivity analysis for scorer weight stability.

Perturbs each weight independently, re-ranks techniques, and measures
ranking stability via Kendall tau rank correlation.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from itertools import combinations

from adversarypilot.models.results import EvaluationResult
from adversarypilot.models.target import TargetProfile
from adversarypilot.models.technique import AttackTechnique
from adversarypilot.prioritizer.scorers import (
    score_access_fit,
    score_compatibility,
    score_cost_penalty,
    score_defense_bypass_likelihood,
    score_detection_risk_penalty,
    score_goal_fit,
    score_signal_gain,
)


@dataclass
class WeightSensitivity:
    """Sensitivity result for a single weight."""

    weight_name: str
    rank_correlation: float  # Kendall tau vs. baseline
    top_k_stability: float  # Fraction of top-K preserved
    displaced_techniques: list[str] = field(default_factory=list)


@dataclass
class SensitivityReport:
    """Full sensitivity analysis report."""

    num_samples: int
    perturbation_pct: float
    weight_sensitivities: list[WeightSensitivity] = field(default_factory=list)
    most_sensitive_weight: str = ""
    least_sensitive_weight: str = ""


def _kendall_tau(ranking_a: list[str], ranking_b: list[str]) -> float:
    """Compute Kendall tau rank correlation between two rankings.

    Returns value in [-1, 1] where 1 = identical order, -1 = reversed.
    O(n^2) stdlib implementation — no numpy needed.
    """
    if len(ranking_a) < 2:
        return 1.0

    # Build rank maps
    rank_a = {tid: i for i, tid in enumerate(ranking_a)}
    rank_b = {tid: i for i, tid in enumerate(ranking_b)}

    # Only compare IDs present in both
    common = [tid for tid in ranking_a if tid in rank_b]
    n = len(common)
    if n < 2:
        return 1.0

    concordant = 0
    discordant = 0
    for i, j in combinations(range(n), 2):
        a_diff = rank_a[common[i]] - rank_a[common[j]]
        b_diff = rank_b[common[i]] - rank_b[common[j]]
        product = a_diff * b_diff
        if product > 0:
            concordant += 1
        elif product < 0:
            discordant += 1

    total_pairs = n * (n - 1) // 2
    if total_pairs == 0:
        return 1.0
    return (concordant - discordant) / total_pairs


def _compute_scores(
    techniques: list[AttackTechnique],
    target: TargetProfile,
    weights: dict[str, float],
    prior_results: list[EvaluationResult] | None = None,
    thresholds: dict | None = None,
) -> list[tuple[str, float]]:
    """Score and rank techniques with given weights. Returns (id, score) sorted desc."""
    results = []
    for t in techniques:
        compatibility = score_compatibility(t, target, thresholds)
        access_fit = score_access_fit(t, target, thresholds)
        goal_fit = score_goal_fit(t, target)
        defense_bypass = score_defense_bypass_likelihood(t, target, thresholds)
        signal = score_signal_gain(t, prior_results, thresholds)
        cost = score_cost_penalty(t)
        detection = score_detection_risk_penalty(t, target, thresholds)

        total = (
            weights.get("compatibility", 1.0) * compatibility
            + weights.get("access_fit", 0.8) * access_fit
            + weights.get("goal_fit", 1.0) * goal_fit
            + weights.get("defense_bypass_likelihood", 0.7) * defense_bypass
            + weights.get("signal_gain", 0.5) * signal
            - weights.get("cost_penalty", 0.4) * cost
            - weights.get("detection_risk_penalty", 0.3) * detection
        )
        results.append((t.id, total))

    results.sort(key=lambda x: x[1], reverse=True)
    return results


def run_sensitivity(
    techniques: list[AttackTechnique],
    target: TargetProfile,
    weights: dict[str, float],
    perturbation_pct: float = 0.20,
    num_samples: int = 50,
    top_k: int = 10,
    prior_results: list[EvaluationResult] | None = None,
    thresholds: dict | None = None,
    seed: int = 42,
) -> SensitivityReport:
    """Run sensitivity analysis by perturbing each weight independently.

    For each weight:
      1. Sample `num_samples` perturbations within ±perturbation_pct
      2. Re-rank techniques
      3. Compute average Kendall tau and top-K stability vs. baseline
    """
    rng = random.Random(seed)

    # Baseline ranking
    baseline = _compute_scores(techniques, target, weights, prior_results, thresholds)
    baseline_ranking = [tid for tid, _ in baseline]
    baseline_top_k = set(baseline_ranking[:top_k])

    weight_names = list(weights.keys())
    sensitivities: list[WeightSensitivity] = []

    for wname in weight_names:
        tau_sum = 0.0
        stability_sum = 0.0
        displaced_counts: dict[str, int] = {}
        original_val = weights[wname]

        for _ in range(num_samples):
            factor = 1.0 + rng.uniform(-perturbation_pct, perturbation_pct)
            perturbed_weights = dict(weights)
            perturbed_weights[wname] = original_val * factor

            perturbed = _compute_scores(
                techniques, target, perturbed_weights, prior_results, thresholds
            )
            perturbed_ranking = [tid for tid, _ in perturbed]
            perturbed_top_k = set(perturbed_ranking[:top_k])

            tau_sum += _kendall_tau(baseline_ranking, perturbed_ranking)

            overlap = len(baseline_top_k & perturbed_top_k)
            stability_sum += overlap / max(len(baseline_top_k), 1)

            # Track displaced techniques
            displaced = baseline_top_k - perturbed_top_k
            for tid in displaced:
                displaced_counts[tid] = displaced_counts.get(tid, 0) + 1

        avg_tau = tau_sum / num_samples
        avg_stability = stability_sum / num_samples
        top_displaced = sorted(displaced_counts.keys(), key=lambda t: displaced_counts[t], reverse=True)[:5]

        sensitivities.append(WeightSensitivity(
            weight_name=wname,
            rank_correlation=round(avg_tau, 4),
            top_k_stability=round(avg_stability, 4),
            displaced_techniques=top_displaced,
        ))

    # Find most/least sensitive
    sorted_by_tau = sorted(sensitivities, key=lambda s: s.rank_correlation)
    most_sensitive = sorted_by_tau[0].weight_name if sorted_by_tau else ""
    least_sensitive = sorted_by_tau[-1].weight_name if sorted_by_tau else ""

    return SensitivityReport(
        num_samples=num_samples,
        perturbation_pct=perturbation_pct,
        weight_sensitivities=sensitivities,
        most_sensitive_weight=most_sensitive,
        least_sensitive_weight=least_sensitive,
    )
