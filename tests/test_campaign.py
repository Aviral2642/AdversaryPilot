"""Tests for campaign manager."""

from pathlib import Path

from adversarypilot.campaign.manager import CampaignManager
from adversarypilot.models.enums import CampaignStatus


def test_create_campaign(chatbot_target, tmp_path):
    manager = CampaignManager(storage_dir=tmp_path)
    campaign = manager.create(chatbot_target, name="test-campaign")
    assert campaign.id != ""
    assert campaign.name == "test-campaign"
    assert campaign.status == CampaignStatus.ACTIVE
    assert campaign.plan is not None
    assert len(campaign.plan.entries) > 0


def test_create_campaign_no_auto_plan(chatbot_target, tmp_path):
    manager = CampaignManager(storage_dir=tmp_path)
    campaign = manager.create(chatbot_target, auto_plan=False)
    assert campaign.status == CampaignStatus.PLANNING
    assert campaign.plan is None


def test_get_campaign(chatbot_target, tmp_path):
    manager = CampaignManager(storage_dir=tmp_path)
    created = manager.create(chatbot_target)
    retrieved = manager.get(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id


def test_get_missing_campaign(tmp_path):
    manager = CampaignManager(storage_dir=tmp_path)
    assert manager.get("nonexistent") is None


def test_ingest_results(chatbot_target, sample_results, tmp_path):
    manager = CampaignManager(storage_dir=tmp_path)
    campaign = manager.create(chatbot_target)

    attempts = [a for a, _ in sample_results]
    evaluations = [e for _, e in sample_results]

    updated = manager.ingest_results(campaign.id, attempts, evaluations)
    assert updated.total_attempts == 5
    assert updated.successful_attempts == 3  # indices 0, 2, 4
    assert len(updated.state.techniques_tried) == 1


def test_recommend_next(chatbot_target, sample_results, tmp_path):
    manager = CampaignManager(storage_dir=tmp_path)
    campaign = manager.create(chatbot_target)

    attempts = [a for a, _ in sample_results]
    evaluations = [e for _, e in sample_results]
    manager.ingest_results(campaign.id, attempts, evaluations)

    next_plan = manager.recommend_next(campaign.id, max_techniques=3)
    assert len(next_plan.entries) <= 3


def test_update_status(chatbot_target, tmp_path):
    manager = CampaignManager(storage_dir=tmp_path)
    campaign = manager.create(chatbot_target)
    updated = manager.update_status(campaign.id, CampaignStatus.PAUSED)
    assert updated.status == CampaignStatus.PAUSED


def test_campaign_persistence(chatbot_target, tmp_path):
    manager1 = CampaignManager(storage_dir=tmp_path)
    campaign = manager1.create(chatbot_target)
    campaign_id = campaign.id

    # Load from a fresh manager
    manager2 = CampaignManager(storage_dir=tmp_path)
    loaded = manager2.get(campaign_id)
    assert loaded is not None
    assert loaded.id == campaign_id
    assert loaded.target.name == chatbot_target.name
