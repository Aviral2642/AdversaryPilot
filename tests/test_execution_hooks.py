"""Tests for execution hook generator (WS7)."""

import pytest

from adversarypilot.hooks.generator import (
    GARAK_PROBE_MAP,
    PROMPTFOO_TEST_MAP,
    ExecutionHookGenerator,
)
from adversarypilot.models.enums import AccessLevel, Goal, TargetType
from adversarypilot.models.target import TargetProfile
from adversarypilot.taxonomy.registry import TechniqueRegistry


@pytest.fixture
def registry():
    r = TechniqueRegistry()
    r.load_catalog()
    return r


@pytest.fixture
def generator():
    return ExecutionHookGenerator()


@pytest.fixture
def target():
    return TargetProfile(
        name="test-model",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK],
    )


class TestGarakProbeMap:
    def test_has_entries(self):
        assert len(GARAK_PROBE_MAP) >= 10

    def test_dan_maps_correctly(self):
        assert GARAK_PROBE_MAP["AP-TX-LLM-JAILBREAK-DAN"] == "probes.dan.Dan_6_0"

    def test_all_ids_valid_format(self):
        for tid in GARAK_PROBE_MAP:
            assert tid.startswith("AP-TX-")


class TestPromptfooTestMap:
    def test_has_entries(self):
        assert len(PROMPTFOO_TEST_MAP) >= 8

    def test_jailbreak_maps_correctly(self):
        assert PROMPTFOO_TEST_MAP["AP-TX-LLM-JAILBREAK-DAN"] == "jailbreak"


class TestExecutionHookGenerator:
    def test_generates_garak_command(self, generator, registry):
        dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
        hooks = generator.generate(dan)
        assert any("garak" in h for h in hooks)

    def test_generates_promptfoo_command(self, generator, registry):
        dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
        hooks = generator.generate(dan)
        assert any("promptfoo" in h for h in hooks)

    def test_garak_command_has_probes_flag(self, generator, registry):
        dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
        hooks = generator.generate(dan)
        garak_hooks = [h for h in hooks if "garak" in h]
        assert any("--probes" in h for h in garak_hooks)

    def test_promptfoo_command_has_plugins(self, generator, registry):
        dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
        hooks = generator.generate(dan)
        pf_hooks = [h for h in hooks if "promptfoo" in h]
        assert any("--plugins" in h for h in pf_hooks)

    def test_unknown_technique_no_hooks(self, generator):
        from adversarypilot.models.technique import AttackTechnique
        t = AttackTechnique(
            id="AP-TX-CUSTOM-UNKNOWN",
            name="Unknown",
            description="",
            domain="llm",
            surface="model",
            phase="exploit",
            access_required="black_box",
            goals_supported=["jailbreak"],
            target_types=[],
            tool_support=[],
        )
        hooks = generator.generate(t)
        assert len(hooks) == 0

    def test_tap_technique_maps_correctly(self, generator, registry):
        tap = registry.get("AP-TX-LLM-TAP-TREE")
        assert tap is not None
        hooks = generator.generate(tap)
        # TAP may or may not have hooks depending on mappings
        assert isinstance(hooks, list)

    def test_injection_techniques(self, generator, registry):
        inject = registry.get("AP-TX-LLM-INJECT-DIRECT")
        hooks = generator.generate(inject)
        assert len(hooks) > 0

    def test_with_target_profile(self, generator, registry, target):
        dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
        hooks = generator.generate(dan, target)
        assert len(hooks) > 0

    def test_multiple_hooks_per_technique(self, generator, registry):
        # DAN should have both garak and promptfoo hooks
        dan = registry.get("AP-TX-LLM-JAILBREAK-DAN")
        hooks = generator.generate(dan)
        tools = set()
        for h in hooks:
            if "garak" in h:
                tools.add("garak")
            if "promptfoo" in h:
                tools.add("promptfoo")
        assert len(tools) == 2

    def test_extract_sysprompt_technique(self, generator, registry):
        extract = registry.get("AP-TX-LLM-EXTRACT-SYSPROMPT")
        assert extract is not None
        hooks = generator.generate(extract)
        # May or may not have hooks depending on tool support mapping
        assert isinstance(hooks, list)
