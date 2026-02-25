"""Tests for Z-score calibration baselines (WS4)."""

import pytest

from adversarypilot.planner.priors import (
    BENCHMARK_BASELINES,
    compute_z_score,
    get_baseline,
    interpret_z_score,
)


class TestBenchmarkBaselines:
    def test_baselines_populated(self):
        assert len(BENCHMARK_BASELINES) >= 25

    def test_all_have_required_keys(self):
        for key, baseline in BENCHMARK_BASELINES.items():
            assert "mean_asr" in baseline, f"{key} missing mean_asr"
            assert "std_asr" in baseline, f"{key} missing std_asr"
            assert "n_models" in baseline, f"{key} missing n_models"

    def test_all_values_in_range(self):
        for key, baseline in BENCHMARK_BASELINES.items():
            assert 0.0 <= baseline["mean_asr"] <= 1.0, f"{key} mean_asr out of range"
            assert baseline["std_asr"] > 0, f"{key} std_asr must be positive"
            assert baseline["n_models"] >= 1, f"{key} n_models must be >= 1"


class TestGetBaseline:
    def test_known_family(self):
        b = get_baseline("llm:guardrail:jailbreak")
        assert b["mean_asr"] == 0.55
        assert b["std_asr"] == 0.18

    def test_unknown_family_returns_default(self):
        b = get_baseline("unknown:family:key")
        assert b["mean_asr"] == 0.40
        assert b["std_asr"] == 0.20

    def test_a2a_baselines(self):
        b = get_baseline("agent:action:a2a")
        assert b["mean_asr"] == 0.25

    def test_mcp_baselines(self):
        b = get_baseline("agent:tool:mcp")
        assert b["mean_asr"] == 0.35


class TestComputeZScore:
    def test_exact_mean_returns_zero(self):
        z = compute_z_score(0.55, "llm:guardrail:jailbreak")
        assert abs(z) < 0.001

    def test_above_mean_positive_z(self):
        z = compute_z_score(0.80, "llm:guardrail:jailbreak")
        assert z > 0

    def test_below_mean_negative_z(self):
        z = compute_z_score(0.20, "llm:guardrail:jailbreak")
        assert z < 0

    def test_one_sigma_above(self):
        b = get_baseline("llm:guardrail:jailbreak")
        z = compute_z_score(b["mean_asr"] + b["std_asr"], "llm:guardrail:jailbreak")
        assert abs(z - 1.0) < 0.001

    def test_unknown_family(self):
        z = compute_z_score(0.60, "unknown:family")
        # Uses default baseline: mean=0.40, std=0.20 → z = (0.60-0.40)/0.20 = 1.0
        assert abs(z - 1.0) < 0.001


class TestInterpretZScore:
    def test_highly_vulnerable(self):
        assert "Significantly more vulnerable" in interpret_z_score(2.5)

    def test_more_vulnerable(self):
        assert "More vulnerable" in interpret_z_score(1.5)

    def test_normal_range(self):
        assert "normal range" in interpret_z_score(0.0)

    def test_more_resistant(self):
        assert "More resistant" in interpret_z_score(-1.5)

    def test_significantly_resistant(self):
        assert "Significantly more resistant" in interpret_z_score(-2.5)
