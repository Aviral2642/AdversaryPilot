"""Tests for technique registry."""

from adversarypilot.models.enums import AccessLevel, Domain, Goal, Surface, TargetType
from adversarypilot.taxonomy.registry import TechniqueRegistry


def test_load_catalog(registry):
    assert len(registry) == 70


def test_get_technique(registry):
    t = registry.get("AP-TX-LLM-JAILBREAK-DAN")
    assert t is not None
    assert t.name == "DAN-style Jailbreak"
    assert t.domain == Domain.LLM


def test_get_missing_technique(registry):
    assert registry.get("AP-TX-NONEXISTENT") is None


def test_contains(registry):
    assert "AP-TX-LLM-JAILBREAK-DAN" in registry
    assert "AP-TX-NONEXISTENT" not in registry


def test_filter_by_domain(registry):
    llm = registry.filter(domain=Domain.LLM)
    assert len(llm) == 33
    assert all(t.domain == Domain.LLM for t in llm)

    agent = registry.filter(domain=Domain.AGENT)
    assert len(agent) == 25

    aml = registry.filter(domain=Domain.AML)
    assert len(aml) == 12


def test_filter_by_goal(registry):
    jailbreak = registry.filter(goal=Goal.JAILBREAK)
    assert len(jailbreak) > 0
    assert all(Goal.JAILBREAK in t.goals_supported for t in jailbreak)


def test_filter_by_surface(registry):
    guardrail = registry.filter(surface=Surface.GUARDRAIL)
    assert len(guardrail) > 0
    assert all(t.surface == Surface.GUARDRAIL for t in guardrail)


def test_filter_by_target_type(registry):
    chatbot = registry.filter(target_type=TargetType.CHATBOT)
    assert len(chatbot) > 0
    assert all(TargetType.CHATBOT in t.target_types for t in chatbot)


def test_filter_by_tool(registry):
    garak = registry.filter(tool="garak")
    assert len(garak) > 0
    assert all("garak" in t.tool_support for t in garak)


def test_filter_combined(registry):
    results = registry.filter(domain=Domain.LLM, goal=Goal.JAILBREAK)
    assert len(results) > 0
    assert all(t.domain == Domain.LLM and Goal.JAILBREAK in t.goals_supported for t in results)


def test_filter_no_results(registry):
    results = registry.filter(domain=Domain.AML, goal=Goal.JAILBREAK)
    assert len(results) == 0


def test_get_all(registry):
    all_techniques = registry.get_all()
    assert len(all_techniques) == 70


def test_atlas_refs_present(registry):
    t = registry.get("AP-TX-LLM-JAILBREAK-DAN")
    assert len(t.atlas_refs) > 0
    assert t.atlas_refs[0].atlas_id == "AML.T0051"
