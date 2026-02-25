"""Weakest layer analyzer — per-layer scoring with Wilson confidence intervals."""

from __future__ import annotations

import math

from adversarypilot.models.enums import Surface
from adversarypilot.models.report import EvidenceBundle, LayerAssessment
from adversarypilot.models.results import EvaluationResult
from adversarypilot.models.technique import AttackTechnique


def compute_assessment_quality(
    assessments: list[LayerAssessment],
    warnings: list[str] | None = None,
) -> "AssessmentQuality":
    """Compute overall assessment quality score.

    Factors:
    - Evidence depth: average evidence quality across layers
    - Coverage breadth: fraction of layers with sufficient evidence
    - Statistical power: based on total attempts
    - Comparability: penalized by number of warnings
    """
    from adversarypilot.models.report import AssessmentQuality

    if not assessments:
        return AssessmentQuality()

    # Evidence depth: average evidence quality
    qualities = [a.evidence.evidence_quality for a in assessments if a.evidence.total_attempts > 0]
    evidence_depth = sum(qualities) / len(qualities) if qualities else 0.0

    # Coverage breadth: fraction with sufficient evidence
    total_layers = len(assessments)
    sufficient = sum(1 for a in assessments if not a.is_insufficient_evidence)
    coverage_breadth = sufficient / max(total_layers, 1)

    # Statistical power: based on total attempts (diminishing returns)
    total_attempts = sum(a.evidence.total_attempts for a in assessments)
    statistical_power = min(1.0, total_attempts / 30.0)  # 30 attempts = full power

    # Comparability: penalized by warnings
    num_warnings = len(warnings) if warnings else 0
    comparability_score = max(0.0, 1.0 - 0.1 * num_warnings)

    # Overall: weighted average
    overall = (
        0.30 * evidence_depth
        + 0.25 * coverage_breadth
        + 0.25 * statistical_power
        + 0.20 * comparability_score
    )

    return AssessmentQuality(
        overall_score=round(overall, 3),
        evidence_depth=round(evidence_depth, 3),
        coverage_breadth=round(coverage_breadth, 3),
        statistical_power=round(statistical_power, 3),
        comparability_score=round(comparability_score, 3),
        factors={
            "layers_with_evidence": len(qualities),
            "layers_sufficient": sufficient,
            "total_attempts": total_attempts,
            "num_warnings": num_warnings,
        },
    )


class WeakestLayerAnalyzer:
    """Analyzes evaluation results to identify the weakest system layer."""

    def __init__(self, min_attempts: int = 3, z: float = 1.96) -> None:
        self._min_attempts = min_attempts
        self._z = z  # Z-score for confidence interval (1.96 = 95%)

    def analyze(
        self,
        results: list[EvaluationResult],
        techniques: dict[str, AttackTechnique],
    ) -> list[LayerAssessment]:
        """Produce per-layer assessments from evaluation results."""
        # Group results by surface layer
        layer_results: dict[Surface, list[EvaluationResult]] = {}
        layer_techniques: dict[Surface, set[str]] = {}

        for result in results:
            technique_id = result.comparability.technique_id
            technique = techniques.get(technique_id)
            if technique is None:
                continue

            layer = technique.surface
            layer_results.setdefault(layer, []).append(result)
            layer_techniques.setdefault(layer, set()).add(technique_id)

        # Build assessment for each layer
        assessments = []
        for layer in Surface:
            layer_evals = layer_results.get(layer, [])
            techs = layer_techniques.get(layer, set())
            assessment = self._assess_layer(layer, layer_evals, list(techs))
            assessments.append(assessment)

        # Determine primary weakness (highest risk_score with sufficient evidence)
        sufficient = [a for a in assessments if not a.is_insufficient_evidence]
        if sufficient:
            primary = max(sufficient, key=lambda a: a.risk_score)
            primary.is_primary_weakness = True

        # Sort by risk_score descending
        assessments.sort(key=lambda a: a.risk_score, reverse=True)
        return assessments

    def _assess_layer(
        self,
        layer: Surface,
        results: list[EvaluationResult],
        technique_ids: list[str],
    ) -> LayerAssessment:
        """Build a LayerAssessment for a single layer."""
        total = len(results)
        insufficient = total < self._min_attempts

        if total == 0:
            return LayerAssessment(
                layer=layer,
                is_insufficient_evidence=True,
                techniques_tested=technique_ids,
                recommendations=[f"No attempts targeted the {layer.value} layer yet"],
            )

        successes = sum(1 for r in results if r.success is True)
        smoothed_rate = self._wilson_center(successes, total)
        ci = self._wilson_interval(successes, total)
        avg_quality = sum(r.evidence_quality for r in results) / total
        attempt_ids = [r.attempt_id for r in results]

        # Risk score: smoothed success rate weighted by evidence quality and coverage
        coverage_factor = min(1.0, total / (self._min_attempts * 2))
        risk_score = smoothed_rate * avg_quality * coverage_factor

        caveats = []
        if insufficient:
            caveats.append(
                f"Only {total} attempts (minimum {self._min_attempts} recommended)"
            )
        inconclusive = sum(1 for r in results if r.success is None)
        if inconclusive > 0:
            caveats.append(f"{inconclusive} inconclusive result(s)")

        evidence = EvidenceBundle(
            supporting_attempt_ids=attempt_ids,
            success_count=successes,
            total_attempts=total,
            smoothed_success_rate=smoothed_rate,
            confidence_interval=ci,
            confidence_method="wilson",
            evidence_quality=avg_quality,
            caveats=caveats,
        )

        recommendations = self._generate_recommendations(
            layer, successes, total, insufficient
        )

        return LayerAssessment(
            layer=layer,
            evidence=evidence,
            risk_score=risk_score,
            is_insufficient_evidence=insufficient,
            techniques_tested=technique_ids,
            recommendations=recommendations,
        )

    def _wilson_center(self, successes: int, total: int) -> float:
        """Wilson score interval center — smoothed success rate."""
        if total == 0:
            return 0.0
        z2 = self._z ** 2
        p = successes / total
        return (p + z2 / (2 * total)) / (1 + z2 / total)

    def _wilson_interval(
        self, successes: int, total: int
    ) -> tuple[float, float]:
        """Wilson score confidence interval."""
        if total == 0:
            return (0.0, 1.0)
        z2 = self._z ** 2
        p = successes / total
        denominator = 1 + z2 / total
        center = (p + z2 / (2 * total)) / denominator
        spread = (self._z / denominator) * math.sqrt(
            p * (1 - p) / total + z2 / (4 * total**2)
        )
        return (max(0.0, center - spread), min(1.0, center + spread))

    def _generate_recommendations(
        self,
        layer: Surface,
        successes: int,
        total: int,
        insufficient: bool,
    ) -> list[str]:
        """Generate actionable recommendations for defenders."""
        recs = []
        if insufficient:
            recs.append(f"Increase test coverage on the {layer.value} layer")

        if total > 0:
            rate = successes / total
            if rate > 0.5:
                recs.append(
                    f"HIGH PRIORITY: {layer.value} layer shows {rate:.0%} attack success rate"
                )
                recs.append(f"Review and strengthen defenses on the {layer.value} layer")
            elif rate > 0.2:
                recs.append(
                    f"MODERATE: {layer.value} layer shows {rate:.0%} attack success rate"
                )
            elif rate > 0:
                recs.append(
                    f"Some attacks succeeded on {layer.value} layer ({rate:.0%})"
                )
        return recs
