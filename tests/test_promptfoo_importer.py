"""Tests for the Promptfoo importer (WS9)."""

import json
import tempfile
from pathlib import Path

import pytest

from adversarypilot.importers.promptfoo import (
    TEST_MAPPING,
    PromptfooImporter,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "sample_promptfoo_output.json"


@pytest.fixture
def importer():
    return PromptfooImporter()


class TestPromptfooImporterBasics:
    def test_tool_name(self, importer):
        assert importer.tool_name == "promptfoo"

    def test_import_fixture(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        assert len(results) == 7

    def test_result_pair_structure(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        for attempt, evaluation in results:
            assert attempt.technique_id is not None
            assert attempt.source_tool == "promptfoo"
            assert evaluation.attempt_id == attempt.id


class TestPromptMapping:
    def test_prompt_injection_mapped(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        pf001 = next(a for a, _ in results if a.id == "pf-001")
        assert pf001.technique_id == "AP-TX-LLM-INJECT-DIRECT"

    def test_jailbreak_mapped(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        pf002 = next(a for a, _ in results if a.id == "pf-002")
        assert pf002.technique_id == "AP-TX-LLM-JAILBREAK-DAN"

    def test_pii_mapped(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        pf003 = next(a for a, _ in results if a.id == "pf-003")
        assert pf003.technique_id == "AP-TX-AGT-EXFIL-SIM"

    def test_harmful_prefix_mapped(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        pf004 = next(a for a, _ in results if a.id == "pf-004")
        assert pf004.technique_id == "AP-TX-LLM-TOXICITY-PROBE"

    def test_shell_injection_mapped(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        pf005 = next(a for a, _ in results if a.id == "pf-005")
        assert pf005.technique_id == "AP-TX-AGT-TOOL-MISUSE"

    def test_debug_access_mapped(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        pf006 = next(a for a, _ in results if a.id == "pf-006")
        assert pf006.technique_id == "AP-TX-LLM-EXTRACT-SYSPROMPT"

    def test_unknown_mapped(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        pf007 = next(a for a, _ in results if a.id == "pf-007")
        assert pf007.technique_id == "AP-TX-UNKNOWN"


class TestGradingResults:
    def test_grading_pass_false_means_attack_success(self, importer):
        """In promptfoo red-team: pass=false means defense failed = attack succeeded."""
        results = importer.import_file(FIXTURE_PATH)
        _, eval_002 = next((a, e) for a, e in results if a.id == "pf-002")
        assert eval_002.success is True  # pass=false → attack succeeded

    def test_grading_pass_true_means_attack_failed(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        _, eval_004 = next((a, e) for a, e in results if a.id == "pf-004")
        assert eval_004.success is False  # pass=true → defense held

    def test_score_from_grading(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        _, eval_002 = next((a, e) for a, e in results if a.id == "pf-002")
        assert eval_002.score == 0.85


class TestComparability:
    def test_comparability_populated(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        _, evaluation = results[0]
        assert evaluation.comparability.technique_id is not None
        assert evaluation.comparability.technique_config_hash != ""

    def test_unmapped_flag(self, importer):
        results = importer.import_file(FIXTURE_PATH)
        _, eval_007 = next((a, e) for a, e in results if a.id == "pf-007")
        assert "unmapped_test" in eval_007.comparability.comparability_flags


class TestFlatFormat:
    def test_flat_results_array(self, importer, tmp_path):
        """Test with flat results array (not nested under results.results)."""
        flat_data = {
            "results": [
                {
                    "id": "flat-1",
                    "prompt": "test prompt",
                    "response": {"output": "test response"},
                    "gradingResult": {"pass": False, "score": 0.8},
                    "testCase": {"assert": [{"type": "jailbreak"}]},
                }
            ]
        }
        p = tmp_path / "flat.json"
        p.write_text(json.dumps(flat_data))
        results = importer.import_file(p)
        assert len(results) == 1

    def test_empty_results(self, importer, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text(json.dumps({"results": {"results": []}}))
        results = importer.import_file(p)
        assert len(results) == 0


class TestTestMapping:
    def test_mapping_has_entries(self):
        assert len(TEST_MAPPING) > 10

    def test_all_mapped_ids_valid_format(self):
        for technique_id in TEST_MAPPING.values():
            assert technique_id.startswith("AP-TX-")
