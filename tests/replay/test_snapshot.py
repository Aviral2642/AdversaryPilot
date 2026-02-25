"""Tests for decision snapshots."""

from adversarypilot.planner.posterior import PosteriorState
from adversarypilot.replay.snapshot import DecisionSnapshot


def test_snapshot_creation():
    """Test basic snapshot creation."""
    posterior = PosteriorState()
    posterior.posteriors["test_tech"] = posterior.get_or_init("test_tech", 0.5)

    snapshot = DecisionSnapshot(
        snapshot_id="snap-001",
        campaign_id="camp-001",
        step_number=1,
        step_seed=12345,
        posterior_state=posterior,
        techniques_tried=["test_tech"],
    )

    assert snapshot.snapshot_id == "snap-001"
    assert snapshot.campaign_id == "camp-001"
    assert snapshot.step_number == 1
    assert len(snapshot.techniques_tried) == 1


def test_snapshot_serialization():
    """Test snapshot serialization/deserialization."""
    posterior = PosteriorState()
    posterior.posteriors["test_tech"] = posterior.get_or_init("test_tech", 0.5)

    snapshot = DecisionSnapshot(
        snapshot_id="snap-001",
        campaign_id="camp-001",
        step_number=1,
        step_seed=12345,
        posterior_state=posterior,
        techniques_tried=["test_tech"],
        base_scores={"test_tech": 0.75},
        thompson_samples={"test_tech": 0.82},
    )

    # Serialize to dict
    data = snapshot.to_dict()
    assert isinstance(data, dict)
    assert data["snapshot_id"] == "snap-001"

    # Deserialize from dict
    restored = DecisionSnapshot.from_dict(data)
    assert restored.snapshot_id == snapshot.snapshot_id
    assert restored.step_number == snapshot.step_number
    assert restored.posterior_state.posteriors.keys() == snapshot.posterior_state.posteriors.keys()


def test_snapshot_timestamp_is_utc_aware():
    """Test that snapshot timestamps are UTC-aware."""
    snapshot = DecisionSnapshot(
        snapshot_id="snap-001",
        campaign_id="camp-001",
        step_number=1,
        step_seed=12345,
        posterior_state=PosteriorState(),
    )

    assert snapshot.timestamp.tzinfo is not None


def test_snapshot_stores_full_scoring_inputs():
    """Test that snapshot stores full scoring inputs."""
    snapshot = DecisionSnapshot(
        snapshot_id="snap-001",
        campaign_id="camp-001",
        step_number=1,
        step_seed=12345,
        posterior_state=PosteriorState(),
        filtered_candidates=["tech1", "tech2"],
        filter_rejections={"tech3": "incompatible"},
        base_scores={"tech1": 0.7, "tech2": 0.6},
        thompson_samples={"tech1": 0.75, "tech2": 0.55},
        utility_components={
            "tech1": {"impact": 0.8, "cost": 0.3, "utility": 0.65},
            "tech2": {"impact": 0.6, "cost": 0.4, "utility": 0.45},
        },
    )

    assert len(snapshot.filtered_candidates) == 2
    assert "tech3" in snapshot.filter_rejections
    assert snapshot.base_scores["tech1"] == 0.7
    assert snapshot.thompson_samples["tech2"] == 0.55
    assert snapshot.utility_components["tech1"]["utility"] == 0.65
