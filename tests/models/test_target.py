"""Tests for target profile models."""

import json

import yaml

from adversarypilot.models.target import ConstraintSpec, DefenseProfile, TargetProfile


def test_target_profile_minimal():
    t = TargetProfile(name="test", target_type="chatbot", access_level="black_box")
    assert t.name == "test"
    assert t.schema_version == "1.0"
    assert t.goals == []
    assert t.defenses.has_moderation is False


def test_target_profile_full(chatbot_target):
    assert chatbot_target.target_type == "chatbot"
    assert chatbot_target.access_level == "black_box"
    assert chatbot_target.constraints.max_queries == 100
    assert chatbot_target.defenses.has_moderation is True


def test_target_profile_serialization_roundtrip(chatbot_target):
    json_str = chatbot_target.model_dump_json()
    restored = TargetProfile.model_validate_json(json_str)
    assert restored.name == chatbot_target.name
    assert restored.target_type == chatbot_target.target_type


def test_target_profile_from_yaml():
    yaml_str = """
name: YAML Target
target_type: rag
access_level: gray_box
goals:
  - jailbreak
  - extraction
defenses:
  has_moderation: true
  has_prompt_injection_detection: true
"""
    data = yaml.safe_load(yaml_str)
    t = TargetProfile.model_validate(data)
    assert t.target_type == "rag"
    assert len(t.goals) == 2
    assert t.defenses.has_prompt_injection_detection is True


def test_constraint_spec_defaults():
    c = ConstraintSpec()
    assert c.max_queries is None
    assert c.stealth_priority == "overt"


def test_defense_profile_defaults():
    d = DefenseProfile()
    assert d.has_moderation is False
    assert d.known_defenses == []
