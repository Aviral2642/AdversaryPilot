"""Decision replayer for reproducing planning decisions."""

from __future__ import annotations

from adversarypilot.models.enums import CampaignPhase
from adversarypilot.models.plan import AttackPlan
from adversarypilot.models.target import TargetProfile
from adversarypilot.planner.adaptive import AdaptivePlanner
from adversarypilot.planner.diversity import FamilyTracker
from adversarypilot.replay.snapshot import DecisionSnapshot
from adversarypilot.taxonomy.registry import TechniqueRegistry


class DecisionReplayer:
    """Replays planning decisions from snapshots.

    Reproduces rankings by restoring frozen state and re-running
    the planner with the same seed.
    """

    def __init__(
        self,
        registry: TechniqueRegistry,
        planner: AdaptivePlanner | None = None,
    ) -> None:
        """Initialize replayer.

        Args:
            registry: Technique registry
            planner: Adaptive planner (creates default if None)
        """
        self.registry = registry
        self.planner = planner

    def replay(
        self, snapshot: DecisionSnapshot, target: TargetProfile
    ) -> AttackPlan:
        """Replay a planning decision from snapshot.

        Restores frozen state and re-runs planner with same seed.

        Args:
            snapshot: Decision snapshot to replay
            target: Target profile (must match snapshot's campaign target)

        Returns:
            Reproduced AttackPlan
        """
        # Create planner with frozen config
        if self.planner is None:
            # Use snapshot's planner config and campaign seed
            campaign_seed = snapshot.planner_config.get("campaign_seed")
            planner = AdaptivePlanner(campaign_seed=campaign_seed)
        else:
            planner = self.planner

        # Restore frozen state
        posterior_state = snapshot.posterior_state
        step_number = snapshot.step_number

        # Extract planner params from frozen config
        config = snapshot.planner_config
        max_techniques = len(snapshot.produced_plan_entries)
        exclude_tried = config.get("exclude_tried", False)
        repeat_penalty = config.get("repeat_penalty", 0.0)

        # Restore family tracker from tried techniques
        family_tracker = FamilyTracker()
        for tech_id in snapshot.techniques_tried:
            technique = self.registry.get(tech_id)
            if technique:
                family_tracker.mark_tried(technique)

        # Restore campaign phase
        phase_str = config.get("campaign_phase", "probe")
        campaign_phase = CampaignPhase(phase_str)

        # Replay decision
        plan, _ = planner.plan(
            target=target,
            registry=self.registry,
            posterior_state=posterior_state,
            prior_results=[],
            max_techniques=max_techniques,
            exclude_tried=exclude_tried,
            repeat_penalty=repeat_penalty,
            family_tracker=family_tracker,
            step_number=step_number,
            campaign_phase=campaign_phase,
        )

        return plan

    def verify(
        self,
        snapshot: DecisionSnapshot,
        target: TargetProfile,
        tolerance: float = 1e-6,
    ) -> tuple[bool, list[str]]:
        """Verify that replay matches original decision.

        Args:
            snapshot: Decision snapshot
            target: Target profile
            tolerance: Floating-point tolerance for score comparison

        Returns:
            Tuple of (matches: bool, divergences: list[str])
        """
        replayed_plan = self.replay(snapshot, target)

        divergences: list[str] = []

        # Check plan length
        original_len = len(snapshot.produced_plan_entries)
        replayed_len = len(replayed_plan.entries)
        if original_len != replayed_len:
            divergences.append(
                f"Plan length mismatch: original={original_len}, replayed={replayed_len}"
            )

        # Check technique rankings
        for i, (original_entry, replayed_entry) in enumerate(
            zip(snapshot.produced_plan_entries, replayed_plan.entries)
        ):
            orig_tech_id = original_entry["technique_id"]
            repl_tech_id = replayed_entry.technique_id

            if orig_tech_id != repl_tech_id:
                divergences.append(
                    f"Rank #{i+1}: technique_id mismatch "
                    f"(original={orig_tech_id}, replayed={repl_tech_id})"
                )

            # Check utility scores if available
            orig_utility = original_entry.get("score", {}).get("utility")
            repl_utility = replayed_entry.score.utility

            if orig_utility is not None and repl_utility is not None:
                if abs(orig_utility - repl_utility) > tolerance:
                    divergences.append(
                        f"Rank #{i+1} ({orig_tech_id}): utility mismatch "
                        f"(original={orig_utility:.6f}, replayed={repl_utility:.6f})"
                    )

        matches = len(divergences) == 0
        return matches, divergences
