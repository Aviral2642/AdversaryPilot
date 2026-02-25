"""Comparability hashing utilities for AdversaryPilot."""

import hashlib
import json
from typing import Any

from adversarypilot.models.enums import JudgeType


def _stable_hash(data: dict[str, Any]) -> str:
    """Generate stable SHA256 hash from dictionary.

    Args:
        data: Dictionary to hash (must be JSON-serializable)

    Returns:
        str: First 16 characters of hex digest
    """
    json_str = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(json_str.encode("utf-8")).hexdigest()[:16]


def hash_target_profile(target: "TargetProfile") -> str:  # noqa: F821
    """Hash target profile for comparability grouping.

    Includes: target_type, access_level, goals, defense profile, constraints.

    Args:
        target: TargetProfile to hash

    Returns:
        str: Deterministic hash string
    """
    from adversarypilot.models.target import TargetProfile

    if not isinstance(target, TargetProfile):
        return ""

    data = {
        "target_type": target.target_type,
        "access_level": target.access_level,
        "goals": sorted(target.goals),
        "defenses": target.defenses.model_dump(exclude={"notes"}),
        "constraints": target.constraints.model_dump(exclude={"custom_constraints"}),
    }
    return _stable_hash(data)


def hash_technique_config(
    technique_id: str, exec_spec: "TechniqueExecutionSpec | None" = None  # noqa: F821
) -> str:
    """Hash technique configuration for comparability grouping.

    Includes: technique_id, query_budget, prompt_set, seed, judge_config.

    Args:
        technique_id: Technique identifier
        exec_spec: Optional execution spec with configuration

    Returns:
        str: Deterministic hash string
    """
    data = {"technique_id": technique_id}

    if exec_spec is not None:
        data.update(
            {
                "query_budget": exec_spec.query_budget,
                "prompt_set": exec_spec.prompt_set,
                "seed": exec_spec.seed,
                "judge_config": exec_spec.judge_config,
            }
        )

    return _stable_hash(data)


def hash_success_criteria(judge_type: JudgeType, judge_config: dict[str, Any]) -> str:
    """Hash success criteria for comparability grouping.

    Includes: judge_type, relevant judge_config parameters.

    Args:
        judge_type: Type of judge used
        judge_config: Judge configuration dictionary

    Returns:
        str: Deterministic hash string
    """
    # Filter judge_config to only include fields that affect success determination
    relevant_config = {
        k: v
        for k, v in judge_config.items()
        if k
        in {
            "threshold",
            "criteria",
            "model",
            "prompt_template",
            "temperature",
            "keywords",
            "patterns",
        }
    }

    data = {"judge_type": judge_type, "config": relevant_config}
    return _stable_hash(data)


def hash_file(path: str) -> str:
    """Compute SHA-256 hash of a file's contents.

    Args:
        path: Path to the file

    Returns:
        str: First 16 characters of hex digest
    """
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def compute_reproducibility_token(
    audit_trail: dict[str, Any],
    repro_metadata: dict[str, Any],
) -> str:
    """Compute a deterministic reproducibility token from audit + repro metadata.

    Args:
        audit_trail: Audit trail dict
        repro_metadata: Reproducibility metadata dict

    Returns:
        str: Deterministic reproducibility token
    """
    combined = {
        "config_hash": audit_trail.get("config_hash", ""),
        "catalog_hash": audit_trail.get("catalog_hash", ""),
        "target_hash": audit_trail.get("target_profile_hash", ""),
        "campaign_seed": repro_metadata.get("campaign_seed"),
        "catalog_version": repro_metadata.get("catalog_version", ""),
    }
    return _stable_hash(combined)


def derive_comparable_group_key(comparability: "ComparabilityMetadata") -> str:  # noqa: F821
    """Derive canonical comparable group key from comparability metadata.

    Results with the same group key can be directly compared.
    Based on: target, technique config, judge type, success criteria.

    Args:
        comparability: ComparabilityMetadata to derive key from

    Returns:
        str: Canonical group key
    """
    from adversarypilot.models.results import ComparabilityMetadata

    if not isinstance(comparability, ComparabilityMetadata):
        return ""

    # Warn if critical fields are missing
    missing_fields = []
    if not comparability.target_profile_hash:
        missing_fields.append("target_profile_hash")
    if not comparability.technique_config_hash:
        missing_fields.append("technique_config_hash")
    if not comparability.success_criteria_hash:
        missing_fields.append("success_criteria_hash")

    if missing_fields:
        # Return empty to signal incomplete metadata
        return ""

    data = {
        "target": comparability.target_profile_hash,
        "technique": comparability.technique_config_hash,
        "judge_type": comparability.judge_type,
        "criteria": comparability.success_criteria_hash,
        "judge_version": comparability.judge_model_version or "",
    }

    return _stable_hash(data)
