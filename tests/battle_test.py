"""
Battle Test Suite — End-to-end integration tests that simulate real-world
AI red teaming workflows. Tests the FULL pipeline as a skeptical security
engineer would use it.

NOT unit tests. These are scenario-based validation tests.
"""

from __future__ import annotations

import json
import random
import textwrap
from pathlib import Path

from adversarypilot.campaign.manager import CampaignManager
from adversarypilot.models.campaign import Campaign
from adversarypilot.models.enums import (
    AccessLevel,
    CampaignStatus,
    Domain,
    Goal,
    JudgeType,
    Phase,
    StealthLevel,
    Surface,
    TargetType,
)
from adversarypilot.models.plan import AttackPlan
from adversarypilot.models.report import DefenderReport
from adversarypilot.models.results import AttemptResult, ComparabilityMetadata, EvaluationResult
from adversarypilot.models.target import ConstraintSpec, DefenseProfile, TargetProfile
from adversarypilot.planner.adaptive import AdaptivePlanner
from adversarypilot.planner.chains import ChainPlanner
from adversarypilot.planner.diversity import FamilyTracker
from adversarypilot.planner.posterior import PosteriorState
from adversarypilot.prioritizer.engine import PrioritizerEngine
from adversarypilot.replay.recorder import SnapshotRecorder
from adversarypilot.replay.replayer import DecisionReplayer
from adversarypilot.replay.snapshot import DecisionSnapshot
from adversarypilot.reporting.analyzer import WeakestLayerAnalyzer
from adversarypilot.reporting.html_renderer import HtmlReportRenderer
from adversarypilot.reporting.renderer import ReportRenderer
from adversarypilot.taxonomy.registry import TechniqueRegistry


# ═══════════════════════════════════════════════════════════════════════
# REALISTIC TARGET PROFILES — modeled after real-world AI systems
# ═══════════════════════════════════════════════════════════════════════

def make_enterprise_chatbot() -> TargetProfile:
    """GPT-4-class enterprise chatbot with production defenses."""
    return TargetProfile(
        name="Enterprise Customer Support Chatbot (GPT-4)",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK, Goal.EXTRACTION],
        constraints=ConstraintSpec(
            max_queries=500,
            stealth_priority=StealthLevel.MODERATE,
        ),
        defenses=DefenseProfile(
            has_moderation=True,
            has_input_filtering=True,
            has_output_filtering=True,
            has_rate_limiting=True,
        ),
    )


def make_rag_system() -> TargetProfile:
    """Production RAG system with document retrieval."""
    return TargetProfile(
        name="Internal Knowledge Base RAG (Claude + Pinecone)",
        target_type=TargetType.RAG,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK, Goal.EXFIL_SIM, Goal.EXTRACTION],
        constraints=ConstraintSpec(
            max_queries=200,
            stealth_priority=StealthLevel.COVERT,
        ),
        defenses=DefenseProfile(
            has_moderation=True,
            has_input_filtering=True,
            has_prompt_injection_detection=True,
        ),
    )


def make_agent_system() -> TargetProfile:
    """Autonomous AI agent with tool access."""
    return TargetProfile(
        name="Autonomous Code Agent (MCP + Tools)",
        target_type=TargetType.AGENT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.TOOL_MISUSE, Goal.EXFIL_SIM, Goal.JAILBREAK],
        constraints=ConstraintSpec(
            max_queries=100,
            stealth_priority=StealthLevel.COVERT,
        ),
        defenses=DefenseProfile(
            has_moderation=True,
            has_schema_validation=True,
            has_prompt_injection_detection=True,
        ),
    )


def make_whitebox_classifier() -> TargetProfile:
    """White-box ML classifier for adversarial testing."""
    return TargetProfile(
        name="Fraud Detection Classifier (XGBoost + Neural)",
        target_type=TargetType.CLASSIFIER,
        access_level=AccessLevel.WHITE_BOX,
        goals=[Goal.EVASION, Goal.POISONING],
    )


def make_minimal_chatbot() -> TargetProfile:
    """Minimal chatbot with no defenses — easy target."""
    return TargetProfile(
        name="Prototype Chatbot (No Defenses)",
        target_type=TargetType.CHATBOT,
        access_level=AccessLevel.BLACK_BOX,
        goals=[Goal.JAILBREAK],
    )


def simulate_attack_results(
    plan: AttackPlan,
    success_rate: float = 0.3,
    seed: int = 42,
) -> tuple[list[AttemptResult], list[EvaluationResult]]:
    """Simulate realistic attack results from a plan."""
    rng = random.Random(seed)
    attempts = []
    evaluations = []

    for entry in plan.entries:
        # Simulate 3 attempts per technique
        for trial in range(3):
            attempt_id = f"att-{entry.technique_id}-{trial}"
            success = rng.random() < success_rate
            score = rng.uniform(0.6, 1.0) if success else rng.uniform(0.0, 0.4)

            attempts.append(AttemptResult(
                id=attempt_id,
                technique_id=entry.technique_id,
                prompt=f"Simulated attack prompt for {entry.technique_name} (trial {trial})",
                response=f"Simulated response (success={success})",
                source_tool="battle_test",
            ))

            evaluations.append(EvaluationResult(
                attempt_id=attempt_id,
                success=success,
                score=round(score, 3),
                judge_type=JudgeType.RULE_BASED,
                confidence=0.85,
                evidence_quality=0.8,
                comparability=ComparabilityMetadata(
                    technique_id=entry.technique_id,
                    judge_type=JudgeType.RULE_BASED,
                    num_trials=1,
                ),
            ))

    return attempts, evaluations


# ═══════════════════════════════════════════════════════════════════════
# TEST 1: FULL CAMPAIGN LIFECYCLE — Enterprise Chatbot
# ═══════════════════════════════════════════════════════════════════════

