"""Tests for enterprise hardening fixes."""

from __future__ import annotations

import pytest

from adversarypilot.campaign.manager import _validate_campaign_id
from adversarypilot.planner.posterior import PosteriorState, TechniquePosterior


class TestCampaignIdValidation:
    """Tests for path traversal prevention in campaign IDs."""

    def test_valid_alphanumeric(self):
        _validate_campaign_id("abc123")

    def test_valid_with_hyphens(self):
        _validate_campaign_id("my-campaign-001")

    def test_valid_with_underscores(self):
        _validate_campaign_id("campaign_test_42")

    def test_valid_hex_id(self):
        _validate_campaign_id("a1b2c3d4e5f6")

    def test_rejects_path_traversal(self):
        with pytest.raises(ValueError, match="Invalid campaign_id"):
            _validate_campaign_id("../../etc/passwd")

    def test_rejects_slashes(self):
        with pytest.raises(ValueError, match="Invalid campaign_id"):
            _validate_campaign_id("foo/bar")

    def test_rejects_backslashes(self):
        with pytest.raises(ValueError, match="Invalid campaign_id"):
            _validate_campaign_id("foo\\bar")

    def test_rejects_dots_only(self):
        with pytest.raises(ValueError, match="Invalid campaign_id"):
            _validate_campaign_id("..")

    def test_rejects_empty_string(self):
        with pytest.raises(ValueError, match="Invalid campaign_id"):
            _validate_campaign_id("")

    def test_rejects_spaces(self):
        with pytest.raises(ValueError, match="Invalid campaign_id"):
            _validate_campaign_id("foo bar")

    def test_rejects_special_chars(self):
        with pytest.raises(ValueError, match="Invalid campaign_id"):
            _validate_campaign_id("foo;rm -rf /")


class TestPosteriorValidation:
    """Tests for posterior state input validation."""

    def test_reward_bounds_valid(self):
        p = TechniquePosterior(technique_id="test")
        p.update(0.0)
        p.update(0.5)
        p.update(1.0)
        assert p.observations == 3

    def test_reward_too_high(self):
        p = TechniquePosterior(technique_id="test")
        with pytest.raises(ValueError, match="Reward must be in"):
            p.update(1.1)

    def test_reward_negative(self):
        p = TechniquePosterior(technique_id="test")
        with pytest.raises(ValueError, match="Reward must be in"):
            p.update(-0.1)

    def test_posterior_mean(self):
        p = TechniquePosterior(technique_id="test", alpha=3.0, beta=1.0)
        assert p.mean == pytest.approx(0.75)

    def test_posterior_state_get_or_init(self):
        state = PosteriorState()
        p = state.get_or_init("tech-1", 0.7)
        assert p.technique_id == "tech-1"
        # With default prior_strength=8.0: alpha = 1 + 8*0.7 = 6.6
        assert p.alpha == pytest.approx(6.6)
        assert p.beta == pytest.approx(3.4)

    def test_posterior_state_returns_existing(self):
        state = PosteriorState()
        p1 = state.get_or_init("tech-1", 0.7)
        p1.update(1.0)
        p2 = state.get_or_init("tech-1", 0.7)
        assert p2.observations == 1  # Same object, not reinitialized


class TestExpandedCatalog:
    """Tests for the expanded technique catalog."""

    def test_catalog_has_research_techniques(self, registry):
        """Verify key research-backed techniques are present."""
        assert registry.get("AP-TX-LLM-GCG-SUFFIX") is not None
        assert registry.get("AP-TX-LLM-PAIR-ITERATIVE") is not None
        assert registry.get("AP-TX-LLM-TAP-TREE") is not None
        assert registry.get("AP-TX-LLM-AUTODAN") is not None
        assert registry.get("AP-TX-LLM-MANYSHOT") is not None
        assert registry.get("AP-TX-LLM-CRESCENDO") is not None
        assert registry.get("AP-TX-LLM-SKELETON-KEY") is not None
        assert registry.get("AP-TX-LLM-CIPHER-JAILBREAK") is not None

    def test_catalog_has_multimodal_techniques(self, registry):
        assert registry.get("AP-TX-LLM-FIGSTEP-VISUAL") is not None
        assert registry.get("AP-TX-LLM-MULTIMODAL-COMPOSE") is not None

    def test_catalog_has_agent_techniques(self, registry):
        assert registry.get("AP-TX-AGT-MCP-EXFIL") is not None
        assert registry.get("AP-TX-AGT-PRIVILEGE-ESCALATION") is not None
        assert registry.get("AP-TX-AGT-RAG-POISON") is not None
        assert registry.get("AP-TX-AGT-ADAPTIVE-IPI") is not None
        assert registry.get("AP-TX-AGT-TOOL-CHAIN-HIJACK") is not None

    def test_catalog_has_aml_extensions(self, registry):
        assert registry.get("AP-TX-AML-EXTRACT-LLM-DISTILL") is not None
        assert registry.get("AP-TX-AML-EMBEDDING-INVERSION") is not None
        assert registry.get("AP-TX-AML-SUPPLY-CHAIN") is not None
        assert registry.get("AP-TX-AML-RETRIEVAL-POISON") is not None
        assert registry.get("AP-TX-AML-POISON-CLEAN-LABEL") is not None

    def test_all_techniques_have_atlas_or_other_refs(self, registry):
        """Every technique should have at least atlas_refs or other_refs."""
        # Some techniques legitimately have no refs (like hallucination probe)
        no_refs = [
            t for t in registry.get_all()
            if not t.atlas_refs and not t.other_refs
        ]
        # Allow a few without refs but not too many
        assert len(no_refs) <= 5, f"Too many techniques without references: {[t.id for t in no_refs]}"

    def test_gcg_requires_white_box(self, registry):
        gcg = registry.get("AP-TX-LLM-GCG-SUFFIX")
        assert gcg.access_required.value == "white_box"

    def test_pair_is_black_box(self, registry):
        pair = registry.get("AP-TX-LLM-PAIR-ITERATIVE")
        assert pair.access_required.value == "black_box"

    def test_crescendo_is_covert(self, registry):
        crescendo = registry.get("AP-TX-LLM-CRESCENDO")
        assert crescendo.stealth_profile.value == "covert"
