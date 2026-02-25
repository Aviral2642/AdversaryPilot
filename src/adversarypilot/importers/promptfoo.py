"""Promptfoo importer — parses promptfoo JSON evaluation output into AdversaryPilot result pairs."""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path

from adversarypilot.importers.base import AbstractImporter
from adversarypilot.models.enums import JudgeType
from adversarypilot.models.results import AttemptResult, ComparabilityMetadata, EvaluationResult
from adversarypilot.utils.hashing import hash_success_criteria, hash_technique_config
from adversarypilot.utils.timestamps import utc_now

logger = logging.getLogger(__name__)

# Maps promptfoo test/plugin types to AdversaryPilot technique IDs
TEST_MAPPING: dict[str, str] = {
    # Red-team plugins
    "promptInjection": "AP-TX-LLM-INJECT-DIRECT",
    "prompt-injection": "AP-TX-LLM-INJECT-DIRECT",
    "indirectPromptInjection": "AP-TX-LLM-INJECT-INDIRECT",
    "indirect-prompt-injection": "AP-TX-LLM-INJECT-INDIRECT",
    "jailbreak": "AP-TX-LLM-JAILBREAK-DAN",
    "jailbreak:tree": "AP-TX-LLM-TAP-TREE",
    "excessive-agency": "AP-TX-AGT-GOAL-HIJACK",
    "harmful": "AP-TX-LLM-TOXICITY-PROBE",
    "harmful:violent-crime": "AP-TX-LLM-TOXICITY-PROBE",
    "harmful:non-violent-crime": "AP-TX-LLM-TOXICITY-PROBE",
    "harmful:sex-crime": "AP-TX-LLM-TOXICITY-PROBE",
    "harmful:child-exploitation": "AP-TX-LLM-TOXICITY-PROBE",
    "harmful:self-harm": "AP-TX-LLM-TOXICITY-PROBE",
    "harmful:cybercrime": "AP-TX-LLM-TOXICITY-PROBE",
    "pii": "AP-TX-AGT-EXFIL-SIM",
    "pii:direct": "AP-TX-AGT-EXFIL-SIM",
    "pii:session": "AP-TX-AGT-EXFIL-SIM",
    "hijacking": "AP-TX-AGT-GOAL-HIJACK",
    "overreliance": "AP-TX-LLM-HALLUCINATION",
    "hallucination": "AP-TX-LLM-HALLUCINATION",
    "contracts": "AP-TX-LLM-REFUSAL-BOUNDARY",
    "politics": "AP-TX-LLM-REFUSAL-BOUNDARY",
    "imitation": "AP-TX-LLM-JAILBREAK-PERSONA",
    "shell-injection": "AP-TX-AGT-TOOL-MISUSE",
    "sql-injection": "AP-TX-AGT-TOOL-MISUSE",
    "debug-access": "AP-TX-LLM-EXTRACT-SYSPROMPT",
    "rbac": "AP-TX-AGT-GOAL-HIJACK",
    "competitors": "AP-TX-LLM-REFUSAL-BOUNDARY",
}


