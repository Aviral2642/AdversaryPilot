"""Campaign manager — create, update, and get recommendations for attack campaigns."""

from __future__ import annotations

import json
import logging
import random
import re
import uuid
from datetime import datetime
from pathlib import Path

from adversarypilot.models.campaign import Campaign, CampaignState
from adversarypilot.models.enums import CampaignPhase, CampaignStatus, Surface
from adversarypilot.models.plan import AttackPlan
from adversarypilot.models.results import AttemptResult, EvaluationResult
from adversarypilot.models.target import TargetProfile
from adversarypilot.planner.adaptive import AdaptivePlanner
from adversarypilot.planner.diversity import FamilyTracker
from adversarypilot.planner.posterior import PosteriorState
from adversarypilot.prioritizer.engine import PrioritizerEngine
from adversarypilot.replay.recorder import SnapshotRecorder
from adversarypilot.replay.snapshot import DecisionSnapshot
from adversarypilot.taxonomy.registry import TechniqueRegistry
from adversarypilot.utils.hashing import derive_comparable_group_key, hash_target_profile
from adversarypilot.utils.timestamps import utc_now

logger = logging.getLogger(__name__)

# Pattern for valid campaign IDs (alphanumeric, hyphens, underscores)
_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def _validate_campaign_id(campaign_id: str) -> None:
    """Validate campaign_id to prevent path traversal.

    Raises:
        ValueError: If campaign_id contains unsafe characters
    """
    if not campaign_id or not _SAFE_ID_RE.match(campaign_id):
        raise ValueError(
            f"Invalid campaign_id '{campaign_id}': must be alphanumeric, hyphens, underscores only"
        )


