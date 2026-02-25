from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from adversarypilot.campaign.manager import CampaignManager
from adversarypilot.cli.main import app
from adversarypilot.planner.adaptive import AdaptivePlanner


runner = CliRunner()
FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _extract_campaign_id(output: str) -> str:
    """Extract campaign ID from CLI output."""
    match = re.search(r"Campaign created:\s+([a-zA-Z0-9_-]+)", output)
    assert match, f"Could not find campaign id in output:\n{output}"
    return match.group(1)


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "adversarypilot" in result.stdout


def test_cli_validate_success():
    target_path = FIXTURES_DIR / "sample_target_chatbot.yaml"
    result = runner.invoke(app, ["validate", str(target_path)])
    assert result.exit_code == 0
    assert "Valid target profile" in result.stdout


def test_cli_validate_failure(tmp_path: Path):
    bad_target = tmp_path / "bad_target.yaml"
    bad_target.write_text("name: Missing required fields\n")

    result = runner.invoke(app, ["validate", str(bad_target)])
    assert result.exit_code == 1
    assert "Validation failed" in result.stdout


def test_cli_plan_stdout_and_file(tmp_path: Path):
    target_path = FIXTURES_DIR / "sample_target_chatbot.yaml"

    # Plan to stdout
    result = runner.invoke(app, ["plan", str(target_path), "--max", "3"])
    assert result.exit_code == 0
    assert "Attack Plan for: Test Chatbot" in result.stdout
    assert "Techniques:" in result.stdout

    # Plan to JSON file
    out_file = tmp_path / "plan.json"
    result = runner.invoke(
        app,
        ["plan", str(target_path), "--max", "2", "--output", str(out_file)],
    )
    assert result.exit_code == 0
    assert out_file.exists()

    data = json.loads(out_file.read_text())
    assert "entries" in data
    assert len(data["entries"]) <= 2


def test_cli_techniques_list_filters():
    result = runner.invoke(
        app,
        ["techniques", "list", "--domain", "llm", "--goal", "jailbreak"],
    )
    assert result.exit_code == 0
    assert "Techniques (" in result.stdout
    # Should list at least the DAN jailbreak technique
    assert "AP-TX-LLM-JAILBREAK-DAN" in result.stdout


def test_cli_import_garak(garak_report_path: Path, tmp_path: Path):
    out_file = tmp_path / "garak_import.json"
    result = runner.invoke(
        app,
        ["import", "garak", str(garak_report_path), "--output", str(out_file)],
    )
    assert result.exit_code == 0
    assert "Imported" in result.stdout
    assert "result pairs from garak" in result.stdout
    assert out_file.exists()

    data = json.loads(out_file.read_text())
    assert isinstance(data, list)
    assert len(data) > 0
    assert "attempt" in data[0]
    assert "evaluation" in data[0]


def test_cli_chains_stdout_and_file(tmp_path: Path):
    target_path = FIXTURES_DIR / "sample_target_chatbot.yaml"

    # Chains to stdout
    result = runner.invoke(
        app,
        ["chains", str(target_path), "--max-length", "3", "--max-chains", "2"],
    )
    assert result.exit_code == 0
    assert "Attack Chains for: Test Chatbot" in result.stdout

    # Chains to file (JSON)
    out_file = tmp_path / "chains.json"
    result = runner.invoke(
        app,
        [
            "chains",
            str(target_path),
            "--max-length",
            "3",
            "--max-chains",
            "2",
            "--output",
            str(out_file),
        ],
    )
    assert result.exit_code == 0
    assert out_file.exists()

    data = json.loads(out_file.read_text())
    assert isinstance(data, list)


def test_cli_campaign_new_and_next_chatbot(tmp_path: Path):
    target_path = FIXTURES_DIR / "sample_target_chatbot.yaml"
    storage_dir = tmp_path / "campaigns"

    # Create campaign via CLI
    result = runner.invoke(
        app,
        [
            "campaign",
            "new",
            str(target_path),
            "--name",
            "cli-campaign",
            "--dir",
            str(storage_dir),
        ],
    )
    assert result.exit_code == 0
    campaign_id = _extract_campaign_id(result.stdout)

    # Get next recommendations via CLI
    result = runner.invoke(
        app,
        [
            "campaign",
            "next",
            campaign_id,
            "--dir",
            str(storage_dir),
            "--max",
            "3",
        ],
    )
    assert result.exit_code == 0
    assert "Next Recommended Techniques:" in result.stdout