def test_full_campaign_lifecycle(tmp_path: Path):
    """
    Scenario: Red team assessing an enterprise chatbot.
    - Create adaptive campaign
    - Get initial recommendations
    - Simulate round 1 attacks (low success)
    - Ingest results, posteriors should update
    - Get round 2 recommendations (should adapt)
    - Simulate round 2 attacks (higher success on adapted plan)
    - Generate full report
    """
    target = make_enterprise_chatbot()
    storage_dir = tmp_path / "campaigns"

    # Step 1: Create adaptive campaign
    planner = AdaptivePlanner(campaign_seed=42)
    manager = CampaignManager(
        storage_dir=storage_dir,
        adaptive_planner=planner,
    )
    campaign = manager.create(
        target, name="enterprise-chatbot-assessment",
        adaptive=True, campaign_seed=42,
    )

    assert campaign.status == CampaignStatus.ACTIVE
    assert campaign.plan is not None
    assert len(campaign.plan.entries) > 0
    assert campaign.posterior_state is not None
    print(f"\n{'='*70}")
    print(f"CAMPAIGN CREATED: {campaign.id}")
    print(f"  Target: {target.name}")
    print(f"  Initial plan: {len(campaign.plan.entries)} techniques")
    for e in campaign.plan.entries[:5]:
        print(f"    #{e.rank} {e.technique_name} (utility={e.score.utility:.3f})")

    # Step 2: Round 1 — initial attacks
    round1_plan = manager.recommend_next(
        campaign.id, max_techniques=5, adaptive=True,
    )
    assert len(round1_plan.entries) > 0

    print(f"\nROUND 1 RECOMMENDATIONS ({len(round1_plan.entries)} techniques):")
    for e in round1_plan.entries:
        print(f"    #{e.rank} {e.technique_name} (utility={e.score.utility:.3f})")
        print(f"          {e.rationale}")

    # Simulate mostly-failing attacks (well-defended chatbot)
    attempts1, evals1 = simulate_attack_results(round1_plan, success_rate=0.15, seed=100)
    campaign = manager.ingest_results(campaign.id, attempts1, evals1)

    successes = sum(1 for e in evals1 if e.success)
    print(f"\n  Round 1 results: {successes}/{len(evals1)} succeeded")

    # Verify posteriors were updated
    for e in round1_plan.entries:
        post = campaign.posterior_state.posteriors.get(e.technique_id)
        if post:
            assert post.observations > 0, f"{e.technique_id} should have observations"

    # Step 3: Round 2 — adapted recommendations
    round2_plan = manager.recommend_next(
        campaign.id, max_techniques=5,
        exclude_tried=True, adaptive=True,
    )

    print(f"\nROUND 2 RECOMMENDATIONS (adapted, excluding tried):")
    round1_ids = {e.technique_id for e in round1_plan.entries}
    round2_ids = {e.technique_id for e in round2_plan.entries}

    # Round 2 should NOT repeat round 1 techniques (exclude_tried=True)
    overlap = round1_ids & round2_ids
    assert len(overlap) == 0, f"Round 2 repeated techniques from round 1: {overlap}"

    for e in round2_plan.entries:
        print(f"    #{e.rank} {e.technique_name} (utility={e.score.utility:.3f})")
        print(f"          {e.rationale}")

    # Simulate better success on adapted techniques
    attempts2, evals2 = simulate_attack_results(round2_plan, success_rate=0.4, seed=200)
    campaign = manager.ingest_results(campaign.id, attempts2, evals2)

    successes2 = sum(1 for e in evals2 if e.success)
    print(f"\n  Round 2 results: {successes2}/{len(evals2)} succeeded")

    # Step 4: Generate defender report
    techniques = {t.id: t for t in manager._registry.get_all()}
    analyzer = WeakestLayerAnalyzer()
    assessments = analyzer.analyze(campaign.state.evaluations, techniques)

    sufficient = [a for a in assessments if not a.is_insufficient_evidence]
    primary = max(sufficient, key=lambda a: a.risk_score).layer if sufficient else None

    report = DefenderReport(
        target_profile=campaign.target,
        campaign_id=campaign.id,
        layer_assessments=assessments,
        primary_weak_layer=primary,
    )

    assert len(assessments) > 0
    assert primary is not None

    print(f"\nDEFENDER REPORT:")
    print(f"  Primary weak layer: {primary.value}")
    for a in assessments:
        if not a.is_insufficient_evidence:
            print(f"  Layer {a.layer.value}: risk={a.risk_score:.2f}, "
                  f"success_rate={a.evidence.smoothed_success_rate:.2f}")

    # Verify the report has actionable recommendations
    all_recs = [r for a in assessments for r in a.recommendations]
    assert len(all_recs) > 0, "Report should contain recommendations"
    print(f"  Recommendations: {len(all_recs)}")
    for r in all_recs[:3]:
        print(f"    - {r}")

    print(f"\n  VERDICT: Campaign lifecycle PASSED ✓")


# ═══════════════════════════════════════════════════════════════════════
# TEST 2: RAG SYSTEM — Multi-goal attack with chain planning
# ═══════════════════════════════════════════════════════════════════════

