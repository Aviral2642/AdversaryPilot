"""Tests for score normalization (WS1)."""

import math

from adversarypilot.planner.cost_aware import normalize_utility
from adversarypilot.prioritizer.engine import PrioritizerEngine


class TestScoreNormalization:
    def test_score_range_from_weights(self):
        engine = PrioritizerEngine()
        lo, hi = engine._score_lo, engine._score_hi
        assert lo < 0, "min score should be negative (penalty terms)"
        assert hi > 0, "max score should be positive"
        assert hi > lo

    def test_normalize_zero_raw(self):
        engine = PrioritizerEngine()
        result = engine.normalize_score(0.0)
        assert 0.0 <= result <= 1.0

    def test_normalize_max_raw(self):
        engine = PrioritizerEngine()
        result = engine.normalize_score(engine._score_hi)
        assert result == 1.0

    def test_normalize_min_raw(self):
        engine = PrioritizerEngine()
        result = engine.normalize_score(engine._score_lo)
        assert result == 0.0

    def test_normalize_negative_raw_preserves_information(self):
        engine = PrioritizerEngine()
        neg = engine.normalize_score(-0.3)
        zero = engine.normalize_score(0.0)
        assert neg < zero, "negative raw should map below zero raw"

    def test_normalize_clamps_above_max(self):
        engine = PrioritizerEngine()
        result = engine.normalize_score(100.0)
        assert result == 1.0

    def test_normalize_clamps_below_min(self):
        engine = PrioritizerEngine()
        result = engine.normalize_score(-100.0)
        assert result == 0.0

    def test_normalize_monotonic(self):
        engine = PrioritizerEngine()
        vals = [engine.normalize_score(x * 0.5) for x in range(-4, 12)]
        for i in range(len(vals) - 1):
            assert vals[i] <= vals[i + 1]


class TestNormalizeUtility:
    def test_midpoint_maps_to_half(self):
        assert normalize_utility(0.5) == 0.5

    def test_large_positive_near_one(self):
        assert normalize_utility(5.0) > 0.99

    def test_large_negative_near_zero(self):
        assert normalize_utility(-5.0) < 0.01

    def test_monotonic(self):
        vals = [normalize_utility(x * 0.1) for x in range(-20, 21)]
        for i in range(len(vals) - 1):
            assert vals[i] <= vals[i + 1]

    def test_custom_steepness(self):
        gentle = normalize_utility(1.0, steepness=1.0)
        steep = normalize_utility(1.0, steepness=10.0)
        assert steep > gentle