class PromptfooImporter(AbstractImporter):
    """Import promptfoo JSON evaluation output into AdversaryPilot result pairs."""

    @property
    def tool_name(self) -> str:
        return "promptfoo"

    def import_file(
        self, path: Path
    ) -> list[tuple[AttemptResult, EvaluationResult]]:
        """Parse a promptfoo JSON output file.

        Supports both the standard promptfoo output format:
        {
            "results": {
                "results": [
                    {
                        "prompt": {...},
                        "response": {...},
                        "success": bool,
                        "score": float,
                        ...
                    }
                ]
            }
        }

        And the flat results array format:
        {
            "results": [
                { "prompt": ..., "response": ..., ... }
            ]
        }
        """
        results: list[tuple[AttemptResult, EvaluationResult]] = []
        logger.info("Importing promptfoo output from %s", path)

        with open(path) as f:
            data = json.load(f)

        # Handle both nested and flat result formats
        raw_results = data.get("results", [])
        if isinstance(raw_results, dict):
            raw_results = raw_results.get("results", [])

        for entry in raw_results:
            pair = self._parse_result(entry)
            if pair is not None:
                results.append(pair)

        logger.info("Imported %d results from promptfoo", len(results))
        return results

    def _parse_result(
        self, entry: dict
    ) -> tuple[AttemptResult, EvaluationResult] | None:
        """Parse a single promptfoo result entry."""
        # Extract prompt
        prompt_data = entry.get("prompt", {})
        if isinstance(prompt_data, dict):
            prompt = prompt_data.get("raw", prompt_data.get("display", str(prompt_data)))
        else:
            prompt = str(prompt_data)

        # Extract response
        response_data = entry.get("response", {})
        if isinstance(response_data, dict):
            response = response_data.get("output", str(response_data))
        else:
            response = str(response_data) if response_data else None

        # Map test type to technique
        test_type = self._extract_test_type(entry)
        technique_id = self._map_test_to_technique(test_type)

        attempt_id = entry.get("id", uuid.uuid4().hex)
        timestamp = utc_now()

        attempt = AttemptResult(
            id=attempt_id,
            technique_id=technique_id,
            timestamp=timestamp,
            prompt=prompt,
            response=response,
            raw_output=entry,
            source_tool="promptfoo",
        )

        # Parse success/score
        success = entry.get("success")
        if isinstance(success, bool):
            pass
        elif success is not None:
            success = bool(success)
        else:
            success = None

        score = entry.get("score")
        if score is not None:
            score = float(score)

        # Grade results can override success
        grade_result = entry.get("gradingResult", entry.get("grading_result", {}))
        if isinstance(grade_result, dict):
            if "pass" in grade_result:
                # In promptfoo red-team: pass=true means the defense held (attack failed)
                # We invert: success=True means the attack succeeded
                success = not grade_result["pass"]
            if "score" in grade_result and score is None:
                score = float(grade_result["score"])

        # Build comparability metadata
        technique_config_hash = hash_technique_config(technique_id)
        judge_config = {"test_type": test_type, "provider": entry.get("provider", "")}
        success_criteria_hash = hash_success_criteria(JudgeType.CLASSIFIER, judge_config)

        comparability = ComparabilityMetadata(
            technique_id=technique_id,
            technique_config_hash=technique_config_hash,
            judge_type=JudgeType.CLASSIFIER,
            success_criteria_hash=success_criteria_hash,
            num_trials=1,
            random_seed_policy="unknown",
            comparability_flags=(
                ["unmapped_test"] if technique_id == "AP-TX-UNKNOWN" else []
            ),
        )

        evaluation = EvaluationResult(
            attempt_id=attempt_id,
            success=success,
            score=score,
            judge_type=JudgeType.CLASSIFIER,
            judge_details=judge_config,
            confidence=0.7 if success is not None else 0.3,
            evidence_quality=0.6,
            comparability=comparability,
        )

        return (attempt, evaluation)

    def _extract_test_type(self, entry: dict) -> str:
        """Extract the test/plugin type from a promptfoo result entry."""
        # Check various locations where promptfoo stores the test type
        test_type = entry.get("testCase", {}).get("assert", [{}])
        if isinstance(test_type, list) and test_type:
            first = test_type[0]
            if isinstance(first, dict):
                return first.get("type", first.get("metric", ""))

        # Check vars for red-team plugin info
        vars_data = entry.get("vars", entry.get("testCase", {}).get("vars", {}))
        if isinstance(vars_data, dict):
            plugin = vars_data.get("harmCategory", vars_data.get("pluginId", ""))
            if plugin:
                return plugin

        # Check metadata
        metadata = entry.get("testCase", {}).get("metadata", {})
        if isinstance(metadata, dict):
            plugin_id = metadata.get("pluginId", metadata.get("plugin", ""))
            if plugin_id:
                return plugin_id

        return entry.get("type", "")

    def _map_test_to_technique(self, test_type: str) -> str:
        """Map a promptfoo test type to an AdversaryPilot technique ID."""
        if not test_type:
            return "AP-TX-UNKNOWN"

        # Try exact match
        if test_type in TEST_MAPPING:
            return TEST_MAPPING[test_type]

        # Try prefix matching (for harmful:subcategory patterns)
        for prefix, technique_id in TEST_MAPPING.items():
            if test_type.startswith(prefix):
                return technique_id

        return "AP-TX-UNKNOWN"
