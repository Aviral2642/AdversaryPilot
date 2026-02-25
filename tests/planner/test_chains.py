"""Tests for multi-stage attack chain planning."""

from __future__ import annotations

import pytest

from adversarypilot.models.enums import (
    AccessLevel,
    Domain,
    Goal,
    JudgeType,
    Phase,
    StealthLevel,
    Surface,
    TargetType,
)
from adversarypilot.models.plan import AttackPlan, PlanEntry, ScoreBreakdown
from adversarypilot.models.results import ComparabilityMetadata, EvaluationResult
from adversarypilot.models.target import TargetProfile
from adversarypilot.models.technique import AttackTechnique
from adversarypilot.planner.chains import (
    AttackChain,
    ChainPlanner,
    ChainStage,
    KILL_CHAIN_ORDER,
    suggest_escalation,
)
from adversarypilot.taxonomy.registry import TechniqueRegistry


@pytest.fixture
def chain_registry() -> TechniqueRegistry:
    reg = TechniqueRegistry()
    reg.load_catalog()
    return reg


@pytest.fixture
def jailbreak_target() -> TargetProfile:
    return TargetProfile(
        name="Test Chatbot",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK],
    )


@pytest.fixture
def agent_target() -> TargetProfile:
    return TargetProfile(
        name="Test Agent",
        target_type=TargetType.AGENT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.TOOL_MISUSE, Goal.EXFIL_SIM],
    )


def test_chain_stage_to_dict():
    stage = ChainStage(
        stage_number=0,
        technique_id="AP-TX-LLM-REFUSAL-BOUNDARY",
        technique_name="Refusal Boundary Mapping",
        phase=Phase.RECON,
        surface=Surface.GUARDRAIL,
        estimated_cost=0.4,
        rationale="Recon phase",
        depends_on=[],
        fallback_techniques=["AP-TX-LLM-GUARDRAIL-RECON"],
    )
    d = stage.to_dict()
    assert d["stage"] == 0
    assert d["technique_id"] == "AP-TX-LLM-REFUSAL-BOUNDARY"
    assert d["fallback_techniques"] == ["AP-TX-LLM-GUARDRAIL-RECON"]


def test_attack_chain_total_cost():
    stages = [
        ChainStage(0, "t1", "T1", Phase.RECON, Surface.GUARDRAIL, 0.2),
        ChainStage(1, "t2", "T2", Phase.PROBE, Surface.MODEL, 0.3),
        ChainStage(2, "t3", "T3", Phase.EXPLOIT, Surface.MODEL, 0.5),
    ]
    chain = AttackChain("chain-1", "test chain", stages, Goal.JAILBREAK)
    assert chain.total_cost == pytest.approx(1.0)


def test_attack_chain_phase_sequence():
    stages = [
        ChainStage(0, "t1", "T1", Phase.RECON, Surface.GUARDRAIL, 0.2),
        ChainStage(1, "t2", "T2", Phase.PROBE, Surface.MODEL, 0.3),
        ChainStage(2, "t3", "T3", Phase.EXPLOIT, Surface.MODEL, 0.5),
    ]
    chain = AttackChain("chain-1", "test chain", stages, Goal.JAILBREAK)
    assert chain.phase_sequence == [Phase.RECON, Phase.PROBE, Phase.EXPLOIT]


def test_attack_chain_to_dict():
    chain = AttackChain("chain-1", "test chain", [], Goal.JAILBREAK)
    d = chain.to_dict()
    assert d["chain_id"] == "chain-1"
    assert d["total_cost"] == 0.0


def test_chain_planner_builds_chains(chain_registry, jailbreak_target):
    planner = ChainPlanner(chain_registry, max_chain_length=5, max_chains=3)
    plan = AttackPlan(target=jailbreak_target, entries=[])
    chains = planner.plan_chains(jailbreak_target, plan)

    assert len(chains) > 0
    for chain in chains:
        assert len(chain.stages) > 0
        assert chain.target_goal == Goal.JAILBREAK


def test_chain_planner_respects_max_chain_length(chain_registry, jailbreak_target):
    planner = ChainPlanner(chain_registry, max_chain_length=2, max_chains=3)
    plan = AttackPlan(target=jailbreak_target, entries=[])
    chains = planner.plan_chains(jailbreak_target, plan)

    for chain in chains:
        assert len(chain.stages) <= 2


def test_chain_planner_respects_max_chains(chain_registry, jailbreak_target):
    planner = ChainPlanner(chain_registry, max_chain_length=5, max_chains=1)
    plan = AttackPlan(target=jailbreak_target, entries=[])
    chains = planner.plan_chains(jailbreak_target, plan)

    assert len(chains) <= 1


def test_chain_planner_multiple_goals(chain_registry, agent_target):
    planner = ChainPlanner(chain_registry, max_chain_length=5, max_chains=5)
    plan = AttackPlan(target=agent_target, entries=[])
    chains = planner.plan_chains(agent_target, plan)

    # Should have chains for tool_misuse and exfil_sim
    goals_covered = {c.target_goal for c in chains}
    assert len(goals_covered) >= 1  # At least one goal should have techniques


def test_chain_planner_stages_have_fallbacks(chain_registry, jailbreak_target):
    planner = ChainPlanner(chain_registry, max_chain_length=5, max_chains=3)
    plan = AttackPlan(target=jailbreak_target, entries=[])
    chains = planner.plan_chains(jailbreak_target, plan)

    # At least some stages should have fallback techniques
    has_fallbacks = any(
        len(stage.fallback_techniques) > 0
        for chain in chains
        for stage in chain.stages
    )
    assert has_fallbacks


def test_chain_planner_adapts_to_failed_surfaces(chain_registry, jailbreak_target):
    planner = ChainPlanner(chain_registry, max_chain_length=5, max_chains=3)

    # Create prior results showing guardrail failures
    prior_results = []
    for i in range(3):
        prior_results.append(EvaluationResult(
            attempt_id=f"att-{i}",
            success=False,
            score=0.1,
            judge_type=JudgeType.RULE_BASED,
            confidence=0.8,
            evidence_quality=0.7,
            comparability=ComparabilityMetadata(
                technique_id="AP-TX-LLM-JAILBREAK-DAN",
                judge_type=JudgeType.RULE_BASED,
                num_trials=1,
            ),
        ))

    plan = AttackPlan(target=jailbreak_target, entries=[])
    chains = planner.plan_chains(jailbreak_target, plan, prior_results)

    # Should still produce chains (adapting around defended surfaces)
    assert len(chains) > 0


def test_kill_chain_order():
    assert KILL_CHAIN_ORDER[Phase.RECON] < KILL_CHAIN_ORDER[Phase.PROBE]
    assert KILL_CHAIN_ORDER[Phase.PROBE] < KILL_CHAIN_ORDER[Phase.EXPLOIT]
    assert KILL_CHAIN_ORDER[Phase.EXPLOIT] < KILL_CHAIN_ORDER[Phase.PERSISTENCE]


def test_suggest_escalation_known_path():
    surfaces = suggest_escalation(Surface.GUARDRAIL, Goal.JAILBREAK)
    assert len(surfaces) > 0
    assert Surface.MODEL in surfaces


def test_suggest_escalation_default_fallback():
    surfaces = suggest_escalation(Surface.MODEL, Goal.DOS)
    assert len(surfaces) > 0
    assert Surface.MODEL not in surfaces  # Should not suggest current surface
