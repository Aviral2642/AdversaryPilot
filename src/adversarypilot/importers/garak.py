"""Garak importer — parses garak JSONL reports into AdversaryPilot result pairs."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path

from adversarypilot.importers.base import AbstractImporter
from adversarypilot.models.enums import JudgeType
from adversarypilot.models.results import AttemptResult, ComparabilityMetadata, EvaluationResult
from adversarypilot.utils.hashing import hash_success_criteria, hash_technique_config
from adversarypilot.utils.timestamps import utc_now

logger = logging.getLogger(__name__)

# Maps garak probe class prefixes to AdversaryPilot technique IDs
PROBE_MAPPING: dict[str, str] = {
    "probes.dan": "AP-TX-LLM-JAILBREAK-DAN",
    "probes.encoding": "AP-TX-LLM-ENCODING-BYPASS",
    "probes.promptinject": "AP-TX-LLM-INJECT-DIRECT",
    "probes.latentinjection": "AP-TX-LLM-INJECT-INDIRECT",
    "probes.leakreplay": "AP-TX-LLM-EXTRACT-TRAINING",
    "probes.realtoxicityprompts": "AP-TX-LLM-TOXICITY-PROBE",
    "probes.lmrc": "AP-TX-LLM-TOXICITY-PROBE",
    "probes.goodside": "AP-TX-LLM-JAILBREAK-PERSONA",
    "probes.grandma": "AP-TX-LLM-JAILBREAK-PERSONA",
    "probes.suffix": "AP-TX-LLM-ENCODING-BYPASS",
    "probes.tap": "AP-TX-LLM-JAILBREAK-DAN",
}


class GarakImporter(AbstractImporter):
    """Import garak JSONL report files into AdversaryPilot result pairs."""

    @property
    def tool_name(self) -> str:
        return "garak"

    def import_file(
        self, path: Path
    ) -> list[tuple[AttemptResult, EvaluationResult]]:
        """Parse a garak JSONL report file.

        Processes entries with entry_type='attempt' and status=2 (evaluated).
        """
        results: list[tuple[AttemptResult, EvaluationResult]] = []
        run_start_time: datetime | None = None
        logger.info("Importing garak report from %s", path)

        with open(path) as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                entry_type = entry.get("entry_type", "")

                # Track run start time from start_run entry
                if entry_type == "start_run" and run_start_time is None:
                    run_start_time = self._parse_timestamp(entry.get("start_time"))

                if entry_type != "attempt":
                    continue

                # Only process fully evaluated attempts (status=2)
                if entry.get("status", 0) != 2:
                    continue

                pair = self._parse_attempt(entry, line_num, run_start_time)
                if pair is not None:
                    results.append(pair)

        return results

    def _parse_attempt(
        self, entry: dict, line_num: int, run_start_time: datetime | None = None
    ) -> tuple[AttemptResult, EvaluationResult] | None:
        """Parse a single garak attempt entry into an AdversaryPilot result pair."""
        attempt_id = entry.get("uuid", uuid.uuid4().hex)
        probe_classname = entry.get("probe_classname", "")
        technique_id = self._map_probe_to_technique(probe_classname)

        # Extract prompt and response
        prompt = entry.get("prompt", "")
        outputs = entry.get("outputs", [])
        response = outputs[0] if outputs else None
        if isinstance(response, dict):
            response = response.get("text", str(response))

        # Use run_start_time if available, otherwise use current UTC time
        timestamp = run_start_time or utc_now()

        attempt = AttemptResult(
            id=attempt_id,
            technique_id=technique_id,
            timestamp=timestamp,
            prompt=prompt if isinstance(prompt, str) else str(prompt),
            response=str(response) if response else None,
            raw_output=entry,
            source_tool="garak",
            source_run_id=entry.get("run_id"),
        )

        # Parse detector results
        detector_results = entry.get("detector_results", {})
        success, score = self._parse_detector_results(detector_results)

        # Populate comparability hashes
        technique_config_hash = hash_technique_config(technique_id)
        judge_config = {"detectors": detector_results, "probe": probe_classname}
        success_criteria_hash = hash_success_criteria(JudgeType.CLASSIFIER, judge_config)

        comparability = ComparabilityMetadata(
            technique_id=technique_id,
            technique_config_hash=technique_config_hash,
            judge_type=JudgeType.CLASSIFIER,
            success_criteria_hash=success_criteria_hash,
            num_trials=1,
            random_seed_policy="unknown",
            comparability_flags=(
                ["unmapped_probe"] if technique_id == "AP-TX-UNKNOWN" else []
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

    def _map_probe_to_technique(self, probe_classname: str) -> str:
        """Map a garak probe classname to an AdversaryPilot technique ID.

        Uses prefix matching: 'probes.dan.Dan_6_0' matches 'probes.dan'.
        """
        # Try exact match first
        if probe_classname in PROBE_MAPPING:
            return PROBE_MAPPING[probe_classname]

        # Try prefix matching
        for prefix, technique_id in PROBE_MAPPING.items():
            if probe_classname.startswith(prefix):
                return technique_id

        return "AP-TX-UNKNOWN"

    def _parse_detector_results(
        self, detector_results: dict
    ) -> tuple[bool | None, float | None]:
        """Convert garak detector scores to success bool + score float.

        garak detector scores: higher values typically indicate successful attacks.
        Returns (success, score) where score is 0.0-1.0.
        """
        if not detector_results:
            return (None, None)

        scores = []
        for detector_name, score_val in detector_results.items():
            if isinstance(score_val, (int, float)):
                scores.append(float(score_val))
            elif isinstance(score_val, list):
                scores.extend(float(s) for s in score_val if isinstance(s, (int, float)))

        if not scores:
            return (None, None)

        # Average detector score; garak typically uses 0/1 for fail/pass
        avg_score = sum(scores) / len(scores)
        # In garak, a higher detector score means the attack succeeded
        # (the detector "detected" the vulnerability)
        success = avg_score > 0.5
        return (success, min(1.0, max(0.0, avg_score)))

    def _parse_timestamp(self, timestamp_str: str | None) -> datetime | None:
        """Parse garak timestamp string to datetime.

        Garak uses ISO format timestamps. Falls back to None if parsing fails.
        """
        if not timestamp_str:
            return None
        try:
            # Try parsing ISO format with timezone
            return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None
