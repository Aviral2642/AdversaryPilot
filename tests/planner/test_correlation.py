"""Tests for correlated arms via technique families (WS3)."""

import pytest

from adversarypilot.models.enums import (
    AccessLevel,
    Domain,
    ExecutionMode,
    Goal,
    Phase,
    StealthLevel,
    Surface,
    TargetType,
)
from adversarypilot.models.technique import AttackTechnique
from adversarypilot.planner.correlation import FamilyCorrelation
from adversarypilot.planner.posterior import PosteriorState, TechniquePosterior


def _make_technique(id: str, domain: str, surface: str, tags: list[str]) -> AttackTechnique:
    return AttackTechnique(
        id=id,
        name=f"Test {id}",
        description="test",
        domain=Domain(domain),
        phase=Phase.EXPLOIT,
        surface=Surface(surface),
        access_required=AccessLevel.BLACK_BOX,
        goals_supported=[Goal.JAILBREAK],
        target_types=[TargetType.CHATBOT],
        stealth_profile=StealthLevel.MODERATE,
        execution_mode=ExecutionMode.FULLY_AUTOMATED,
        base_cost=0.3,
        tags=tags,
    )


@pytest.fixture
def sibling_techniques():
    return [
        _make_technique("AP-TX-A", "llm", "guardrail", ["encoding"]),
        _make_technique("AP-TX-B", "llm", "guardrail", ["encoding"]),
        _make_technique("AP-TX-C", "llm", "guardrail", ["encoding"]),
    ]


@pytest.fixture
def unrelated_technique():
    return _make_technique("AP-TX-X", "agent", "tool", ["injection"])


class TestFamilyCorrelation:
    def test_siblings_share_family(self, sibling_techniques):
        corr = FamilyCorrelation()
        corr.register_techniques(sibling_techniques)
        siblings = corr.get_siblings("AP-TX-A")
        assert siblings == {"AP-TX-B", "AP-TX-C"}

    def test_no_self_in_siblings(self, sibling_techniques):
        corr = FamilyCorrelation()
        corr.register_techniques(sibling_techniques)
        assert "AP-TX-A" not in corr.get_siblings("AP-TX-A")

    def test_cross_family_isolation(self, sibling_techniques, unrelated_technique):
        corr = FamilyCorrelation()
        corr.register_techniques(sibling_techniques + [unrelated_technique])
        siblings_a = corr.get_siblings("AP-TX-A")
        assert "AP-TX-X" not in siblings_a
        assert corr.get_siblings("AP-TX-X") == set()

    def test_propagate_updates_siblings(self, sibling_techniques):
        corr = FamilyCorrelation(spillover_rate=0.3)
        corr.register_techniques(sibling_techniques)

        state = PosteriorState(prior_strength=3.0)
        for t in sibling_techniques:
            state.get_or_init(t.id, 0.5)

        alpha_b_before = state.posteriors["AP-TX-B"].alpha
        corr.propagate_update("AP-TX-A", 1.0, state)
        alpha_b_after = state.posteriors["AP-TX-B"].alpha

        assert alpha_b_after == pytest.approx(alpha_b_before + 0.3)

    def test_propagate_does_not_update_self(self, sibling_techniques):
        corr = FamilyCorrelation(spillover_rate=0.3)
        corr.register_techniques(sibling_techniques)

        state = PosteriorState(prior_strength=3.0)
        for t in sibling_techniques:
            state.get_or_init(t.id, 0.5)

        alpha_a_before = state.posteriors["AP-TX-A"].alpha
        corr.propagate_update("AP-TX-A", 1.0, state)
        assert state.posteriors["AP-TX-A"].alpha == alpha_a_before

    def test_propagate_does_not_increment_observations(self, sibling_techniques):
        corr = FamilyCorrelation(spillover_rate=0.3)
        corr.register_techniques(sibling_techniques)

        state = PosteriorState(prior_strength=3.0)
        for t in sibling_techniques:
            state.get_or_init(t.id, 0.5)

        corr.propagate_update("AP-TX-A", 1.0, state)
        assert state.posteriors["AP-TX-B"].observations == 0

    def test_spillover_magnitude(self, sibling_techniques):
        corr = FamilyCorrelation(spillover_rate=0.5)
        corr.register_techniques(sibling_techniques)

        state = PosteriorState(prior_strength=3.0)
        for t in sibling_techniques:
            state.get_or_init(t.id, 0.5)

        alpha_before = state.posteriors["AP-TX-B"].alpha
        corr.propagate_update("AP-TX-A", 0.8, state)
        expected_delta = 0.8 * 0.5
        assert state.posteriors["AP-TX-B"].alpha == pytest.approx(alpha_before + expected_delta)

    def test_failure_propagation(self, sibling_techniques):
        corr = FamilyCorrelation(spillover_rate=0.3)
        corr.register_techniques(sibling_techniques)

        state = PosteriorState(prior_strength=3.0)
        for t in sibling_techniques:
            state.get_or_init(t.id, 0.5)

        beta_before = state.posteriors["AP-TX-B"].beta
        corr.propagate_update("AP-TX-A", 0.0, state)
        assert state.posteriors["AP-TX-B"].beta == pytest.approx(beta_before + 0.3)

    def test_empty_family(self, unrelated_technique):
        corr = FamilyCorrelation()
        corr.register_techniques([unrelated_technique])
        assert corr.get_siblings("AP-TX-X") == set()

    def test_unknown_technique_id(self):
        corr = FamilyCorrelation()
        corr.register_techniques([])
        assert corr.get_siblings("nonexistent") == set()
