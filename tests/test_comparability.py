"""Tests for the comparability checker."""

from adversarypilot.models.enums import JudgeType
from adversarypilot.models.results import ComparabilityMetadata, EvaluationResult
from adversarypilot.reporting.comparability import ComparabilityChecker


def _make_eval(
    judge_type: JudgeType = JudgeType.RULE_BASED,
    judge_version: str | None = None,
    criteria_hash: str = "hash1",
    input_slice: str | None = None,
    seed_policy: str = "fixed",
    num_trials: int = 100,
) -> EvaluationResult:
    return EvaluationResult(
        attempt_id="test",
        success=True,
        comparability=ComparabilityMetadata(
            judge_type=judge_type,
            judge_model_version=judge_version,
            success_criteria_hash=criteria_hash,
            input_slice_id=input_slice,
            random_seed_policy=seed_policy,
            num_trials=num_trials,
        ),
    )


def test_comparable_results():
    checker = ComparabilityChecker()
    a = _make_eval()
    b = _make_eval()
    flags = checker.check_pairwise(a, b)
    assert flags == []


def test_different_judge_types():
    checker = ComparabilityChecker()
    a = _make_eval(judge_type=JudgeType.RULE_BASED)
    b = _make_eval(judge_type=JudgeType.LLM_JUDGE)
    flags = checker.check_pairwise(a, b)
    assert any("judge types" in f.lower() for f in flags)


def test_different_judge_versions():
    checker = ComparabilityChecker()
    a = _make_eval(judge_version="gpt-4-0613")
    b = _make_eval(judge_version="gpt-4-1106")
    flags = checker.check_pairwise(a, b)
    assert any("judge model versions" in f.lower() for f in flags)


def test_different_success_criteria():
    checker = ComparabilityChecker()
    a = _make_eval(criteria_hash="hash1")
    b = _make_eval(criteria_hash="hash2")
    flags = checker.check_pairwise(a, b)
    assert any("success criteria" in f.lower() for f in flags)


def test_different_seed_policy():
    checker = ComparabilityChecker()
    a = _make_eval(seed_policy="fixed")
    b = _make_eval(seed_policy="swept")
    flags = checker.check_pairwise(a, b)
    assert any("seed" in f.lower() for f in flags)


def test_different_trial_counts():
    checker = ComparabilityChecker()
    a = _make_eval(num_trials=100)
    b = _make_eval(num_trials=50)
    flags = checker.check_pairwise(a, b)
    assert any("trial counts" in f.lower() for f in flags)


def test_check_group_multiple_issues():
    checker = ComparabilityChecker()
    results = [
        _make_eval(judge_type=JudgeType.RULE_BASED, seed_policy="fixed"),
        _make_eval(judge_type=JudgeType.LLM_JUDGE, seed_policy="swept"),
    ]
    flags = checker.check_group(results)
    assert len(flags) >= 2


def test_check_group_single_result():
    checker = ComparabilityChecker()
    flags = checker.check_group([_make_eval()])
    assert flags == []


def test_find_comparable_groups():
    checker = ComparabilityChecker()
    r1 = _make_eval()
    r1.comparability.comparable_group_key = "group-a"
    r2 = _make_eval()
    r2.comparability.comparable_group_key = "group-a"
    r3 = _make_eval()
    r3.comparability.comparable_group_key = "group-b"

    groups = checker.find_comparable_groups([r1, r2, r3])
    assert len(groups) == 2
    assert len(groups["group-a"]) == 2
    assert len(groups["group-b"]) == 1
