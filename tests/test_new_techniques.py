"""Tests for new 2025 techniques — A2A, MCP, ATLAS Oct 2025 (WS6)."""

import pytest

from adversarypilot.models.enums import Domain, Surface, TargetType
from adversarypilot.taxonomy.registry import TechniqueRegistry


@pytest.fixture
def registry():
    r = TechniqueRegistry()
    r.load_catalog()
    return r


A2A_IDS = [
    "AP-TX-AGT-A2A-IMPERSONATION",
    "AP-TX-AGT-A2A-TASKPOISONING",
    "AP-TX-AGT-A2A-CARDMANIPULATION",
    "AP-TX-AGT-A2A-CONTEXTLEAK",
]

MCP_IDS = [
    "AP-TX-AGT-MCP-TOOLPOISONING",
    "AP-TX-AGT-MCP-SCHEMAINJECT",
    "AP-TX-AGT-MCP-SERVERSQUAT",
]

ATLAS_OCT_2025_IDS = [
    "AP-TX-AGT-DELEGATION-ABUSE",
    "AP-TX-AGT-MEMORY-POISONING",
    "AP-TX-AGT-OBSERVATION-MANIPULATION",
]

ALL_NEW_IDS = A2A_IDS + MCP_IDS + ATLAS_OCT_2025_IDS


class TestCatalogSize:
    def test_total_techniques_70(self, registry):
        assert len(registry.get_all()) == 70


class TestA2ATechniques:
    @pytest.mark.parametrize("tid", A2A_IDS)
    def test_exists(self, registry, tid):
        t = registry.get(tid)
        assert t is not None, f"{tid} not found"

    @pytest.mark.parametrize("tid", A2A_IDS)
    def test_is_agent_domain(self, registry, tid):
        assert registry.get(tid).domain == Domain.AGENT

    @pytest.mark.parametrize("tid", A2A_IDS)
    def test_has_a2a_tag(self, registry, tid):
        assert "a2a" in registry.get(tid).tags

    @pytest.mark.parametrize("tid", A2A_IDS)
    def test_targets_multi_agent(self, registry, tid):
        t = registry.get(tid)
        assert TargetType.MULTI_AGENT_SYSTEM in t.target_types or TargetType.AGENT in t.target_types


class TestMCPTechniques:
    @pytest.mark.parametrize("tid", MCP_IDS)
    def test_exists(self, registry, tid):
        t = registry.get(tid)
        assert t is not None, f"{tid} not found"

    @pytest.mark.parametrize("tid", MCP_IDS)
    def test_is_agent_domain(self, registry, tid):
        assert registry.get(tid).domain == Domain.AGENT

    @pytest.mark.parametrize("tid", MCP_IDS)
    def test_targets_tool_surface(self, registry, tid):
        assert registry.get(tid).surface == Surface.TOOL

    @pytest.mark.parametrize("tid", MCP_IDS)
    def test_has_mcp_tag(self, registry, tid):
        assert "mcp" in registry.get(tid).tags


class TestATLASOct2025:
    @pytest.mark.parametrize("tid", ATLAS_OCT_2025_IDS)
    def test_exists(self, registry, tid):
        assert registry.get(tid) is not None

    @pytest.mark.parametrize("tid", ATLAS_OCT_2025_IDS)
    def test_is_agent_domain(self, registry, tid):
        assert registry.get(tid).domain == Domain.AGENT


class TestAllNewTechniques:
    @pytest.mark.parametrize("tid", ALL_NEW_IDS)
    def test_has_compliance_refs(self, registry, tid):
        t = registry.get(tid)
        assert len(t.compliance_refs) > 0, f"{tid} missing compliance_refs"

    @pytest.mark.parametrize("tid", ALL_NEW_IDS)
    def test_has_atlas_refs(self, registry, tid):
        t = registry.get(tid)
        assert len(t.atlas_refs) > 0, f"{tid} missing atlas_refs"

    @pytest.mark.parametrize("tid", ALL_NEW_IDS)
    def test_has_goals(self, registry, tid):
        t = registry.get(tid)
        assert len(t.goals_supported) > 0, f"{tid} missing goals"
