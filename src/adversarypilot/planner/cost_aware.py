"""Cost-aware utility computation for adaptive planning."""

import math

from adversarypilot.models.enums import Goal, Surface
from adversarypilot.models.technique import AttackTechnique

# Goal severity weights (higher = more severe impact)
GOAL_SEVERITY: dict[Goal, float] = {
    Goal.EXFIL_SIM: 1.0,
    Goal.TOOL_MISUSE: 0.95,
    Goal.EXTRACTION: 0.9,
    Goal.JAILBREAK: 0.8,
    Goal.EVASION: 0.7,
    Goal.POISONING: 1.0,
    Goal.DOS: 0.6,
}

# Surface criticality weights (higher = more critical layer)
SURFACE_CRITICALITY: dict[Surface, float] = {
    Surface.ACTION: 0.95,
    Surface.DATA: 0.9,
    Surface.TOOL: 0.85,
    Surface.RETRIEVAL: 0.8,
    Surface.MODEL: 0.7,
    Surface.GUARDRAIL: 0.6,
}


def compute_impact_weight(
    technique: AttackTechnique,
    target_goals: list[Goal],
    goal_severity: dict[Goal, float] | None = None,
    surface_criticality: dict[Surface, float] | None = None,
) -> float:
    """Compute impact weight for a technique.

    Impact = max_goal_severity × surface_criticality

    Args:
        technique: Technique to score
        target_goals: Target's priority goals
        goal_severity: Optional custom goal severity weights
        surface_criticality: Optional custom surface weights

    Returns:
        Impact weight (0.0-1.0)
    """
    goal_sev = goal_severity or GOAL_SEVERITY
    surf_crit = surface_criticality or SURFACE_CRITICALITY

    # Find max severity of relevant goals
    relevant_goals = set(target_goals) & set(technique.goals_supported)
    if not relevant_goals:
        max_goal_sev = 0.0
    else:
        max_goal_sev = max(goal_sev.get(g, 0.5) for g in relevant_goals)

    # Get surface criticality
    surf_weight = surf_crit.get(technique.surface, 0.5)

    return max_goal_sev * surf_weight


def compute_cost(
    technique: AttackTechnique, max_cost: float = 1.0
) -> float:
    """Compute normalized cost for a technique.

    Args:
        technique: Technique to score
        max_cost: Maximum allowable cost (for normalization)

    Returns:
        Normalized cost (0.0-1.0)
    """
    return min(technique.base_cost / max(max_cost, 0.01), 1.0)


def compute_utility(
    success_prob: float,
    impact_weight: float,
    cost: float,
    cost_weight: float,
    info_gain_bonus: float = 0.0,
    detection_penalty: float = 0.0,
    diversity_bonus: float = 0.0,
) -> float:
    """Compute additive cost-aware utility.

    Formula:
        utility = p * impact + info_gain + diversity - detection - λ * cost

    Args:
        success_prob: Sampled success probability (Thompson sample)
        impact_weight: Impact score from compute_impact_weight()
        cost: Normalized cost from compute_cost()
        cost_weight: Lambda parameter for cost penalty (default 0.4)
        info_gain_bonus: Information gain bonus (default 0.0)
        detection_penalty: Detection risk penalty (default 0.0)
        diversity_bonus: Diversity bonus (default 0.0)

    Returns:
        Utility score (unbounded, but typically 0.0-2.0)
    """
    return (
        success_prob * impact_weight
        + info_gain_bonus
        + diversity_bonus
        - detection_penalty
        - cost_weight * cost
    )


def normalize_utility(raw: float, midpoint: float = 0.5, steepness: float = 4.0) -> float:
    """Normalize unbounded utility to [0, 1] via logistic sigmoid.

    Maps the full real line to (0, 1) with the midpoint at the given value.
    steepness controls how quickly values saturate toward 0 or 1.
    """
    return 1.0 / (1.0 + math.exp(-steepness * (raw - midpoint)))