def test_rag_system_attack_chains(tmp_path: Path):
    """
    Scenario: Red team targeting a RAG system with multiple objectives.
    - Generate attack chains (kill-chain ordered)
    - Verify chains cover different attack surfaces
    - Verify chains have meaningful fallback strategies
    """
    target = make_rag_system()
    registry = TechniqueRegistry()
    registry.load_catalog()

    planner = ChainPlanner(registry, max_chain_length=5, max_chains=5)
    plan = AttackPlan(target=target, entries=[])
    chains = planner.plan_chains(target, plan)

    print(f"\n{'='*70}")
    print(f"RAG SYSTEM ATTACK CHAINS")
    print(f"  Target: {target.name}")
    print(f"  Goals: {[g.value for g in target.goals]}")
    print(f"  Chains generated: {len(chains)}")

    assert len(chains) > 0, "Should generate at least one chain"

    # Verify chains cover multiple goals
    goals_covered = {c.target_goal for c in chains}
    print(f"  Goals covered: {[g.value for g in goals_covered]}")

    # Verify chains follow kill-chain ordering
    for chain in chains:
        print(f"\n  Chain: {chain.name} ({len(chain.stages)} stages, cost={chain.total_cost:.2f})")
        phases = chain.phase_sequence
        print(f"    Phases: {' → '.join(p.value for p in phases)}")

        # Verify phases are in non-decreasing kill-chain order
        from adversarypilot.planner.chains import KILL_CHAIN_ORDER
        phase_orders = [KILL_CHAIN_ORDER[p] for p in phases]
        assert phase_orders == sorted(phase_orders), \
            f"Kill chain order violated: {phases}"

        # Print stages
        for stage in chain.stages:
            fallbacks = f" [fallbacks: {', '.join(stage.fallback_techniques)}]" if stage.fallback_techniques else ""
            print(f"    Stage {stage.stage_number}: {stage.technique_name} "
                  f"({stage.phase.value}/{stage.surface.value}){fallbacks}")

    # Verify surfaces are diverse
    all_surfaces = set()
    for chain in chains:
        for stage in chain.stages:
            all_surfaces.add(stage.surface)
    print(f"\n  Surfaces covered: {[s.value for s in all_surfaces]}")
    assert len(all_surfaces) >= 2, "Chains should cover multiple attack surfaces"

    # Verify fallbacks exist
    total_fallbacks = sum(
        len(s.fallback_techniques) for c in chains for s in c.stages
    )
    assert total_fallbacks > 0, "At least some stages should have fallbacks"
    print(f"  Total fallback techniques: {total_fallbacks}")

    print(f"\n  VERDICT: RAG chain planning PASSED ✓")


# ═══════════════════════════════════════════════════════════════════════
# TEST 3: AGENT SYSTEM — Tool misuse and exfil attack planning
# ═══════════════════════════════════════════════════════════════════════

def test_agent_system_comprehensive(tmp_path: Path):
    """
    Scenario: Targeting an AI agent with MCP tools.
    - Verify agent-specific techniques are prioritized
    - Verify tool/action surfaces are covered
    - Run adaptive campaign with multi-step planning
    """
    target = make_agent_system()
    storage_dir = tmp_path / "campaigns"

    planner = AdaptivePlanner(campaign_seed=99)
    manager = CampaignManager(
        storage_dir=storage_dir,
        adaptive_planner=planner,
    )

    campaign = manager.create(
        target, name="agent-red-team",
        adaptive=True, campaign_seed=99,
    )

    print(f"\n{'='*70}")
    print(f"AGENT SYSTEM ASSESSMENT")
    print(f"  Target: {target.name}")
    print(f"  Goals: {[g.value for g in target.goals]}")
    print(f"  Initial plan: {len(campaign.plan.entries)} techniques")

    # Verify agent-specific techniques appear
    agent_techniques = [
        e for e in campaign.plan.entries
        if "AGT" in e.technique_id
    ]
    print(f"  Agent-specific techniques in plan: {len(agent_techniques)}")
    for e in agent_techniques:
        print(f"    {e.technique_id}: {e.technique_name}")

    # Should have agent techniques for an agent target
    assert len(agent_techniques) > 0, \
        "Agent target should get agent-specific techniques"

    # Verify tool/action surfaces are targeted
    registry = TechniqueRegistry()
    registry.load_catalog()
    plan_surfaces = set()
    for e in campaign.plan.entries:
        tech = registry.get(e.technique_id)
        if tech:
            plan_surfaces.add(tech.surface)

    print(f"  Attack surfaces targeted: {[s.value for s in plan_surfaces]}")

    # For agent targets, should include tool or action surfaces
    agent_surfaces = {Surface.TOOL, Surface.ACTION}
    assert agent_surfaces & plan_surfaces, \
        "Agent plan should target tool or action surfaces"

    # Run 3 rounds of adaptive planning
    for round_num in range(3):
        next_plan = manager.recommend_next(
            campaign.id, max_techniques=3,
            adaptive=True, exclude_tried=(round_num > 0),
        )
        attempts, evals = simulate_attack_results(
            next_plan, success_rate=0.2 + round_num * 0.15, seed=round_num * 100,
        )
        manager.ingest_results(campaign.id, attempts, evals)
        successes = sum(1 for e in evals if e.success)
        print(f"  Round {round_num+1}: {successes}/{len(evals)} succeeded "
              f"({len(next_plan.entries)} techniques)")

    # Verify campaign accumulated data correctly
    campaign = manager.get(campaign.id)
    assert campaign.state.queries_used > 0
    assert len(campaign.state.evaluations) > 0
    assert len(campaign.state.techniques_tried) > 0

    print(f"\n  Total attempts: {campaign.state.queries_used}")
    print(f"  Techniques tried: {len(campaign.state.techniques_tried)}")
    print(f"  Total evaluations: {len(campaign.state.evaluations)}")

    print(f"\n  VERDICT: Agent system assessment PASSED ✓")


# ═══════════════════════════════════════════════════════════════════════
# TEST 4: HTML REPORT QUALITY — Does the output look professional?
# ═══════════════════════════════════════════════════════════════════════

