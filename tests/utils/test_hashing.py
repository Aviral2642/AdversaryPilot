"""Tests for hashing utilities."""

from adversarypilot.models.enums import Goal, JudgeType, TargetType
from adversarypilot.models.target import TargetProfile
from adversarypilot.utils.hashing import (
    derive_comparable_group_key,
    hash_success_criteria,
    hash_target_profile,
    hash_technique_config,
)


def test_hash_target_profile_deterministic(chatbot_target):
    """Test that hashing produces deterministic results."""
    hash1 = hash_target_profile(chatbot_target)
    hash2 = hash_target_profile(chatbot_target)
    assert hash1 == hash2
    assert len(hash1) == 16


def test_hash_target_profile_different_targets():
    """Test that different targets produce different hashes."""
    target1 = TargetProfile(
        name="Target1",
        target_type=TargetType.CHATBOT,
        access_level="black_box",
        goals=[Goal.JAILBREAK],
    )
    target2 = TargetProfile(
        name="Target2",
        target_type=TargetType.RAG,
        access_level="black_box",
        goals=[Goal.JAILBREAK],
    )

    hash1 = hash_target_profile(target1)
    hash2 = hash_target_profile(target2)
    assert hash1 != hash2


def test_hash_technique_config_basic():
    """Test basic technique config hashing."""
    hash1 = hash_technique_config("AP-TX-LLM-JAILBREAK-DAN")
    hash2 = hash_technique_config("AP-TX-LLM-JAILBREAK-DAN")
    assert hash1 == hash2
    assert len(hash1) == 16


def test_hash_success_criteria():
    """Test success criteria hashing."""
    judge_config = {"threshold": 0.5, "model": "gpt-4"}
    hash1 = hash_success_criteria(JudgeType.LLM_JUDGE, judge_config)
    hash2 = hash_success_criteria(JudgeType.LLM_JUDGE, judge_config)
    assert hash1 == hash2


def test_hash_success_criteria_different_config():
    """Test that different configs produce different hashes."""
    config1 = {"threshold": 0.5}
    config2 = {"threshold": 0.7}
    hash1 = hash_success_criteria(JudgeType.RULE_BASED, config1)
    hash2 = hash_success_criteria(JudgeType.RULE_BASED, config2)
    assert hash1 != hash2


def test_derive_comparable_group_key(sample_results):
    """Test comparable group key derivation."""
    from adversarypilot.models.results import ComparabilityMetadata

    comp = ComparabilityMetadata(
        target_profile_hash="hash1",
        technique_config_hash="hash2",
        success_criteria_hash="hash3",
        judge_type=JudgeType.RULE_BASED,
    )

    key = derive_comparable_group_key(comp)
    assert key != ""
    assert len(key) == 16


def test_derive_comparable_group_key_missing_fields():
    """Test that missing fields return empty key."""
    from adversarypilot.models.results import ComparabilityMetadata

    comp = ComparabilityMetadata(
        technique_config_hash="hash2",  # Missing target and criteria
    )

    key = derive_comparable_group_key(comp)
    assert key == ""