def test_cli_campaign_new_adaptive_and_next(tmp_path: Path):
    target_path = FIXTURES_DIR / "sample_target_chatbot.yaml"
    storage_dir = tmp_path / "campaigns"

    # Create adaptive campaign via CLI with deterministic seed
    result = runner.invoke(
        app,
        [
            "campaign",
            "new",
            str(target_path),
            "--name",
            "adaptive-cli-campaign",
            "--dir",
            str(storage_dir),
            "--adaptive",
            "--seed",
            "42",
        ],
    )
    assert result.exit_code == 0
    campaign_id = _extract_campaign_id(result.stdout)
    assert "Mode: Adaptive (seed=42)" in result.stdout

    # Get adaptive next recommendations via CLI
    result = runner.invoke(
        app,
        [
            "campaign",
            "next",
            campaign_id,
            "--dir",
            str(storage_dir),
            "--max",
            "3",
            "--adaptive",
        ],
    )
    assert result.exit_code == 0
    assert "Next Recommended Techniques:" in result.stdout


def test_cli_report_generates_markdown_and_html(tmp_path: Path, chatbot_target, sample_results):
    storage_dir = tmp_path / "campaigns"

    # Set up campaign and ingest results via library API
    manager = CampaignManager(storage_dir=storage_dir)
    campaign = manager.create(chatbot_target, name="report-campaign")

    attempts = [a for a, _ in sample_results]
    evaluations = [e for _, e in sample_results]
    manager.ingest_results(campaign.id, attempts, evaluations)

    # Markdown report to stdout
    result = runner.invoke(
        app,
        [
            "report",
            campaign.id,
            "--dir",
            str(storage_dir),
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    # Markdown renderer should include defender report header and target name
    assert "Defender Report: Test Chatbot" in result.stdout

    # HTML report to file
    html_out = tmp_path / "report.html"
    result = runner.invoke(
        app,
        [
            "report",
            campaign.id,
            "--dir",
            str(storage_dir),
            "--format",
            "html",
            "--output",
            str(html_out),
        ],
    )
    assert result.exit_code == 0
    assert html_out.exists()
    contents = html_out.read_text()
    assert "<html" in contents.lower()


def test_cli_report_missing_campaign(tmp_path: Path):
    storage_dir = tmp_path / "campaigns"

    result = runner.invoke(
        app,
        [
            "report",
            "nonexistent-campaign",
            "--dir",
            str(storage_dir),
        ],
    )
    # Typer should exit with non-zero for missing campaigns
    assert result.exit_code != 0
    assert "Campaign nonexistent-campaign not found" in result.stdout


def test_cli_replay_latest_snapshot(tmp_path: Path, chatbot_target):
    storage_dir = tmp_path / "campaigns"

    # Create adaptive campaign and generate at least one snapshot via library API
    planner = AdaptivePlanner(campaign_seed=42)
    manager = CampaignManager(storage_dir=storage_dir, adaptive_planner=planner)
    campaign = manager.create(chatbot_target, name="replay-campaign", adaptive=True, campaign_seed=42)

    # Produce a recommendation to create a snapshot
    manager.recommend_next(campaign.id, max_techniques=3, adaptive=True)

    # Replay latest snapshot via CLI
    result = runner.invoke(
        app,
        [
            "replay",
            campaign.id,
            "--dir",
            str(storage_dir),
        ],
    )
    assert result.exit_code == 0
    assert "Replaying Decision:" in result.stdout


def test_cli_replay_verify(tmp_path: Path, chatbot_target):
    storage_dir = tmp_path / "campaigns"

    planner = AdaptivePlanner(campaign_seed=42)
    manager = CampaignManager(storage_dir=storage_dir, adaptive_planner=planner)
    campaign = manager.create(chatbot_target, name="replay-verify-campaign", adaptive=True, campaign_seed=42)

    manager.recommend_next(campaign.id, max_techniques=3, adaptive=True)

    result = runner.invoke(
        app,
        [
            "replay",
            campaign.id,
            "--dir",
            str(storage_dir),
            "--verify",
        ],
    )
    assert result.exit_code == 0
    assert "Replaying Decision:" in result.stdout


def test_cli_replay_missing_campaign(tmp_path: Path):
    storage_dir = tmp_path / "campaigns"

    result = runner.invoke(
        app,
        [
            "replay",
            "nonexistent-campaign",
            "--dir",
            str(storage_dir),
        ],
    )
    assert result.exit_code != 0
    assert "Campaign nonexistent-campaign not found" in result.stdout

