"""Tests for the weakest layer analyzer."""

from adversarypilot.models.enums import JudgeType, Surface
from adversarypilot.models.results import ComparabilityMetadata, EvaluationResult
from adversarypilot.models.technique import AttackTechnique
from adversarypilot.reporting.analyzer import WeakestLayerAnalyzer


def _make_eval(technique_id: str, success: bool, quality: float = 0.7) -> EvaluationResult:
    return EvaluationResult(
        attempt_id=f"att-{id(success)}",
        success=success,
        score=0.8 if success else 0.2,
        judge_type=JudgeType.RULE_BASED,
        confidence=0.8,
        evidence_quality=quality,
        comparability=ComparabilityMetadata(technique_id=technique_id),
    )


def _make_technique(tid: str, surface: Surface) -> AttackTechnique:
    return AttackTechnique(
        id=tid, name=f"Test {tid}", domain="llm", phase="exploit",
        surface=surface, access_required="black_box",
    )


def test_analyze_basic():
    analyzer = WeakestLayerAnalyzer(min_attempts=2)
    techniques = {
        "t1": _make_technique("t1", Surface.GUARDRAIL),
        "t2": _make_technique("t2", Surface.MODEL),
    }
    results = [
        _make_eval("t1", True),
        _make_eval("t1", True),
        _make_eval("t1", False),
        _make_eval("t2", False),
        _make_eval("t2", False),
    ]

    assessments = analyzer.analyze(results, techniques)
    assert len(assessments) == len(Surface)

    guardrail = next(a for a in assessments if a.layer == Surface.GUARDRAIL)
    model = next(a for a in assessments if a.layer == Surface.MODEL)

    assert guardrail.risk_score > model.risk_score
    assert guardrail.is_primary_weakness is True


def test_analyze_insufficient_evidence():
    analyzer = WeakestLayerAnalyzer(min_attempts=5)
    techniques = {"t1": _make_technique("t1", Surface.GUARDRAIL)}
    results = [_make_eval("t1", True), _make_eval("t1", True)]

    assessments = analyzer.analyze(results, techniques)
    guardrail = next(a for a in assessments if a.layer == Surface.GUARDRAIL)
    assert guardrail.is_insufficient_evidence is True


def test_analyze_empty_results():
    analyzer = WeakestLayerAnalyzer()
    assessments = analyzer.analyze([], {})
    assert len(assessments) == len(Surface)
    assert all(a.is_insufficient_evidence for a in assessments)


def test_wilson_score():
    analyzer = WeakestLayerAnalyzer()
    center = analyzer._wilson_center(5, 10)
    assert 0.3 < center < 0.7  # Smoothed toward 0.5

    ci = analyzer._wilson_interval(5, 10)
    assert ci[0] < center < ci[1]
    assert ci[0] >= 0.0
    assert ci[1] <= 1.0


def test_wilson_score_edge_cases():
    analyzer = WeakestLayerAnalyzer()
    assert analyzer._wilson_center(0, 0) == 0.0
    assert analyzer._wilson_interval(0, 0) == (0.0, 1.0)

    # All successes
    center = analyzer._wilson_center(10, 10)
    assert center > 0.8

    # All failures
    center = analyzer._wilson_center(0, 10)
    assert center < 0.2


def test_recommendations_generated():
    analyzer = WeakestLayerAnalyzer(min_attempts=2)
    techniques = {"t1": _make_technique("t1", Surface.GUARDRAIL)}
    results = [_make_eval("t1", True), _make_eval("t1", True), _make_eval("t1", True)]

    assessments = analyzer.analyze(results, techniques)
    guardrail = next(a for a in assessments if a.layer == Surface.GUARDRAIL)
    assert len(guardrail.recommendations) > 0
    assert any("HIGH PRIORITY" in r for r in guardrail.recommendations)