class CampaignManager:
    """Manages campaign lifecycle: create, ingest results, recommend next techniques."""

    def __init__(
        self,
        registry: TechniqueRegistry | None = None,
        engine: PrioritizerEngine | None = None,
        adaptive_planner: AdaptivePlanner | None = None,
        storage_dir: Path | None = None,
    ) -> None:
        self._registry = registry or TechniqueRegistry()
        if not self._registry.get_all():
            self._registry.load_catalog()
        self._engine = engine or PrioritizerEngine()
        self._adaptive_planner = adaptive_planner
        self._storage_dir = storage_dir
        self._recorder = SnapshotRecorder(storage_dir) if storage_dir else None
        self._campaigns: dict[str, Campaign] = {}
        self._step_counters: dict[str, int] = {}  # Track decision step per campaign

    def create(
        self,
        target: TargetProfile,
        name: str = "",
        auto_plan: bool = True,
        adaptive: bool = False,
        campaign_seed: int | None = None,
    ) -> Campaign:
        """Create a new campaign for the given target.

        Args:
            target: Target profile
            name: Campaign name (generated if empty)
            auto_plan: Generate initial plan immediately
            adaptive: Use adaptive planner
            campaign_seed: Random seed for deterministic planning (generated if None)

        Returns:
            Created campaign
        """
        campaign_id = uuid.uuid4().hex[:12]
        logger.info(
            "Creating campaign %s for target '%s' (type=%s, adaptive=%s)",
            campaign_id, target.name, target.target_type, adaptive,
        )

        # Hash target profile for comparability tracking
        target_hash = hash_target_profile(target)

        # Generate campaign seed for adaptive planning
        if adaptive and campaign_seed is None:
            campaign_seed = random.randint(0, 2**31 - 1)

        metadata = {
            "target_profile_hash": target_hash,
            "adaptive": adaptive,
        }
        if campaign_seed is not None:
            metadata["campaign_seed"] = campaign_seed

        # Initialize posterior state for adaptive campaigns
        posterior_state = None
        if adaptive:
            posterior_state = PosteriorState()

        campaign = Campaign(
            id=campaign_id,
            name=name or f"campaign-{campaign_id}",
            target=target,
            status=CampaignStatus.PLANNING,
            posterior_state=posterior_state,
            metadata=metadata,
        )

        if auto_plan:
            if adaptive and self._adaptive_planner is not None:
                # Use adaptive planner
                plan, updated_posterior = self._adaptive_planner.plan(
                    target,
                    self._registry,
                    posterior_state=campaign.posterior_state,
                )
                campaign.plan = plan
                campaign.posterior_state = updated_posterior
            else:
                # Use V1 planner
                plan = self._engine.plan(target, self._registry)
                campaign.plan = plan

            campaign.status = CampaignStatus.ACTIVE

        self._campaigns[campaign_id] = campaign
        self._step_counters[campaign_id] = 0
        self._save(campaign)
        return campaign

    def get(self, campaign_id: str) -> Campaign | None:
        """Retrieve a campaign by ID."""
        if campaign_id in self._campaigns:
            return self._campaigns[campaign_id]
        return self._load(campaign_id)

    def ingest_results(
        self,
        campaign_id: str,
        attempts: list[AttemptResult],
        evaluations: list[EvaluationResult],
    ) -> Campaign:
        """Add results to a campaign and update state.

        Args:
            campaign_id: Campaign identifier
            attempts: Attempt results to add
            evaluations: Evaluation results to add

        Returns:
            Updated campaign
        """
        campaign = self.get(campaign_id)
        if campaign is None:
            raise ValueError(f"Campaign {campaign_id} not found")

        logger.info(
            "Ingesting %d attempts and %d evaluations into campaign %s",
            len(attempts), len(evaluations), campaign_id,
        )

        campaign.state.attempts.extend(attempts)
        campaign.state.evaluations.extend(evaluations)

        # Track which techniques have been tried
        new_technique_ids = {a.technique_id for a in attempts}
        for tid in new_technique_ids:
            if tid not in campaign.state.techniques_tried:
                campaign.state.techniques_tried.append(tid)

        campaign.state.queries_used += len(attempts)
        campaign.state.last_updated = utc_now()

        # Populate comparable_group_key for each evaluation
        for evaluation in evaluations:
            if not evaluation.comparability.comparable_group_key:
                evaluation.comparability.comparable_group_key = derive_comparable_group_key(
                    evaluation.comparability
                )

        # Update posteriors if adaptive campaign
        is_adaptive = campaign.metadata.get("adaptive", False)
        if is_adaptive and self._adaptive_planner and campaign.posterior_state:
            campaign.posterior_state = self._adaptive_planner.update_posteriors(
                campaign.posterior_state,
                evaluations,
                self._registry,
                campaign.target,
            )

        self._save(campaign)
        return campaign

    def recommend_next(
        self,
        campaign_id: str,
        max_techniques: int = 5,
        exclude_tried: bool = False,
        repeat_penalty: float = 0.0,
        adaptive: bool | None = None,
    ) -> AttackPlan:
        """Get next recommended techniques based on campaign state.

        Args:
            campaign_id: Campaign identifier
            max_techniques: Maximum techniques to recommend
            exclude_tried: If True, exclude techniques already tried
            repeat_penalty: Penalty for repeat techniques (0.0 = no penalty)
            adaptive: Use adaptive planner (None = use campaign default)

        Returns:
            Attack plan with recommendations
        """
        campaign = self.get(campaign_id)
        if campaign is None:
            raise ValueError(f"Campaign {campaign_id} not found")

        # Determine if using adaptive planner
        is_adaptive = adaptive if adaptive is not None else campaign.metadata.get("adaptive", False)

        # Increment step counter
        step_number = self._step_counters.get(campaign_id, 0)
        self._step_counters[campaign_id] = step_number + 1

        # Check for phase transition
        if self._should_transition(campaign):
            campaign.phase = CampaignPhase.EXPLOIT
            logger.info("Campaign %s transitioned to EXPLOIT phase", campaign_id)

        if is_adaptive and self._adaptive_planner and campaign.posterior_state:
            # Use adaptive planner
            family_tracker = FamilyTracker()
            for tech_id in campaign.state.techniques_tried:
                technique = self._registry.get(tech_id)
                if technique:
                    family_tracker.mark_tried(technique)

            plan, updated_posterior = self._adaptive_planner.plan(
                campaign.target,
                self._registry,
                posterior_state=campaign.posterior_state,
                prior_results=campaign.state.evaluations,
                max_techniques=max_techniques,
                exclude_tried=exclude_tried,
                repeat_penalty=repeat_penalty,
                family_tracker=family_tracker,
                step_number=step_number,
                campaign_phase=campaign.phase,
            )

            # Update campaign posterior
            campaign.posterior_state = updated_posterior
            self._save(campaign)

            # Record snapshot if enabled
            if self._recorder:
                self._record_snapshot(
                    campaign,
                    step_number,
                    plan,
                    {},  # TODO: capture full scoring inputs
                )

            return plan
        else:
            # Use V1 planner
            return self._engine.plan(
                campaign.target,
                self._registry,
                prior_results=campaign.state.evaluations,
                max_techniques=max_techniques,
            )

    def _record_snapshot(
        self,
        campaign: Campaign,
        step_number: int,
        plan: AttackPlan,
        scoring_inputs: dict,
    ) -> None:
        """Record a decision snapshot.

        Args:
            campaign: Campaign
            step_number: Current step number
            plan: Produced plan
            scoring_inputs: Full scoring inputs (TODO: populate)
        """
        if not self._recorder or not campaign.posterior_state:
            return

        campaign_seed = campaign.metadata.get("campaign_seed", 0)
        step_seed = hash(f"{campaign_seed}:{step_number}") % (2**31)

        snapshot = DecisionSnapshot(
            snapshot_id="",  # Will be generated by recorder
            campaign_id=campaign.id,
            step_number=step_number,
            step_seed=step_seed,
            techniques_tried=campaign.state.techniques_tried.copy(),
            evaluation_count=len(campaign.state.evaluations),
            queries_used=campaign.state.queries_used,
            posterior_state=campaign.posterior_state,
            planner_config=plan.config_used,
            produced_plan_entries=[e.model_dump() for e in plan.entries],
        )

        self._recorder.record(campaign.id, step_number, snapshot)

    def _should_transition(self, campaign: Campaign) -> bool:
        """Check if campaign should transition from PROBE to EXPLOIT.

        Transitions when >= 60% of attack surfaces have been tested
        OR >= 3 recommendation rounds have occurred.
        """
        if campaign.phase != CampaignPhase.PROBE:
            return False

        step = self._step_counters.get(campaign.id, 0)
        if step >= 3:
            return True

        tested_surfaces = set()
        for tech_id in campaign.state.techniques_tried:
            technique = self._registry.get(tech_id)
            if technique:
                tested_surfaces.add(technique.surface)

        total_surfaces = len(Surface)
        return len(tested_surfaces) / max(total_surfaces, 1) >= 0.6

    def update_status(self, campaign_id: str, status: CampaignStatus) -> Campaign:
        """Update campaign status."""
        campaign = self.get(campaign_id)
        if campaign is None:
            raise ValueError(f"Campaign {campaign_id} not found")
        campaign.status = status
        self._save(campaign)
        return campaign

    def list_campaigns(self) -> list[Campaign]:
        """List all in-memory campaigns."""
        return list(self._campaigns.values())

    def _save(self, campaign: Campaign) -> None:
        """Persist campaign to disk if storage_dir is set."""
        _validate_campaign_id(campaign.id)
        self._campaigns[campaign.id] = campaign
        if self._storage_dir:
            try:
                self._storage_dir.mkdir(parents=True, exist_ok=True)
                path = self._storage_dir / f"{campaign.id}.json"
                # Write atomically via temp file to prevent corruption
                tmp_path = path.with_suffix(".json.tmp")
                tmp_path.write_text(campaign.model_dump_json(indent=2))
                tmp_path.replace(path)
                logger.debug("Campaign %s saved to %s", campaign.id, path)
            except OSError as e:
                logger.error("Failed to save campaign %s: %s", campaign.id, e)
                raise

    def _load(self, campaign_id: str) -> Campaign | None:
        """Load campaign from disk."""
        _validate_campaign_id(campaign_id)
        if not self._storage_dir:
            return None
        path = self._storage_dir / f"{campaign_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            campaign = Campaign.model_validate(data)
            self._campaigns[campaign_id] = campaign
            logger.debug("Campaign %s loaded from %s", campaign_id, path)
            return campaign
        except (json.JSONDecodeError, OSError) as e:
            logger.error("Failed to load campaign %s from %s: %s", campaign_id, path, e)
            return None
