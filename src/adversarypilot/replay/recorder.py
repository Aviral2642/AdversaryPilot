"""Snapshot recorder for saving decision points."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from adversarypilot.replay.snapshot import DecisionSnapshot


class SnapshotRecorder:
    """Records decision snapshots to disk for replay.

    Snapshots are saved at:
        <storage_dir>/<campaign_id>/snapshots/step_NNNN.json
    """

    def __init__(self, storage_dir: Path) -> None:
        """Initialize recorder.

        Args:
            storage_dir: Base directory for campaign storage
        """
        self.storage_dir = storage_dir

    def record(
        self, campaign_id: str, step_number: int, snapshot: DecisionSnapshot
    ) -> Path:
        """Record a decision snapshot.

        Args:
            campaign_id: Campaign identifier
            step_number: Current step number
            snapshot: Snapshot to record

        Returns:
            Path where snapshot was saved
        """
        snapshot_dir = self.storage_dir / campaign_id / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # Generate snapshot ID if not set
        if not snapshot.snapshot_id:
            snapshot.snapshot_id = uuid.uuid4().hex[:12]

        # Save with zero-padded step number for sorting
        path = snapshot_dir / f"step_{step_number:04d}.json"
        path.write_text(snapshot.model_dump_json(indent=2))

        return path

    def load(self, campaign_id: str, step_number: int) -> DecisionSnapshot | None:
        """Load a decision snapshot.

        Args:
            campaign_id: Campaign identifier
            step_number: Step number to load

        Returns:
            DecisionSnapshot if found, None otherwise
        """
        path = self.storage_dir / campaign_id / "snapshots" / f"step_{step_number:04d}.json"
        if not path.exists():
            return None

        data = json.loads(path.read_text())
        return DecisionSnapshot.model_validate(data)

    def list_snapshots(self, campaign_id: str) -> list[int]:
        """List all snapshot step numbers for a campaign.

        Args:
            campaign_id: Campaign identifier

        Returns:
            List of step numbers (sorted ascending)
        """
        snapshot_dir = self.storage_dir / campaign_id / "snapshots"
        if not snapshot_dir.exists():
            return []

        step_numbers = []
        for path in snapshot_dir.glob("step_*.json"):
            # Extract step number from filename
            try:
                step_num = int(path.stem.split("_")[1])
                step_numbers.append(step_num)
            except (IndexError, ValueError):
                continue

        return sorted(step_numbers)

    def delete_snapshot(self, campaign_id: str, step_number: int) -> bool:
        """Delete a snapshot.

        Args:
            campaign_id: Campaign identifier
            step_number: Step number to delete

        Returns:
            True if deleted, False if not found
        """
        path = self.storage_dir / campaign_id / "snapshots" / f"step_{step_number:04d}.json"
        if not path.exists():
            return False

        path.unlink()
        return True
