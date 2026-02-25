"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from adversarypilot.models.enums import (
    AccessLevel,
    CampaignStatus,
    Domain,
    Goal,
    JudgeType,
    Phase,
    StealthLevel,
    Surface,
    TargetType,
)
from adversarypilot.models.results import AttemptResult, ComparabilityMetadata, EvaluationResult
from adversarypilot.models.target import ConstraintSpec, DefenseProfile, TargetProfile
from adversarypilot.models.technique import AttackTechnique, AtlasReference
from adversarypilot.taxonomy.registry import TechniqueRegistry

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def chatbot_target() -> TargetProfile:
    return TargetProfile(
        name="Test Chatbot",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK],
        constraints=ConstraintSpec(max_queries=100, stealth_priority=StealthLevel.OVERT),
        defenses=DefenseProfile(has_moderation=True),
    )


@pytest.fixture
def classifier_target() -> TargetProfile:
    return TargetProfile(
        name="Test Classifier",
        target_type=TargetType.CLASSIFIER,
        access_level=AccessLevel.WHITE_BOX,
        goals=[Goal.EVASION],
    )


@pytest.fixture
def registry() -> TechniqueRegistry:
    reg = TechniqueRegistry()
    reg.load_catalog()
    return reg


@pytest.fixture
def sample_technique() -> AttackTechnique:
    return AttackTechnique(
        id="AP-TX-TEST-001",
        name="Test Technique",
        domain=Domain.LLM,
        phase=Phase.EXPLOIT,
        surface=Surface.GUARDRAIL,
        access_required=AccessLevel.BLACK_BOX,
        goals_supported=[Goal.JAILBREAK],
        target_types=[TargetType.CHATBOT],
        atlas_refs=[AtlasReference(atlas_id="AML.T0051", atlas_name="LLM Prompt Injection")],
        base_cost=0.3,
    )


@pytest.fixture
def sample_results() -> list[tuple[AttemptResult, EvaluationResult]]:
    pairs = []
    for i in range(5):
        attempt = AttemptResult(
            id=f"test-att-{i}",
            technique_id="AP-TX-LLM-JAILBREAK-DAN",
            prompt=f"test prompt {i}",
            response=f"test response {i}",
            source_tool="test",
        )
        evaluation = EvaluationResult(
            attempt_id=f"test-att-{i}",
            success=i % 2 == 0,  # alternating success/failure
            score=0.8 if i % 2 == 0 else 0.2,
            judge_type=JudgeType.RULE_BASED,
            confidence=0.8,
            evidence_quality=0.7,
            comparability=ComparabilityMetadata(
                technique_id="AP-TX-LLM-JAILBREAK-DAN",
                judge_type=JudgeType.RULE_BASED,
                num_trials=1,
            ),
        )
        pairs.append((attempt, evaluation))
    return pairs


@pytest.fixture
def garak_report_path() -> Path:
    return FIXTURES_DIR / "sample_garak_report.jsonl"
