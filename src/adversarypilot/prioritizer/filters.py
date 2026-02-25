"""Hard filter predicates for technique elimination."""

from __future__ import annotations

from adversarypilot.models.enums import AccessLevel
from adversarypilot.models.target import TargetProfile
from adversarypilot.models.technique import AttackTechnique

ACCESS_ORDER = {
    AccessLevel.BLACK_BOX: 0,
    AccessLevel.GRAY_BOX: 1,
    AccessLevel.WHITE_BOX: 2,
}


def is_target_type_compatible(technique: AttackTechnique, target: TargetProfile) -> bool:
    """Reject if target type is not in the technique's supported list."""
    if not technique.target_types:
        return True
    return target.target_type in technique.target_types


def is_access_sufficient(technique: AttackTechnique, target: TargetProfile) -> bool:
    """Reject if technique requires more access than available."""
    available = ACCESS_ORDER.get(target.access_level, 0)
    required = ACCESS_ORDER.get(technique.access_required, 0)
    return available >= required


def is_within_budget(technique: AttackTechnique, target: TargetProfile) -> bool:
    """Reject if technique cost exceeds budget constraints."""
    max_cost = target.constraints.custom_constraints.get("max_technique_cost")
    if max_cost is not None and technique.base_cost > max_cost:
        return False
    return True


def is_goal_relevant(technique: AttackTechnique, target: TargetProfile) -> bool:
    """Reject if technique supports none of the target's goals."""
    if not target.goals:
        return True
    return bool(set(technique.goals_supported) & set(target.goals))


def passes_all_filters(technique: AttackTechnique, target: TargetProfile) -> bool:
    """Apply all hard filters. Returns True if technique passes."""
    return (
        is_target_type_compatible(technique, target)
        and is_access_sufficient(technique, target)
        and is_within_budget(technique, target)
        and is_goal_relevant(technique, target)
    )
