"""Tests for enum definitions."""

from adversarypilot.models.enums import (
    AccessLevel,
    CampaignStatus,
    Domain,
    ExecutionMode,
    Goal,
    JudgeType,
    Phase,
    StealthLevel,
    Surface,
    TargetType,
)


def test_target_type_values():
    assert TargetType.CHATBOT == "chatbot"
    assert TargetType.RAG == "rag"
    assert TargetType.AGENT == "agent"
    assert len(TargetType) == 8


def test_access_level_ordering():
    levels = [AccessLevel.BLACK_BOX, AccessLevel.GRAY_BOX, AccessLevel.WHITE_BOX]
    assert all(isinstance(l, str) for l in levels)


def test_domain_values():
    assert set(Domain) == {Domain.AML, Domain.LLM, Domain.AGENT}


def test_surface_values():
    expected = {"model", "data", "retrieval", "tool", "action", "guardrail"}
    assert {s.value for s in Surface} == expected


def test_goal_values():
    assert Goal.JAILBREAK == "jailbreak"
    assert Goal.EXFIL_SIM == "exfil_sim"
    assert len(Goal) == 7


def test_enums_are_str():
    """All enums should be StrEnum for YAML/JSON serialization."""
    assert isinstance(TargetType.CHATBOT, str)
    assert isinstance(AccessLevel.BLACK_BOX, str)
    assert isinstance(Domain.LLM, str)
    assert isinstance(Phase.EXPLOIT, str)
    assert isinstance(Surface.MODEL, str)
    assert isinstance(Goal.EVASION, str)
    assert isinstance(ExecutionMode.MANUAL, str)
    assert isinstance(StealthLevel.OVERT, str)
    assert isinstance(JudgeType.KEYWORD, str)
    assert isinstance(CampaignStatus.ACTIVE, str)
