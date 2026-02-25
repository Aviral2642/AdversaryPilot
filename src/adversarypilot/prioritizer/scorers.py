"""Scoring functions for technique ranking.

All thresholds are configurable via scorer_thresholds in config.yaml.
Functions accept an optional thresholds dict with configurable defaults.
"""

from __future__ import annotations

from adversarypilot.models.enums import AccessLevel, StealthLevel, Surface
from adversarypilot.models.results import EvaluationResult
from adversarypilot.models.target import TargetProfile
from adversarypilot.models.technique import AttackTechnique
from adversarypilot.prioritizer.filters import ACCESS_ORDER

DEFAULT_THRESHOLDS: dict[str, dict[str, float]] = {
    "defense_bypass": {
        "no_defenses_baseline": 0.8,
        "min_bypass_likelihood": 0.1,
        "defense_impact_factor": 0.7,
    },
    "signal_gain": {
        "untried_score": 1.0,
        "default_score": 0.7,
        "inconclusive_score": 0.5,
        "already_tested_score": 0.1,
    },
    "compatibility": {
        "exact_match": 1.0,
        "no_types_listed": 0.5,
        "no_match": 0.0,
    },
    "access_fit": {
        "exact_match": 1.0,
        "overqualified_floor": 0.5,
        "overqualified_decay": 0.2,
    },
    "stealth_penalty": {
        "overt": 1.0,
        "moderate": 0.5,
        "covert": 0.1,
    },
    "detection_risk": {
        "moderate_multiplier": 0.5,
    },
}

DEFENSE_SURFACE_MAP: dict[str, Surface] = {
    "has_moderation": Surface.GUARDRAIL,
    "has_input_filtering": Surface.GUARDRAIL,
    "has_output_filtering": Surface.GUARDRAIL,
    "has_prompt_injection_detection": Surface.MODEL,
    "has_schema_validation": Surface.TOOL,
    "has_rate_limiting": Surface.MODEL,
}


def _get(thresholds: dict | None, section: str, key: str) -> float:
    """Look up a threshold value with fallback to defaults."""
    if thresholds:
        section_dict = thresholds.get(section, {})
        if key in section_dict:
            return float(section_dict[key])
    return DEFAULT_THRESHOLDS[section][key]


def score_compatibility(
    technique: AttackTechnique,
    target: TargetProfile,
    thresholds: dict | None = None,
) -> float:
    """How well the technique fits the target type."""
    if not technique.target_types:
        return _get(thresholds, "compatibility", "no_types_listed")
    if target.target_type in technique.target_types:
        return _get(thresholds, "compatibility", "exact_match")
    return _get(thresholds, "compatibility", "no_match")


def score_access_fit(
    technique: AttackTechnique,
    target: TargetProfile,
    thresholds: dict | None = None,
) -> float:
    """Higher score when access level exactly matches."""
    available = ACCESS_ORDER.get(target.access_level, 0)
    required = ACCESS_ORDER.get(technique.access_required, 0)
    if available < required:
        return 0.0
    if available == required:
        return _get(thresholds, "access_fit", "exact_match")
    floor = _get(thresholds, "access_fit", "overqualified_floor")
    decay = _get(thresholds, "access_fit", "overqualified_decay")
    return max(floor, 1.0 - decay * (available - required))


def score_goal_fit(technique: AttackTechnique, target: TargetProfile) -> float:
    """Fraction of target goals this technique supports."""
    if not target.goals:
        return 0.5
    if not technique.goals_supported:
        return 0.0
    overlap = len(set(technique.goals_supported) & set(target.goals))
    return overlap / len(target.goals)


def score_defense_bypass_likelihood(
    technique: AttackTechnique,
    target: TargetProfile,
    thresholds: dict | None = None,
) -> float:
    """Heuristic: lower score if active defenses protect the technique's target surface."""
    defenses = target.defenses
    relevant_defenses = 0
    active_defenses = 0

    for defense_field, surface in DEFENSE_SURFACE_MAP.items():
        if surface == technique.surface:
            relevant_defenses += 1
            if getattr(defenses, defense_field, False):
                active_defenses += 1

    if relevant_defenses == 0:
        return _get(thresholds, "defense_bypass", "no_defenses_baseline")

    min_val = _get(thresholds, "defense_bypass", "min_bypass_likelihood")
    impact = _get(thresholds, "defense_bypass", "defense_impact_factor")
    return max(min_val, 1.0 - (active_defenses / relevant_defenses) * impact)


def score_signal_gain(
    technique: AttackTechnique,
    prior_results: list[EvaluationResult] | None = None,
    thresholds: dict | None = None,
) -> float:
    """How much new information this technique provides."""
    if not prior_results:
        return _get(thresholds, "signal_gain", "default_score")

    tried_techniques = {r.comparability.technique_id for r in prior_results}
    if technique.id not in tried_techniques:
        return _get(thresholds, "signal_gain", "untried_score")

    technique_results = [
        r for r in prior_results if r.comparability.technique_id == technique.id
    ]
    inconclusive = sum(1 for r in technique_results if r.success is None)
    if inconclusive > 0:
        return _get(thresholds, "signal_gain", "inconclusive_score")

    return _get(thresholds, "signal_gain", "already_tested_score")


def score_cost_penalty(technique: AttackTechnique) -> float:
    """Direct cost penalty from base_cost."""
    return technique.base_cost


def score_detection_risk_penalty(
    technique: AttackTechnique,
    target: TargetProfile,
    thresholds: dict | None = None,
) -> float:
    """Penalty based on stealth profile vs. target's stealth priority."""
    if target.constraints.stealth_priority == StealthLevel.OVERT:
        return 0.0

    stealth_vals = {
        StealthLevel.OVERT: _get(thresholds, "stealth_penalty", "overt"),
        StealthLevel.MODERATE: _get(thresholds, "stealth_penalty", "moderate"),
        StealthLevel.COVERT: _get(thresholds, "stealth_penalty", "covert"),
    }
    technique_risk = stealth_vals.get(technique.stealth_profile, 0.5)

    if target.constraints.stealth_priority == StealthLevel.COVERT:
        return technique_risk
    mod_mult = _get(thresholds, "detection_risk", "moderate_multiplier")
    return technique_risk * mod_mult
