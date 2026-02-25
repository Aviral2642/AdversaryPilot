"""Tests for snapshot recorder."""

import pytest

from adversarypilot.planner.posterior import PosteriorState
from adversarypilot.replay.recorder import SnapshotRecorder
from adversarypilot.replay.snapshot import DecisionSnapshot


@pytest.fixture
def storage_dir(tmp_path):
    return tmp_path / "campaigns"


@pytest.fixture
def recorder(storage_dir):
    return SnapshotRecorder(storage_dir)


def _make_snapshot(campaign_id="camp-1", step=0, seed=42):
    return DecisionSnapshot(
        snapshot_id="",
        campaign_id=campaign_id,
        step_number=step,
        step_seed=seed,
        posterior_state=PosteriorState(),
        filtered_candidates=["t1", "t2"],
        base_scores={"t1": 0.7, "t2": 0.5},
    )


class TestSnapshotRecorder:
    def test_record_creates_file(self, recorder, storage_dir):
        snap = _make_snapshot()
        path = recorder.record("camp-1", 0, snap)
        assert path.exists()
        assert "step_0000.json" in str(path)

    def test_record_generates_snapshot_id(self, recorder):
        snap = _make_snapshot()
        recorder.record("camp-1", 0, snap)
        assert snap.snapshot_id != ""

    def test_load_roundtrip(self, recorder):
        snap = _make_snapshot()
        recorder.record("camp-1", 0, snap)
        loaded = recorder.load("camp-1", 0)
        assert loaded is not None
        assert loaded.campaign_id == "camp-1"
        assert loaded.step_number == 0
        assert loaded.base_scores["t1"] == 0.7

    def test_load_missing_returns_none(self, recorder):
        assert recorder.load("nonexistent", 99) is None

    def test_list_snapshots(self, recorder):
        for step in [0, 1, 3]:
            recorder.record("camp-1", step, _make_snapshot(step=step))
        steps = recorder.list_snapshots("camp-1")
        assert steps == [0, 1, 3]

    def test_delete_snapshot(self, recorder):
        recorder.record("camp-1", 0, _make_snapshot())
        assert recorder.delete_snapshot("camp-1", 0) is True
        assert recorder.load("camp-1", 0) is None
        assert recorder.delete_snapshot("camp-1", 0) is False
