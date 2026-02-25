"""Tests for diversity tracking."""

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
from adversarypilot.planner.diversity import FamilyTracker


def _make_technique(
    tech_id: str = "t1",
    surface: Surface = Surface.MODEL,
    domain: Domain = Domain.LLM,
    tags: list[str] | None = None,
) -> AttackTechnique:
    return AttackTechnique(
        id=tech_id,
        name="Test",
        domain=domain,
        phase=Phase.EXPLOIT,
        surface=surface,
        access_required=AccessLevel.BLACK_BOX,
        goals_supported=[Goal.JAILBREAK],
        target_types=[TargetType.CHATBOT],
        base_cost=0.3,
        tags=tags or ["jailbreak"],
    )


class TestFamilyTracker:
    def test_untested_surface_bonus(self):
        tracker = FamilyTracker()
        tech = _make_technique(surface=Surface.MODEL)
        bonus = tracker.compute_diversity_bonus(tech)
        assert bonus == pytest.approx(0.3)  # untested_layer_bonus default

    def test_repeat_family_penalty(self):
        tracker = FamilyTracker()
        tech = _make_technique(surface=Surface.MODEL)
        tracker.mark_tried(tech)
        bonus = tracker.compute_diversity_bonus(tech)
        # Same family penalty: -0.15, surface already tested so no untested bonus
        assert bonus == pytest.approx(-0.15)

    def test_different_surface_after_tried(self):
        tracker = FamilyTracker()
        tech1 = _make_technique(tech_id="t1", surface=Surface.MODEL)
        tracker.mark_tried(tech1)

        tech2 = _make_technique(tech_id="t2", surface=Surface.GUARDRAIL, tags=["guardrail"])
        bonus = tracker.compute_diversity_bonus(tech2)
        # Untested surface: +0.3, different family: no penalty
        assert bonus == pytest.approx(0.3)

    def test_below_coverage_bonus(self):
        tracker = FamilyTracker(min_surface_coverage=3)
        tech = _make_technique(surface=Surface.MODEL, tags=["tag-a"])
        tracker.mark_tried(tech)

        # Same surface, different family → below coverage bonus, no repeat penalty
        tech2 = _make_technique(tech_id="t2", surface=Surface.MODEL, tags=["tag-b"])
        bonus = tracker.compute_diversity_bonus(tech2)
        # below_coverage_bonus=0.15, different family: no penalty
        assert bonus == pytest.approx(0.15)

    def test_surface_coverage_tracking(self):
        tracker = FamilyTracker()
        tech = _make_technique(surface=Surface.MODEL)
        tracker.mark_tried(tech)
        coverage = tracker.get_surface_coverage()
        assert coverage[Surface.MODEL] == 1

    def test_reset_clears_state(self):
        tracker = FamilyTracker()
        tech = _make_technique(surface=Surface.MODEL)
        tracker.mark_tried(tech)
        tracker.reset()
        assert tracker.get_surface_coverage() == {}
        # After reset, should get untested bonus again
        bonus = tracker.compute_diversity_bonus(tech)
        assert bonus == pytest.approx(0.3)