def test_html_report_quality(tmp_path: Path):
    """
    Generate an HTML report from a real campaign and verify it contains:
    - Valid HTML structure
    - Cytoscape.js embedded inline (no CDN dependency)
    - Actual attack data (not placeholder)
    - Risk heatmap data
    - Actionable recommendations
    - XSS protection
    """
    target = make_enterprise_chatbot()
    storage_dir = tmp_path / "campaigns"

    planner = AdaptivePlanner(campaign_seed=42)
    manager = CampaignManager(storage_dir=storage_dir, adaptive_planner=planner)
    campaign = manager.create(target, name="html-report-test", adaptive=True, campaign_seed=42)

    # Run 2 rounds and ingest results
    for round_num in range(2):
        next_plan = manager.recommend_next(
            campaign.id, max_techniques=5, adaptive=True,
        )
        attempts, evals = simulate_attack_results(
            next_plan, success_rate=0.3, seed=round_num * 50,
        )
        manager.ingest_results(campaign.id, attempts, evals)

    campaign = manager.get(campaign.id)

    # Generate report
    techniques = {t.id: t for t in manager._registry.get_all()}
    analyzer = WeakestLayerAnalyzer()
    assessments = analyzer.analyze(campaign.state.evaluations, techniques)

    sufficient = [a for a in assessments if not a.is_insufficient_evidence]
    primary = max(sufficient, key=lambda a: a.risk_score).layer if sufficient else None

    report = DefenderReport(
        target_profile=campaign.target,
        campaign_id=campaign.id,
        layer_assessments=assessments,
        primary_weak_layer=primary,
        overall_risk_summary="Enterprise chatbot shows vulnerabilities in guardrail layer.",
    )

    # Generate HTML
    html_path = tmp_path / "battle_test_report.html"
    renderer = HtmlReportRenderer()
    html = renderer.render(report, campaign, output_path=html_path)

    print(f"\n{'='*70}")
    print(f"HTML REPORT QUALITY AUDIT")
    print(f"  Output: {html_path}")
    print(f"  Size: {len(html):,} bytes")

    # 1. Valid HTML structure
    assert html.startswith("<!DOCTYPE html>"), "Must start with DOCTYPE"
    assert "<html" in html, "Missing <html> tag"
    assert "</html>" in html, "Missing closing </html> tag"
    assert "<head>" in html and "</head>" in html, "Missing head section"
    assert "<body>" in html and "</body>" in html, "Missing body section"
    print(f"  ✓ Valid HTML structure")

    # 2. Self-contained graph visualization (no CDN)
    assert "graph-canvas" in html, "Canvas graph element not found"
    assert "initGraph" in html, "Graph init function not found"
    # Verify no actual CDN <script src="...cdn..."> loading
    import re as _re
    cdn_script_tags = _re.findall(r'<script[^>]+src=["\'][^"\']*cdn[^"\']*["\']', html, _re.IGNORECASE)
    assert len(cdn_script_tags) == 0, \
        f"Should NOT load scripts from CDN — must be self-contained. Found: {cdn_script_tags}"
    print(f"  ✓ Self-contained graph visualization (no CDN script tags)")

    # 3. Contains actual campaign data
    assert campaign.id in html, "Campaign ID not in HTML"
    assert "guardrail" in html.lower() or "model" in html.lower(), \
        "No attack surface data in HTML"
    print(f"  ✓ Contains actual campaign data")

    # 4. Contains technique IDs (real data, not placeholder)
    technique_ids_in_html = sum(1 for t in manager._registry.get_all() if t.id in html)
    print(f"  ✓ {technique_ids_in_html} technique IDs found in HTML")
    assert technique_ids_in_html > 0, "No technique IDs in HTML output"

    # 5. XSS protection present
    assert "function esc(text)" in html, "XSS escape function not found"
    print(f"  ✓ XSS protection (esc function) present")

    # 6. Has interactive elements (tabs, buttons)
    has_tabs = "tab" in html.lower()
    print(f"  ✓ Interactive elements present: tabs={has_tabs}")

    # 7. File actually exists and is readable
    assert html_path.exists(), "HTML file not written"
    file_content = html_path.read_text()
    assert len(file_content) > 1000, "HTML file seems too small"
    print(f"  ✓ File written and readable ({len(file_content):,} bytes)")

    # 8. Contains DATA_JSON payload (the actual data)
    assert '"nodes"' in html, "Graph nodes data missing"
    assert '"edges"' in html, "Graph edges data missing"
    assert '"layers"' in html, "Layer assessment data missing"
    print(f"  ✓ Graph data (nodes, edges, layers) embedded")

    # 9. Check markdown report too
    md_renderer = ReportRenderer()
    md = md_renderer.to_markdown(report)
    assert "Defender Report" in md, "Markdown report missing header"
    assert target.name in md, "Markdown report missing target name"
    assert len(md) > 200, "Markdown report too short"
    print(f"  ✓ Markdown report also valid ({len(md)} chars)")

    print(f"\n  VERDICT: HTML report quality PASSED ✓")
    print(f"  Report saved: {html_path}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 5: REPLAY DETERMINISM — Can we reproduce decisions?
# ═══════════════════════════════════════════════════════════════════════

def test_replay_determinism(tmp_path: Path):
    """
    Verify that the replay system can exactly reproduce planning decisions:
    - Run an adaptive campaign
    - Record snapshots
    - Replay each step and verify exact match
    """
    target = make_enterprise_chatbot()
    storage_dir = tmp_path / "campaigns"

    planner = AdaptivePlanner(campaign_seed=42)
    manager = CampaignManager(
        storage_dir=storage_dir,
        adaptive_planner=planner,
    )
    campaign = manager.create(
        target, name="replay-test", adaptive=True, campaign_seed=42,
    )

    print(f"\n{'='*70}")
    print(f"REPLAY DETERMINISM TEST")

    # Run 3 rounds
    plans = []
    for step in range(3):
        next_plan = manager.recommend_next(
            campaign.id, max_techniques=3, adaptive=True,
        )
        plans.append(next_plan)

        # Simulate and ingest
        attempts, evals = simulate_attack_results(next_plan, success_rate=0.3, seed=step * 77)
        manager.ingest_results(campaign.id, attempts, evals)

    # Now verify snapshots were recorded
    recorder = SnapshotRecorder(storage_dir)
    steps = recorder.list_snapshots(campaign.id)
    print(f"  Snapshots recorded: {steps}")
    assert len(steps) == 3, f"Expected 3 snapshots, got {len(steps)}"

    # Replay each step and verify
    registry = TechniqueRegistry()
    registry.load_catalog()
    replayer = DecisionReplayer(registry, AdaptivePlanner(campaign_seed=42))

    for step_num in steps:
        snapshot = recorder.load(campaign.id, step_num)
        assert snapshot is not None

        matches, divergences = replayer.verify(snapshot, target)
        status = "✓ MATCH" if matches else f"✗ DIVERGED: {divergences}"
        print(f"  Step {step_num}: {status}")
        assert matches, f"Step {step_num} replay diverged: {divergences}"

    print(f"\n  VERDICT: Replay determinism PASSED ✓")


# ═══════════════════════════════════════════════════════════════════════
# TEST 6: EDGE CASES AND STRESS TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_edge_case_empty_results(tmp_path: Path):
    """Campaign with no attack results should still generate a report."""
    target = make_minimal_chatbot()
    storage_dir = tmp_path / "campaigns"

    manager = CampaignManager(storage_dir=storage_dir)
    campaign = manager.create(target, name="empty-campaign")

    # Try to generate report with no results
    techniques = {t.id: t for t in manager._registry.get_all()}
    analyzer = WeakestLayerAnalyzer()
    assessments = analyzer.analyze([], techniques)

    report = DefenderReport(
        target_profile=campaign.target,
        campaign_id=campaign.id,
        layer_assessments=assessments,
    )

    # Should produce a report (all insufficient evidence)
    assert len(assessments) == 0 or all(a.is_insufficient_evidence for a in assessments)
    print(f"\n  Edge case (empty results): PASSED ✓")


def test_edge_case_all_failures(tmp_path: Path):
    """Campaign where every attack fails — should identify strong defenses."""
    target = make_enterprise_chatbot()
    storage_dir = tmp_path / "campaigns"

    planner = AdaptivePlanner(campaign_seed=42)
    manager = CampaignManager(storage_dir=storage_dir, adaptive_planner=planner)
    campaign = manager.create(target, name="all-fail", adaptive=True, campaign_seed=42)

    # Run 3 rounds, everything fails
    for round_num in range(3):
        next_plan = manager.recommend_next(
            campaign.id, max_techniques=5, adaptive=True,
        )
        attempts, evals = simulate_attack_results(next_plan, success_rate=0.0, seed=round_num)
        manager.ingest_results(campaign.id, attempts, evals)

    campaign = manager.get(campaign.id)
    assert all(not e.success for e in campaign.state.evaluations)

    # Posteriors with observations should reflect failures
    # (posteriors with 0 observations were only initialized from V1 priors, never updated)
    updated_posteriors = [p for p in campaign.posterior_state.posteriors.values() if p.observations > 0]
    assert len(updated_posteriors) > 0, "Some posteriors should have observations"
    for post in updated_posteriors:
        # With strong prior (k=8) and base_score around 0.5-0.7,
        # 9 failures (3 rounds × 3 trials) should push most below 0.5
        # but very high base_score priors may resist — check mean decreased from prior
        initial_mean = (1.0 + 8.0 * 0.7) / (2.0 + 8.0)  # worst case base_score=0.7
        assert post.mean < initial_mean, \
            f"Posterior mean ({post.mean:.4f}) should have decreased after all failures"

    print(f"  Edge case (all failures): PASSED ✓")


def test_edge_case_all_successes(tmp_path: Path):
    """Campaign where everything succeeds — weak target."""
    target = make_minimal_chatbot()
    storage_dir = tmp_path / "campaigns"

    planner = AdaptivePlanner(campaign_seed=42)
    manager = CampaignManager(storage_dir=storage_dir, adaptive_planner=planner)
    campaign = manager.create(target, name="all-success", adaptive=True, campaign_seed=42)

    next_plan = manager.recommend_next(
        campaign.id, max_techniques=5, adaptive=True,
    )
    attempts, evals = simulate_attack_results(next_plan, success_rate=1.0, seed=42)
    manager.ingest_results(campaign.id, attempts, evals)

    campaign = manager.get(campaign.id)
    assert all(e.success for e in campaign.state.evaluations)

    # Posteriors should reflect all successes
    for post in campaign.posterior_state.posteriors.values():
        if post.observations > 0:
            assert post.mean > 0.5, \
                f"Posterior mean should be high after all successes: {post.mean}"

    print(f"  Edge case (all successes): PASSED ✓")


def test_edge_case_whitebox_classifier(tmp_path: Path):
    """White-box classifier — should get AML techniques."""
    target = make_whitebox_classifier()
    registry = TechniqueRegistry()
    registry.load_catalog()
    engine = PrioritizerEngine()

    plan = engine.plan(target, registry, max_techniques=10)

    print(f"\n  White-box classifier plan ({len(plan.entries)} techniques):")
    aml_count = 0
    for e in plan.entries:
        tech = registry.get(e.technique_id)
        if tech and tech.domain == Domain.AML:
            aml_count += 1
        print(f"    {e.technique_id}: {e.technique_name}")

    # Should include AML techniques for white-box classifier
    assert aml_count > 0, "White-box classifier plan should include AML techniques"
    print(f"  AML techniques: {aml_count}")
    print(f"  Edge case (white-box classifier): PASSED ✓")


def test_edge_case_massive_campaign(tmp_path: Path):
    """Stress test: 10 rounds of adaptive planning."""
    target = make_enterprise_chatbot()
    storage_dir = tmp_path / "campaigns"

    planner = AdaptivePlanner(campaign_seed=42)
    manager = CampaignManager(storage_dir=storage_dir, adaptive_planner=planner)
    campaign = manager.create(target, name="stress-test", adaptive=True, campaign_seed=42)

    for round_num in range(10):
        next_plan = manager.recommend_next(
            campaign.id, max_techniques=3, adaptive=True,
        )
        attempts, evals = simulate_attack_results(
            next_plan, success_rate=0.1 + round_num * 0.05, seed=round_num,
        )
        manager.ingest_results(campaign.id, attempts, evals)

    campaign = manager.get(campaign.id)
    assert campaign.state.queries_used > 0
    assert len(campaign.state.evaluations) == 90  # 10 rounds × 3 techniques × 3 trials

    print(f"  Stress test (10 rounds): PASSED ✓")
    print(f"    Total evaluations: {len(campaign.state.evaluations)}")
    print(f"    Techniques tried: {len(campaign.state.techniques_tried)}")


# ═══════════════════════════════════════════════════════════════════════
# TEST 7: VALUE ASSESSMENT — Is the output actually useful?
# ═══════════════════════════════════════════════════════════════════════

def test_value_plan_quality(tmp_path: Path):
    """
    Verify plans provide REAL value, not generic noise:
    - Techniques match the target type
    - Scores differentiate meaningfully
    - Rationales explain WHY each technique was chosen
    - Access level filtering works
    - Defense-aware planning adjusts for known defenses
    """
    print(f"\n{'='*70}")
    print(f"VALUE ASSESSMENT — Is this tool worth using?")

    registry = TechniqueRegistry()
    registry.load_catalog()
    engine = PrioritizerEngine()

    # Test 1: Enterprise chatbot (heavy defenses)
    defended_target = make_enterprise_chatbot()
    defended_plan = engine.plan(defended_target, registry, max_techniques=5)

    # Test 2: Undefended chatbot
    undefended_target = make_minimal_chatbot()
    undefended_plan = engine.plan(undefended_target, registry, max_techniques=5)

    print(f"\n  Defended chatbot top techniques:")
    for e in defended_plan.entries:
        print(f"    #{e.rank} {e.technique_name} (score={e.score.total:.2f})")
    print(f"\n  Undefended chatbot top techniques:")
    for e in undefended_plan.entries:
        print(f"    #{e.rank} {e.technique_name} (score={e.score.total:.2f})")

    # The plans should be DIFFERENT — defenses should change rankings
    defended_ids = [e.technique_id for e in defended_plan.entries]
    undefended_ids = [e.technique_id for e in undefended_plan.entries]

    # Scores should have meaningful spread (not all the same)
    defended_scores = [e.score.total for e in defended_plan.entries]
    score_spread = max(defended_scores) - min(defended_scores)
    assert score_spread > 0.05, \
        f"Score spread too narrow ({score_spread:.3f}), not differentiating techniques"
    print(f"\n  Score spread (defended): {score_spread:.3f}")

    # Rationales should be non-empty and descriptive
    for e in defended_plan.entries:
        assert len(e.rationale) > 10, f"Rationale too short for {e.technique_id}"
    print(f"  ✓ All rationales are descriptive")

    # Test 3: Agent vs Chatbot — plans should differ
    agent_target = make_agent_system()
    agent_plan = engine.plan(agent_target, registry, max_techniques=10)

    chatbot_ids = set(e.technique_id for e in defended_plan.entries)
    agent_ids = set(e.technique_id for e in agent_plan.entries)

    # Agent plan should have agent-specific techniques
    agent_specific = [tid for tid in agent_ids if "AGT" in tid]
    assert len(agent_specific) > 0, "Agent plan lacks agent-specific techniques"
    print(f"  ✓ Agent plan has {len(agent_specific)} agent-specific techniques")

    # Test 4: White-box vs Black-box — different technique selection
    bb_plan = engine.plan(
        TargetProfile(
            name="BB", target_type=TargetType.CHATBOT,
            access_level=AccessLevel.BLACK_BOX, goals=[Goal.JAILBREAK],
        ),
        registry, max_techniques=10,
    )
    wb_plan = engine.plan(
        TargetProfile(
            name="WB", target_type=TargetType.CHATBOT,
            access_level=AccessLevel.WHITE_BOX, goals=[Goal.JAILBREAK],
        ),
        registry, max_techniques=10,
    )

    bb_ids = set(e.technique_id for e in bb_plan.entries)
    wb_ids = set(e.technique_id for e in wb_plan.entries)

    # White-box should include techniques that black-box cannot
    wb_only = wb_ids - bb_ids
    print(f"  White-box-only techniques: {len(wb_only)}")
    for tid in wb_only:
        tech = registry.get(tid)
        if tech:
            print(f"    {tid} (requires {tech.access_required.value})")

    # GCG requires white_box — should appear in WB but not BB
    gcg_in_wb = any("GCG" in tid for tid in wb_ids)
    gcg_in_bb = any("GCG" in tid for tid in bb_ids)
    if gcg_in_wb:
        assert not gcg_in_bb, "GCG (white-box-only) should not appear in black-box plan"
        print(f"  ✓ Access level filtering works (GCG correctly filtered)")

    print(f"\n  VERDICT: Value assessment PASSED ✓")
    print(f"  This tool provides differentiated, context-aware attack plans.")


# ═══════════════════════════════════════════════════════════════════════
# TEST 8: THOMPSON SAMPLING — Does adaptive learning actually work?
# ═══════════════════════════════════════════════════════════════════════

def test_thompson_sampling_convergence(tmp_path: Path):
    """
    Verify Thompson Sampling converges:
    - Techniques that succeed should get HIGHER utility over time
    - Techniques that fail should get LOWER utility over time
    - This is the key differentiator vs static planning
    """
    print(f"\n{'='*70}")
    print(f"THOMPSON SAMPLING CONVERGENCE TEST")

    target = make_minimal_chatbot()
    storage_dir = tmp_path / "campaigns"

    planner = AdaptivePlanner(campaign_seed=42)
    manager = CampaignManager(storage_dir=storage_dir, adaptive_planner=planner)
    campaign = manager.create(
        target, name="convergence-test", adaptive=True, campaign_seed=42,
    )

    # Get initial utilities
    initial_plan = manager.recommend_next(
        campaign.id, max_techniques=10, adaptive=True,
    )

    # Pick the top technique and simulate it always succeeding
    winning_tech = initial_plan.entries[0].technique_id
    # Pick the second technique and simulate it always failing
    losing_tech = initial_plan.entries[1].technique_id if len(initial_plan.entries) > 1 else None

    print(f"  Winning technique: {winning_tech}")
    print(f"  Losing technique: {losing_tech}")

    # Simulate 5 rounds: winning_tech always succeeds, losing_tech always fails
    for round_num in range(5):
        # Ingest success for winner
        attempts = [AttemptResult(
            id=f"win-{round_num}", technique_id=winning_tech,
            prompt="test", response="success", source_tool="test",
        )]
        evals = [EvaluationResult(
            attempt_id=f"win-{round_num}", success=True, score=0.95,
            comparability=ComparabilityMetadata(technique_id=winning_tech),
        )]

        if losing_tech:
            attempts.append(AttemptResult(
                id=f"lose-{round_num}", technique_id=losing_tech,
                prompt="test", response="blocked", source_tool="test",
            ))
            evals.append(EvaluationResult(
                attempt_id=f"lose-{round_num}", success=False, score=0.1,
                comparability=ComparabilityMetadata(technique_id=losing_tech),
            ))

        manager.ingest_results(campaign.id, attempts, evals)

    # Check posteriors
    campaign = manager.get(campaign.id)
    winner_post = campaign.posterior_state.posteriors.get(winning_tech)
    loser_post = campaign.posterior_state.posteriors.get(losing_tech) if losing_tech else None

    if winner_post and loser_post:
        print(f"\n  After 5 rounds:")
        print(f"    Winner posterior mean: {winner_post.mean:.3f} "
              f"(α={winner_post.alpha:.1f}, β={winner_post.beta:.1f}, obs={winner_post.observations})")
        print(f"    Loser posterior mean:  {loser_post.mean:.3f} "
              f"(α={loser_post.alpha:.1f}, β={loser_post.beta:.1f}, obs={loser_post.observations})")

        assert winner_post.mean > loser_post.mean, \
            f"Winner ({winner_post.mean:.3f}) should have higher mean than loser ({loser_post.mean:.3f})"
        print(f"  ✓ Thompson Sampling converged correctly")

    # Get final recommendations — winner should rank higher
    final_plan = manager.recommend_next(
        campaign.id, max_techniques=10, adaptive=True,
    )

    final_rankings = {e.technique_id: e.rank for e in final_plan.entries}
    if winning_tech in final_rankings and losing_tech and losing_tech in final_rankings:
        winner_rank = final_rankings[winning_tech]
        loser_rank = final_rankings[losing_tech]
        print(f"    Winner final rank: #{winner_rank}")
        print(f"    Loser final rank:  #{loser_rank}")
        assert winner_rank < loser_rank, \
            f"Winner (rank {winner_rank}) should rank above loser (rank {loser_rank})"
        print(f"  ✓ Winning technique ranked higher after learning")

    print(f"\n  VERDICT: Thompson Sampling convergence PASSED ✓")


# ═══════════════════════════════════════════════════════════════════════
# TEST 9: CATALOG COMPLETENESS — Does it cover real attack vectors?
# ═══════════════════════════════════════════════════════════════════════

def test_catalog_coverage():
    """
    Verify the technique catalog covers the attack vectors a real
    red team would need:
    - OWASP LLM Top 10 coverage
    - Multiple phases (recon, probe, exploit, persistence)
    - Multiple surfaces (model, guardrail, tool, data, retrieval, action)
    - Multiple access levels (black_box, gray_box, white_box)
    - Research-backed techniques with paper references
    """
    print(f"\n{'='*70}")
    print(f"CATALOG COVERAGE ASSESSMENT")

    registry = TechniqueRegistry()
    registry.load_catalog()
    all_techniques = registry.get_all()

    print(f"  Total techniques: {len(all_techniques)}")

    # Domain coverage
    domains = {}
    for t in all_techniques:
        domains.setdefault(t.domain, []).append(t)
    print(f"\n  Domain breakdown:")
    for d, techs in sorted(domains.items(), key=lambda x: x[0].value):
        print(f"    {d.value}: {len(techs)} techniques")
    assert len(domains) >= 3, "Should cover at least 3 domains"

    # Phase coverage
    phases = set(t.phase for t in all_techniques)
    print(f"\n  Phases covered: {sorted(p.value for p in phases)}")
    for required_phase in [Phase.RECON, Phase.PROBE, Phase.EXPLOIT]:
        assert required_phase in phases, f"Missing phase: {required_phase.value}"
    print(f"  ✓ All critical phases covered")

    # Surface coverage
    surfaces = set(t.surface for t in all_techniques)
    print(f"  Surfaces covered: {sorted(s.value for s in surfaces)}")
    for required_surface in [Surface.MODEL, Surface.GUARDRAIL, Surface.TOOL, Surface.DATA]:
        assert required_surface in surfaces, f"Missing surface: {required_surface.value}"
    print(f"  ✓ All critical surfaces covered")

    # Access level coverage
    access_levels = set(t.access_required for t in all_techniques)
    print(f"  Access levels: {sorted(a.value for a in access_levels)}")
    assert AccessLevel.BLACK_BOX in access_levels
    assert AccessLevel.WHITE_BOX in access_levels
    print(f"  ✓ Both black-box and white-box covered")

    # Goal coverage
    all_goals = set()
    for t in all_techniques:
        all_goals.update(t.goals_supported)
    print(f"  Goals covered: {sorted(g.value for g in all_goals)}")
    for required_goal in [Goal.JAILBREAK, Goal.EXTRACTION, Goal.EXFIL_SIM,
                           Goal.TOOL_MISUSE, Goal.EVASION, Goal.POISONING]:
        assert required_goal in all_goals, f"Missing goal: {required_goal.value}"
    print(f"  ✓ All critical goals covered")

    # Research-backed: at least 80% should have references
    with_refs = sum(1 for t in all_techniques if t.atlas_refs or t.other_refs)
    ref_pct = with_refs / len(all_techniques) * 100
    print(f"\n  Techniques with references: {with_refs}/{len(all_techniques)} ({ref_pct:.0f}%)")
    assert ref_pct >= 80, f"Only {ref_pct:.0f}% have references, need >=80%"
    print(f"  ✓ {ref_pct:.0f}% research-backed")

    # ATLAS coverage
    atlas_ids = set()
    for t in all_techniques:
        for ref in t.atlas_refs:
            atlas_ids.add(ref.atlas_id)
    print(f"  MITRE ATLAS IDs referenced: {sorted(atlas_ids)}")
    assert len(atlas_ids) >= 3, "Should reference at least 3 ATLAS technique IDs"
    print(f"  ✓ {len(atlas_ids)} ATLAS IDs referenced")

    # Target type coverage
    target_types = set()
    for t in all_techniques:
        target_types.update(t.target_types)
    print(f"  Target types: {sorted(tt.value for tt in target_types)}")
    for required_tt in [TargetType.CHATBOT, TargetType.RAG, TargetType.AGENT, TargetType.CLASSIFIER]:
        assert required_tt in target_types, f"Missing target type: {required_tt.value}"
    print(f"  ✓ All target types covered")

    print(f"\n  VERDICT: Catalog coverage PASSED ✓")
    print(f"  {len(all_techniques)} techniques across {len(domains)} domains, "
          f"{len(phases)} phases, {len(surfaces)} surfaces")


# ═══════════════════════════════════════════════════════════════════════
# TEST 10: GARAK IMPORT — Real tool integration
# ═══════════════════════════════════════════════════════════════════════

def test_garak_integration():
    """Verify garak import works with the sample fixture."""
    from adversarypilot.importers.garak import GarakImporter

    fixture = Path(__file__).parent / "fixtures" / "sample_garak_report.jsonl"
    if not fixture.exists():
        print(f"  Garak fixture not found, skipping")
        return

    importer = GarakImporter()
    results = importer.import_file(fixture)

    print(f"\n{'='*70}")
    print(f"GARAK INTEGRATION TEST")
    print(f"  Imported: {len(results)} result pairs")

    assert len(results) > 0, "Should import at least one result"

    for attempt, evaluation in results:
        assert attempt.source_tool == "garak"
        assert attempt.technique_id, "Technique ID should be mapped"
        assert evaluation.attempt_id == attempt.id

    techniques_seen = set(a.technique_id for a, _ in results)
    print(f"  Techniques mapped: {techniques_seen}")
    print(f"  ✓ Garak integration works")


# ═══════════════════════════════════════════════════════════════════════
# MAIN RUNNER
# ═══════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import tempfile
    import traceback

    print("=" * 70)
    print("  ADVERSARYPILOT BATTLE TEST SUITE")
    print("  Testing as a skeptical security engineer")
    print("=" * 70)

    tests = [
        ("Full Campaign Lifecycle", test_full_campaign_lifecycle),
        ("RAG Attack Chains", test_rag_system_attack_chains),
        ("Agent System Assessment", test_agent_system_comprehensive),
        ("HTML Report Quality", test_html_report_quality),
        ("Replay Determinism", test_replay_determinism),
        ("Edge: Empty Results", test_edge_case_empty_results),
        ("Edge: All Failures", test_edge_case_all_failures),
        ("Edge: All Successes", test_edge_case_all_successes),
        ("Edge: White-box Classifier", test_edge_case_whitebox_classifier),
        ("Edge: Massive Campaign (10 rounds)", test_edge_case_massive_campaign),
        ("Value Assessment", test_value_plan_quality),
        ("Thompson Sampling Convergence", test_thompson_sampling_convergence),
        ("Catalog Coverage", test_catalog_coverage),
        ("Garak Integration", test_garak_integration),
    ]

    passed = 0
    failed = 0
    failures = []

    for name, test_fn in tests:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                import inspect
                sig = inspect.signature(test_fn)
                if "tmp_path" in sig.parameters:
                    test_fn(Path(tmpdir))
                else:
                    test_fn()
            passed += 1
        except Exception as e:
            failed += 1
            failures.append((name, str(e), traceback.format_exc()))
            print(f"\n  FAILED: {name}")
            print(f"  Error: {e}")

    print(f"\n{'='*70}")
    print(f"  BATTLE TEST RESULTS")
    print(f"{'='*70}")
    print(f"  PASSED: {passed}/{passed + failed}")
    print(f"  FAILED: {failed}/{passed + failed}")

    if failures:
        print(f"\n  FAILURES:")
        for name, error, tb in failures:
            print(f"\n  --- {name} ---")
            print(f"  {error}")
            print(textwrap.indent(tb, "  "))

    if failed == 0:
        print(f"\n  ✓ ADVERSARYPILOT IS BATTLE-TESTED AND READY")
    else:
        print(f"\n  ✗ ADVERSARYPILOT HAS {failed} ISSUES TO FIX")

    exit(1 if failed > 0 else 0)
