"""Tests for posterior state and technique posteriors."""

import pytest

from adversarypilot.planner.posterior import PosteriorState, TechniquePosterior


class TestTechniquePosterior:
    def test_default_uniform_prior(self):
        p = TechniquePosterior(technique_id="t1")
        assert p.alpha == 1.0
        assert p.beta == 1.0
        assert p.observations == 0

    def test_mean_uniform(self):
        p = TechniquePosterior(technique_id="t1")
        assert p.mean == pytest.approx(0.5)

    def test_mean_biased(self):
        p = TechniquePosterior(technique_id="t1", alpha=3.0, beta=1.0)
        assert p.mean == pytest.approx(0.75)

    def test_update_success(self):
        p = TechniquePosterior(technique_id="t1", alpha=1.0, beta=1.0)
        p.update(1.0)
        assert p.alpha == 2.0
        assert p.beta == 1.0
        assert p.observations == 1

    def test_update_failure(self):
        p = TechniquePosterior(technique_id="t1", alpha=1.0, beta=1.0)
        p.update(0.0)
        assert p.alpha == 1.0
        assert p.beta == 2.0
        assert p.observations == 1

    def test_update_partial_reward(self):
        p = TechniquePosterior(technique_id="t1", alpha=1.0, beta=1.0)
        p.update(0.6)
        assert p.alpha == pytest.approx(1.6)
        assert p.beta == pytest.approx(1.4)

    def test_update_rejects_out_of_bounds(self):
        p = TechniquePosterior(technique_id="t1")
        with pytest.raises(ValueError, match="Reward must be in"):
            p.update(1.5)
        with pytest.raises(ValueError, match="Reward must be in"):
            p.update(-0.1)

    def test_serialization_roundtrip(self):
        p = TechniquePosterior(technique_id="t1", alpha=3.5, beta=2.1)
        p.update(0.8)
        data = p.model_dump()
        restored = TechniquePosterior.model_validate(data)
        assert restored.technique_id == p.technique_id
        assert restored.alpha == pytest.approx(p.alpha)
        assert restored.beta == pytest.approx(p.beta)
        assert restored.observations == p.observations


class TestPosteriorState:
    def test_get_or_init_new(self):
        state = PosteriorState()
        p = state.get_or_init("t1", 0.7)
        assert p.technique_id == "t1"
        # alpha = 1 + 8*0.7 = 6.6
        assert p.alpha == pytest.approx(6.6)
        # beta = 1 + 8*0.3 = 3.4
        assert p.beta == pytest.approx(3.4)

    def test_get_or_init_returns_existing(self):
        state = PosteriorState()
        p1 = state.get_or_init("t1", 0.7)
        p1.update(1.0)
        p2 = state.get_or_init("t1", 0.7)
        assert p2 is p1
        assert p2.observations == 1

    def test_custom_prior_strength(self):
        state = PosteriorState(prior_strength=4.0)
        p = state.get_or_init("t1", 0.5)
        # alpha = 1 + 4*0.5 = 3.0
        assert p.alpha == pytest.approx(3.0)
        assert p.beta == pytest.approx(3.0)

    def test_multiple_techniques(self):
        state = PosteriorState()
        state.get_or_init("t1", 0.8)
        state.get_or_init("t2", 0.3)
        assert len(state.posteriors) == 2
        assert state.posteriors["t1"].mean > state.posteriors["t2"].mean

    def test_serialization_roundtrip(self):
        state = PosteriorState()
        state.get_or_init("t1", 0.7)
        state.get_or_init("t2", 0.3)
        data = state.model_dump()
        restored = PosteriorState.model_validate(data)
        assert set(restored.posteriors.keys()) == {"t1", "t2"}
        assert restored.prior_strength == state.prior_strength
