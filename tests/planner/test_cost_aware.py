"""Tests for cost-aware utility computation."""

import pytest

from adversarypilot.models.enums import (
    AccessLevel,
    Domain,
    Goal,
    Phase,
    Surface,
    TargetType,
)
from adversarypilot.models.technique import AttackTechnique
from adversarypilot.planner.cost_aware import (
    GOAL_SEVERITY,
    SURFACE_CRITICALITY,
    compute_cost,
    compute_impact_weight,
    compute_utility,
)


def _make_technique(
    surface: Surface = Surface.MODEL,
    goals: list[Goal] | None = None,
    base_cost: float = 0.5,
) -> AttackTechnique:
    return AttackTechnique(
        id="AP-TX-TEST",
        name="Test",
        domain=Domain.LLM,
        phase=Phase.EXPLOIT,
        surface=surface,
        access_required=AccessLevel.BLACK_BOX,
        goals_supported=goals or [Goal.JAILBREAK],
        target_types=[TargetType.CHATBOT],
        base_cost=base_cost,
    )


class TestComputeImpactWeight:
    def test_single_goal_match(self):
        tech = _make_technique(surface=Surface.MODEL, goals=[Goal.JAILBREAK])
        impact = compute_impact_weight(tech, [Goal.JAILBREAK])
        # jailbreak=0.8, model=0.7 → 0.56
        assert impact == pytest.approx(0.56)

    def test_no_goal_match(self):
        tech = _make_technique(goals=[Goal.EVASION])
        impact = compute_impact_weight(tech, [Goal.JAILBREAK])
        assert impact == 0.0

    def test_multiple_goals_takes_max(self):
        tech = _make_technique(goals=[Goal.JAILBREAK, Goal.EXFIL_SIM])
        impact = compute_impact_weight(tech, [Goal.JAILBREAK, Goal.EXFIL_SIM])
        # exfil_sim=1.0 > jailbreak=0.8, model=0.7 → 0.7
        assert impact == pytest.approx(0.7)

    def test_custom_weights(self):
        tech = _make_technique(surface=Surface.ACTION, goals=[Goal.JAILBREAK])
        custom_goal = {Goal.JAILBREAK: 1.0}
        custom_surf = {Surface.ACTION: 1.0}
        impact = compute_impact_weight(tech, [Goal.JAILBREAK], custom_goal, custom_surf)
        assert impact == pytest.approx(1.0)


class TestComputeCost:
    def test_normalized_cost(self):
        tech = _make_technique(base_cost=0.5)
        assert compute_cost(tech, max_cost=1.0) == pytest.approx(0.5)

    def test_cost_capped_at_one(self):
        tech = _make_technique(base_cost=1.0)
        assert compute_cost(tech, max_cost=0.5) == 1.0


class TestComputeUtility:
    def test_basic_utility(self):
        u = compute_utility(
            success_prob=0.8,
            impact_weight=0.7,
            cost=0.3,
            cost_weight=0.4,
        )
        # 0.8 * 0.7 - 0.4 * 0.3 = 0.56 - 0.12 = 0.44
        assert u == pytest.approx(0.44)

    def test_utility_with_all_components(self):
        u = compute_utility(
            success_prob=0.8,
            impact_weight=0.7,
            cost=0.3,
            cost_weight=0.4,
            info_gain_bonus=0.1,
            detection_penalty=0.05,
            diversity_bonus=0.2,
        )
        # 0.56 + 0.1 + 0.2 - 0.05 - 0.12 = 0.69
        assert u == pytest.approx(0.69)

    def test_zero_success_prob(self):
        u = compute_utility(0.0, 1.0, 0.0, 0.4)
        assert u == pytest.approx(0.0)
