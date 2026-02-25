"""Tests for result models."""

from adversarypilot.models.results import AttemptResult, ComparabilityMetadata, EvaluationResult


def test_attempt_result_minimal():
    a = AttemptResult(id="test-1", technique_id="AP-TX-TEST")
    assert a.id == "test-1"
    assert a.prompt is None
    assert a.source_tool is None


def test_attempt_result_full():
    a = AttemptResult(
        id="test-2",
        technique_id="AP-TX-LLM-JAILBREAK-DAN",
        prompt="test prompt",
        response="test response",
        source_tool="garak",
        source_run_id="run-001",
        duration_ms=1500,
    )
    assert a.source_tool == "garak"
    assert a.duration_ms == 1500


def test_comparability_metadata_defaults():
    c = ComparabilityMetadata()
    assert c.random_seed_policy == "unknown"
    assert c.num_trials == 1
    assert c.comparability_flags == []


def test_evaluation_result_serialization():
    e = EvaluationResult(
        attempt_id="test-1",
        success=True,
        score=0.9,
        confidence=0.85,
        evidence_quality=0.7,
    )
    json_str = e.model_dump_json()
    restored = EvaluationResult.model_validate_json(json_str)
    assert restored.success is True
    assert restored.score == 0.9


def test_evaluation_result_inconclusive():
    e = EvaluationResult(attempt_id="test-1", success=None, score=None)
    assert e.success is None
    assert e.score is None
