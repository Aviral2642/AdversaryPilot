"""Tests for the garak importer."""

from pathlib import Path

from adversarypilot.importers.garak import PROBE_MAPPING, GarakImporter


def test_import_file(garak_report_path):
    importer = GarakImporter()
    results = importer.import_file(garak_report_path)
    # Should import 5 evaluated attempts (status=2), skip 1 unevaluated (status=1)
    assert len(results) == 5


def test_probe_mapping(garak_report_path):
    importer = GarakImporter()
    results = importer.import_file(garak_report_path)

    technique_ids = [a.technique_id for a, _ in results]
    assert "AP-TX-LLM-JAILBREAK-DAN" in technique_ids
    assert "AP-TX-LLM-ENCODING-BYPASS" in technique_ids
    assert "AP-TX-LLM-EXTRACT-TRAINING" in technique_ids


def test_source_tool_set(garak_report_path):
    importer = GarakImporter()
    results = importer.import_file(garak_report_path)
    for attempt, _ in results:
        assert attempt.source_tool == "garak"


def test_detector_results_parsed(garak_report_path):
    importer = GarakImporter()
    results = importer.import_file(garak_report_path)
    for _, evaluation in results:
        assert evaluation.score is not None or evaluation.success is None


def test_successful_attack_detected(garak_report_path):
    importer = GarakImporter()
    results = importer.import_file(garak_report_path)

    # att-002 has toxicity=0.8 (>0.5) so should be marked successful
    att_002 = next((a, e) for a, e in results if a.id == "att-002")
    assert att_002[1].success is True

    # att-006 has leakage=0.9 (>0.5) so should be marked successful
    att_006 = next((a, e) for a, e in results if a.id == "att-006")
    assert att_006[1].success is True


def test_failed_attack_detected(garak_report_path):
    importer = GarakImporter()
    results = importer.import_file(garak_report_path)

    # att-001 has toxicity=0.1 (<0.5) so should be marked failed
    att_001 = next((a, e) for a, e in results if a.id == "att-001")
    assert att_001[1].success is False


def test_skips_unevaluated_attempts(garak_report_path):
    importer = GarakImporter()
    results = importer.import_file(garak_report_path)
    # att-004 has status=1 and should be skipped
    attempt_ids = [a.id for a, _ in results]
    assert "att-004" not in attempt_ids


def test_unmapped_probe():
    importer = GarakImporter()
    technique_id = importer._map_probe_to_technique("probes.unknown.SomeThing")
    assert technique_id == "AP-TX-UNKNOWN"


def test_probe_prefix_matching():
    importer = GarakImporter()
    assert importer._map_probe_to_technique("probes.dan.Dan_6_0") == "AP-TX-LLM-JAILBREAK-DAN"
    assert importer._map_probe_to_technique("probes.dan.Dan_11_0") == "AP-TX-LLM-JAILBREAK-DAN"
    assert importer._map_probe_to_technique("probes.encoding.InjectBase64") == "AP-TX-LLM-ENCODING-BYPASS"


def test_tool_name():
    importer = GarakImporter()
    assert importer.tool_name == "garak"


def test_comparability_flags_for_unmapped():
    importer = GarakImporter()
    # Create a minimal JSONL with an unmapped probe
    import tempfile
    import json

    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        entry = {
            "entry_type": "attempt",
            "uuid": "test-unmapped",
            "status": 2,
            "prompt": "test",
            "probe_classname": "probes.completely_unknown.Test",
            "outputs": ["response"],
            "detector_results": {"test": 0.5},
        }
        f.write(json.dumps(entry) + "\n")
        f.flush()

        results = importer.import_file(Path(f.name))
        assert len(results) == 1
        _, evaluation = results[0]
        assert "unmapped_probe" in evaluation.comparability.comparability_flags
