"""Execution hook generator — produces exact CLI commands for garak and promptfoo.

For each technique with tool_support, generates the shell command to run
the corresponding garak probe or promptfoo red-team test.
"""

from __future__ import annotations

from adversarypilot.models.target import TargetProfile
from adversarypilot.models.technique import AttackTechnique

# Maps technique IDs to garak probe classes
GARAK_PROBE_MAP: dict[str, str] = {
    "AP-TX-LLM-JAILBREAK-DAN": "probes.dan.Dan_6_0",
    "AP-TX-LLM-JAILBREAK-PERSONA": "probes.goodside.WhoIsRiley",
    "AP-TX-LLM-TAP-TREE": "probes.tap.TAP",
    "AP-TX-LLM-PAIR-ITERATIVE": "probes.tap.PAIR",
    "AP-TX-LLM-CRESCENDO": "probes.crescendo.Crescendo",
    "AP-TX-LLM-ENCODING-BYPASS": "probes.encoding.InjectBase64",
    "AP-TX-LLM-INJECT-DIRECT": "probes.promptinject.HijackHateHumansMini",
    "AP-TX-LLM-INJECT-INDIRECT": "probes.latentinjection.LatentInjectionTranslationEnFr",
    "AP-TX-LLM-EXTRACT-TRAINING": "probes.leakreplay.LiteratureCloze80",
    "AP-TX-LLM-TOXICITY-PROBE": "probes.realtoxicityprompts.RTPSevere",
    "AP-TX-LLM-LANG-SWITCH": "probes.encoding.InjectROT13",
    "AP-TX-LLM-MANYSHOT": "probes.goodside.Glitch",
    "AP-TX-LLM-GCG-SUFFIX": "probes.suffix.GCGCached",
}

# Maps technique IDs to promptfoo red-team plugin types
PROMPTFOO_TEST_MAP: dict[str, str] = {
    "AP-TX-LLM-JAILBREAK-DAN": "jailbreak",
    "AP-TX-LLM-TAP-TREE": "jailbreak:tree",
    "AP-TX-LLM-INJECT-DIRECT": "promptInjection",
    "AP-TX-LLM-INJECT-INDIRECT": "indirectPromptInjection",
    "AP-TX-AGT-EXFIL-SIM": "pii",
    "AP-TX-LLM-TOXICITY-PROBE": "harmful",
    "AP-TX-LLM-HALLUCINATION": "hallucination",
    "AP-TX-LLM-EXTRACT-SYSPROMPT": "debug-access",
    "AP-TX-LLM-REFUSAL-BOUNDARY": "contracts",
    "AP-TX-AGT-GOAL-HIJACK": "hijacking",
    "AP-TX-AGT-TOOL-MISUSE": "excessive-agency",
}


class ExecutionHookGenerator:
    """Generates exact CLI commands for running techniques with external tools."""

    def generate(
        self,
        technique: AttackTechnique,
        target: TargetProfile | None = None,
    ) -> list[str]:
        """Generate execution hook commands for a technique.

        Args:
            technique: The attack technique
            target: Optional target profile for context

        Returns:
            List of shell command strings
        """
        hooks: list[str] = []

        model_flag = ""
        if target and hasattr(target, "name"):
            model_flag = f" --model_type openai --model_name {target.name}"

        # Garak command
        if technique.id in GARAK_PROBE_MAP:
            probe = GARAK_PROBE_MAP[technique.id]
            cmd = f"garak --model_type openai --probes {probe}"
            if "garak" in technique.tool_support:
                hooks.append(cmd)
            else:
                hooks.append(cmd)

        # Promptfoo command
        if technique.id in PROMPTFOO_TEST_MAP:
            plugin = PROMPTFOO_TEST_MAP[technique.id]
            cmd = f"promptfoo redteam run --plugins {plugin}"
            hooks.append(cmd)

        # If no specific tool mapping, try generic based on tool_support
        if not hooks and technique.tool_support:
            for tool in technique.tool_support:
                if tool == "garak":
                    hooks.append(f"garak --model_type openai --probes probes.{technique.tags[0] if technique.tags else 'generic'}")
                elif tool == "promptfoo":
                    hooks.append("promptfoo redteam run")

        return hooks
