"""Tests for meta-learning across campaigns (WS10)."""

import pytest

from adversarypilot.models.enums import AccessLevel, Goal, TargetType
from adversarypilot.models.target import TargetProfile
from adversarypilot.planner.meta_learning import CachedPosterior, PosteriorCache


@pytest.fixture
def cache(tmp_path):
    return PosteriorCache(cache_dir=tmp_path / "cache")


@pytest.fixture
def chatbot_target():
    return TargetProfile(
        name="chatbot",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK, Goal.EXFIL_SIM],
    )


@pytest.fixture
def rag_target():
    return TargetProfile(
        name="rag-system",
        target_type=TargetType.RAG,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.EXFIL_SIM, Goal.EXTRACTION],
    )


@pytest.fixture
def sample_posteriors():
    return {
        "T1": {"alpha": 5.0, "beta": 3.0, "mean": 0.625},
        "T2": {"alpha": 2.0, "beta": 8.0, "mean": 0.2},
    }


class TestCachedPosterior:
    def test_model_creation(self):
        entry = CachedPosterior(
            target_hash="abc123",
            target_type="chatbot",
            access_level="black_box",
            goals=["jailbreak"],
            campaign_id="camp-1",
            posteriors={"T1": {"alpha": 5, "beta": 3, "mean": 0.625}},
        )
        assert entry.campaign_id == "camp-1"
        assert len(entry.posteriors) == 1


class TestPosteriorCache:
    def test_empty_cache(self, cache):
        assert cache.size == 0

    def test_store_and_find_exact(self, cache, chatbot_target, sample_posteriors):
        cache.store(chatbot_target, sample_posteriors, "camp-1")
        assert cache.size == 1

        result = cache.find_nearest(chatbot_target)
        assert result is not None
        assert "T1" in result
        assert result["T1"]["mean"] == 0.625

    def test_store_multiple(self, cache, chatbot_target, rag_target, sample_posteriors):
        cache.store(chatbot_target, sample_posteriors, "camp-1")
        cache.store(rag_target, {"T3": {"alpha": 1, "beta": 1, "mean": 0.5}}, "camp-2")
        assert cache.size == 2

    def test_find_nearest_similar_target(self, cache, sample_posteriors):
        # Store for chatbot
        chatbot = TargetProfile(
            name="chatbot-1",
            target_type=TargetType.CHATBOT,
            access_level=AccessLevel.BLACK_BOX,
            goals=[Goal.JAILBREAK],
        )
        cache.store(chatbot, sample_posteriors, "camp-1")

        # Search for similar chatbot
        similar = TargetProfile(
            name="chatbot-2",
            target_type=TargetType.CHATBOT,
            access_level=AccessLevel.BLACK_BOX,
            goals=[Goal.JAILBREAK, Goal.EXFIL_SIM],
        )
        result = cache.find_nearest(similar, max_distance=0.5)
        assert result is not None

    def test_find_nearest_too_different(self, cache, chatbot_target, sample_posteriors):
        cache.store(chatbot_target, sample_posteriors, "camp-1")

        # Very different target
        different = TargetProfile(
            name="classifier",
            target_type=TargetType.CLASSIFIER,
            access_level=AccessLevel.WHITE_BOX,
            goals=[Goal.EVASION],
        )
        result = cache.find_nearest(different, max_distance=0.3)
        assert result is None

    def test_persistence(self, tmp_path, chatbot_target, sample_posteriors):
        cache_dir = tmp_path / "persist_cache"
        # Store
        cache1 = PosteriorCache(cache_dir=cache_dir)
        cache1.store(chatbot_target, sample_posteriors, "camp-1")

        # Reload
        cache2 = PosteriorCache(cache_dir=cache_dir)
        assert cache2.size == 1
        result = cache2.find_nearest(chatbot_target)
        assert result is not None

    def test_clear(self, cache, chatbot_target, sample_posteriors):
        cache.store(chatbot_target, sample_posteriors, "camp-1")
        assert cache.size == 1
        cache.clear()
        assert cache.size == 0

    def test_distance_same_type(self, cache):
        t1 = TargetProfile(
            name="a", target_type=TargetType.CHATBOT,
            access_level=AccessLevel.BLACK_BOX, goals=[Goal.JAILBREAK],
        )
        entry = CachedPosterior(
            target_hash="x", target_type="chatbot", access_level="black_box",
            goals=["jailbreak"], campaign_id="c1", posteriors={},
        )
        dist = cache._compute_distance(t1, entry)
        assert dist == 0.0  # Identical

    def test_distance_different_type(self, cache):
        t1 = TargetProfile(
            name="a", target_type=TargetType.CHATBOT,
            access_level=AccessLevel.BLACK_BOX, goals=[Goal.JAILBREAK],
        )
        entry = CachedPosterior(
            target_hash="x", target_type="classifier", access_level="black_box",
            goals=["jailbreak"], campaign_id="c1", posteriors={},
        )
        dist = cache._compute_distance(t1, entry)
        assert dist > 0.0  # Different type

    def test_distance_partial_goal_overlap(self, cache):
        t1 = TargetProfile(
            name="a", target_type=TargetType.CHATBOT,
            access_level=AccessLevel.BLACK_BOX,
            goals=[Goal.JAILBREAK, Goal.EXFIL_SIM],
        )
        entry = CachedPosterior(
            target_hash="x", target_type="chatbot", access_level="black_box",
            goals=["jailbreak"], campaign_id="c1", posteriors={},
        )
        dist = cache._compute_distance(t1, entry)
        assert 0.0 < dist < 1.0  # Partial goal overlap

    def test_empty_cache_find_returns_none(self, cache, chatbot_target):
        assert cache.find_nearest(chatbot_target) is None
