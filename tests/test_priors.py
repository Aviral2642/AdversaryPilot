"""Tests for benchmark priors (WS2)."""

from adversarypilot.planner.priors import BENCHMARK_ASR, get_benchmark_prior


class TestBenchmarkPriors:
    def test_known_family_lookup(self):
        asr = get_benchmark_prior("llm:guardrail:tap")
        assert asr == 0.65

    def test_unknown_family_fallback(self):
        asr = get_benchmark_prior("unknown:surface:tag")
        assert asr == 0.40

    def test_clamping_lower_bound(self):
        assert get_benchmark_prior("anything") >= 0.05

    def test_clamping_upper_bound(self):
        assert get_benchmark_prior("anything") <= 0.95

    def test_all_entries_within_bounds(self):
        for key, val in BENCHMARK_ASR.items():
            result = get_benchmark_prior(key)
            assert 0.05 <= result <= 0.95, f"{key}: {result}"

    def test_blend_formula(self):
        benchmark = get_benchmark_prior("llm:guardrail:pair")
        v1_score = 0.7
        blend_weight = 0.6
        blended = blend_weight * benchmark + (1 - blend_weight) * v1_score
        expected = 0.6 * 0.60 + 0.4 * 0.7
        assert abs(blended - expected) < 1e-9


class TestPriorStrength:
    def test_k3_shifts_faster_than_k8(self):
        from adversarypilot.planner.posterior import PosteriorState

        state_k3 = PosteriorState(prior_strength=3.0)
        state_k8 = PosteriorState(prior_strength=8.0)

        p3 = state_k3.get_or_init("t1", 0.5)
        p8 = state_k8.get_or_init("t1", 0.5)

        # Both start at 0.5 mean
        assert abs(p3.mean - 0.5) < 0.01
        assert abs(p8.mean - 0.5) < 0.01

        # After 3 successes, k=3 should shift more than k=8
        for _ in range(3):
            p3.update(1.0)
            p8.update(1.0)

        assert p3.mean > p8.mean, "k=3 should shift faster with same observations"
