"""AdversaryPilot CLI — thin Typer wrapper over library calls."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console

from adversarypilot import __version__

app = typer.Typer(
    name="adversarypilot",
    help="ATLAS-aligned attack planning engine for adversarial ML and LLM/agent systems.",
    no_args_is_help=True,
)
console = Console()

techniques_app = typer.Typer(help="Manage attack technique catalog.")
campaign_app = typer.Typer(help="Manage attack campaigns.")
import_app = typer.Typer(help="Import results from external tools.", name="import")
app.add_typer(techniques_app, name="techniques")
app.add_typer(campaign_app, name="campaign")
app.add_typer(import_app, name="import")


def _load_target(path: Path) -> "TargetProfile":
    from adversarypilot.models.target import TargetProfile

    with open(path) as f:
        data = yaml.safe_load(f)
    return TargetProfile.model_validate(data)


@app.command()
def version() -> None:
    """Show AdversaryPilot version."""
    console.print(f"adversarypilot {__version__}")


@app.command()
def validate(target_file: Path = typer.Argument(..., help="Path to target profile YAML")) -> None:
    """Validate a target profile YAML file."""
    try:
        target = _load_target(target_file)
        console.print(f"[green]Valid target profile:[/green] {target.name}")
        console.print(f"  Type: {target.target_type.value}")
        console.print(f"  Access: {target.access_level.value}")
        console.print(f"  Goals: {', '.join(g.value for g in target.goals)}")
    except Exception as e:
        console.print(f"[red]Validation failed:[/red] {e}")
        raise typer.Exit(1)


@app.command()
def plan(
    target_file: Path = typer.Argument(..., help="Path to target profile YAML"),
    max_techniques: Optional[int] = typer.Option(None, "--max", "-m", help="Max techniques to show"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write plan JSON to file"),
) -> None:
    """Generate a ranked attack plan for a target."""
    from adversarypilot.prioritizer.engine import PrioritizerEngine
    from adversarypilot.taxonomy.registry import TechniqueRegistry

    target = _load_target(target_file)
    registry = TechniqueRegistry()
    registry.load_catalog()
    engine = PrioritizerEngine()

    attack_plan = engine.plan(target, registry, max_techniques=max_techniques)

    if output:
        output.write_text(attack_plan.model_dump_json(indent=2))
        console.print(f"[green]Plan written to {output}[/green]")
    else:
        console.print(f"\n[bold]Attack Plan for: {target.name}[/bold]")
        console.print(f"Target: {target.target_type.value} ({target.access_level.value})")
        console.print(f"Techniques: {len(attack_plan.entries)}\n")
        for entry in attack_plan.entries:
            console.print(
                f"  [cyan]#{entry.rank}[/cyan] {entry.technique_name} "
                f"[dim]({entry.technique_id})[/dim]"
            )
            console.print(f"      Score: {entry.score.total:.2f}")
            console.print(f"      {entry.rationale}")
            console.print()


@app.command()
def report(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    storage_dir: Path = typer.Option(
        Path(".adversarypilot/campaigns"), "--dir", "-d", help="Campaign storage directory"
    ),
    format: str = typer.Option("terminal", "--format", "-f", help="Output format: terminal, markdown, json, html"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write report to file"),
) -> None:
    """Generate a defender report for a campaign."""
    from adversarypilot.campaign.manager import CampaignManager
    from adversarypilot.reporting.analyzer import WeakestLayerAnalyzer
    from adversarypilot.reporting.comparability import ComparabilityChecker
    from adversarypilot.reporting.renderer import ReportRenderer
    from adversarypilot.reporting.html_renderer import HtmlReportRenderer
    from adversarypilot.models.report import DefenderReport
    from adversarypilot.taxonomy.registry import TechniqueRegistry

    manager = CampaignManager(storage_dir=storage_dir)
    campaign = manager.get(campaign_id)
    if campaign is None:
        console.print(f"[red]Campaign {campaign_id} not found[/red]")
        raise typer.Exit(1)

    registry = TechniqueRegistry()
    registry.load_catalog()
    techniques = {t.id: t for t in registry.get_all()}

    analyzer = WeakestLayerAnalyzer()
    assessments = analyzer.analyze(campaign.state.evaluations, techniques)

    checker = ComparabilityChecker()
    warnings = checker.check_group(campaign.state.evaluations)

    sufficient = [a for a in assessments if not a.is_insufficient_evidence]
    primary = max(sufficient, key=lambda a: a.risk_score).layer if sufficient else None
    secondary = [
        a.layer for a in sufficient
        if a.layer != primary and a.risk_score > 0.2
    ]

    report_obj = DefenderReport(
        target_profile=campaign.target,
        campaign_id=campaign.id,
        layer_assessments=assessments,
        primary_weak_layer=primary,
        secondary_weak_layers=secondary,
        comparability_warnings=warnings,
    )

    if format == "html":
        html_renderer = HtmlReportRenderer(registry)
        text = html_renderer.render(report_obj, campaign, output_path=output)
        if not output:
            console.print("[yellow]HTML format requires --output/-o path[/yellow]")
            raise typer.Exit(1)
        console.print(f"[green]HTML report written to {output}[/green]")
        return

    renderer = ReportRenderer()
    if format == "json":
        text = renderer.to_json(report_obj)
    elif format == "markdown":
        text = renderer.to_markdown(report_obj)
    else:
        text = renderer.to_terminal(report_obj)

    if output:
        output.write_text(text)
        console.print(f"[green]Report written to {output}[/green]")
    else:
        console.print(text)


# ─── Techniques subcommands ────────────────────────────────────────────


@techniques_app.command("list")
def techniques_list(
    domain: Optional[str] = typer.Option(None, "--domain", help="Filter by domain: aml, llm, agent"),
    surface: Optional[str] = typer.Option(None, "--surface", help="Filter by surface"),
    goal: Optional[str] = typer.Option(None, "--goal", help="Filter by goal"),
    tool: Optional[str] = typer.Option(None, "--tool", help="Filter by tool support"),
) -> None:
    """List attack techniques with optional filters."""
    from adversarypilot.models.enums import Domain, Goal, Surface
    from adversarypilot.taxonomy.registry import TechniqueRegistry

    registry = TechniqueRegistry()
    registry.load_catalog()

    kwargs: dict = {}
    if domain:
        kwargs["domain"] = Domain(domain)
    if surface:
        kwargs["surface"] = Surface(surface)
    if goal:
        kwargs["goal"] = Goal(goal)
    if tool:
        kwargs["tool"] = tool

    techniques = registry.filter(**kwargs)

    console.print(f"\n[bold]Techniques ({len(techniques)}):[/bold]\n")
    for t in techniques:
        goals = ", ".join(g.value for g in t.goals_supported)
        console.print(
            f"  [cyan]{t.id}[/cyan]  {t.name}"
        )
        console.print(
            f"    {t.domain.value}/{t.phase.value}/{t.surface.value}  "
            f"goals=\\[{goals}]  cost={t.base_cost:.1f}  "
            f"access={t.access_required.value}"
        )
        if t.atlas_refs:
            refs = ", ".join(r.atlas_id for r in t.atlas_refs)
            console.print(f"    ATLAS: {refs}")
        console.print()


# ─── Campaign subcommands ──────────────────────────────────────────────


@campaign_app.command("new")
def campaign_new(
    target_file: Path = typer.Argument(..., help="Path to target profile YAML"),
    name: str = typer.Option("", "--name", "-n", help="Campaign name"),
    storage_dir: Path = typer.Option(
        Path(".adversarypilot/campaigns"), "--dir", "-d", help="Storage directory"
    ),
    adaptive: bool = typer.Option(False, "--adaptive", help="Use adaptive planner"),
    seed: Optional[int] = typer.Option(None, "--seed", help="Random seed for deterministic planning"),
) -> None:
    """Create a new campaign."""
    from adversarypilot.campaign.manager import CampaignManager
    from adversarypilot.planner.adaptive import AdaptivePlanner

    target = _load_target(target_file)

    # Create adaptive planner if requested
    adaptive_planner = AdaptivePlanner(campaign_seed=seed) if adaptive else None

    manager = CampaignManager(storage_dir=storage_dir, adaptive_planner=adaptive_planner)
    campaign = manager.create(target, name=name, adaptive=adaptive, campaign_seed=seed)

    console.print(f"[green]Campaign created:[/green] {campaign.id}")
    console.print(f"  Name: {campaign.name}")
    console.print(f"  Status: {campaign.status.value}")
    if adaptive:
        console.print(f"  Mode: Adaptive (seed={seed or 'auto'})")
    if campaign.plan:
        console.print(f"  Plan: {len(campaign.plan.entries)} techniques")


@campaign_app.command("next")
def campaign_next(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    max_techniques: int = typer.Option(5, "--max", "-m", help="Max recommendations"),
    storage_dir: Path = typer.Option(
        Path(".adversarypilot/campaigns"), "--dir", "-d", help="Storage directory"
    ),
    adaptive: bool = typer.Option(False, "--adaptive", help="Use adaptive planner"),
    exclude_tried: bool = typer.Option(False, "--exclude-tried", help="Exclude tried techniques"),
    repeat_penalty: float = typer.Option(0.0, "--repeat-penalty", help="Penalty for repeat techniques"),
) -> None:
    """Get next recommended techniques for a campaign."""
    from adversarypilot.campaign.manager import CampaignManager
    from adversarypilot.planner.adaptive import AdaptivePlanner

    # Create adaptive planner if requested
    adaptive_planner = AdaptivePlanner() if adaptive else None

    manager = CampaignManager(storage_dir=storage_dir, adaptive_planner=adaptive_planner)
    next_plan = manager.recommend_next(
        campaign_id,
        max_techniques=max_techniques,
        exclude_tried=exclude_tried,
        repeat_penalty=repeat_penalty,
        adaptive=adaptive,
    )

    campaign = manager.get(campaign_id)
    if campaign:
        console.print(f"\n[dim]Phase: {campaign.phase.value.upper()}[/dim]")

    console.print(f"\n[bold]Next Recommended Techniques:[/bold]\n")
    for entry in next_plan.entries:
        score_display = entry.score.utility if entry.score.utility is not None else entry.score.total
        console.print(
            f"  [cyan]#{entry.rank}[/cyan] {entry.technique_name} "
            f"(score={score_display:.2f})"
        )
        console.print(f"      {entry.rationale}")
        console.print()


# ─── Import subcommands ────────────────────────────────────────────────


@import_app.command("garak")
def import_garak(
    report_file: Path = typer.Argument(..., help="Path to garak JSONL report"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write results JSON to file"),
) -> None:
    """Import results from a garak JSONL report."""
    from adversarypilot.importers.garak import GarakImporter
    import json

    importer = GarakImporter()
    results = importer.import_file(report_file)

    console.print(f"[green]Imported {len(results)} result pairs from garak[/green]")

    techniques_seen: dict[str, int] = {}
    successes = 0
    for attempt, evaluation in results:
        techniques_seen[attempt.technique_id] = techniques_seen.get(attempt.technique_id, 0) + 1
        if evaluation.success:
            successes += 1

    console.print(f"  Techniques mapped: {len(techniques_seen)}")
    console.print(f"  Successful attacks: {successes}/{len(results)}")

    for tid, count in sorted(techniques_seen.items()):
        console.print(f"    {tid}: {count} attempts")

    if output:
        data = [
            {
                "attempt": attempt.model_dump(mode="json"),
                "evaluation": evaluation.model_dump(mode="json"),
            }
            for attempt, evaluation in results
        ]
        output.write_text(json.dumps(data, indent=2, default=str))
        console.print(f"[green]Results written to {output}[/green]")


# ─── Replay command ────────────────────────────────────────────────────


@app.command()
def replay(
    campaign_id: str = typer.Argument(..., help="Campaign ID"),
    step: Optional[int] = typer.Option(None, "--step", help="Step number to replay"),
    storage_dir: Path = typer.Option(
        Path(".adversarypilot/campaigns"), "--dir", "-d", help="Storage directory"
    ),
    verify: bool = typer.Option(False, "--verify", help="Verify replay matches original"),
) -> None:
    """Replay a planning decision from snapshot."""
    from adversarypilot.campaign.manager import CampaignManager
    from adversarypilot.replay.recorder import SnapshotRecorder
    from adversarypilot.replay.replayer import DecisionReplayer
    from adversarypilot.taxonomy.registry import TechniqueRegistry

    # Load campaign
    manager = CampaignManager(storage_dir=storage_dir)
    campaign = manager.get(campaign_id)
    if campaign is None:
        console.print(f"[red]Campaign {campaign_id} not found[/red]")
        raise typer.Exit(1)

    # Load snapshot
    recorder = SnapshotRecorder(storage_dir)
    if step is None:
        # Use latest snapshot
        steps = recorder.list_snapshots(campaign_id)
        if not steps:
            console.print(f"[red]No snapshots found for campaign {campaign_id}[/red]")
            raise typer.Exit(1)
        step = steps[-1]

    snapshot = recorder.load(campaign_id, step)
    if snapshot is None:
        console.print(f"[red]Snapshot not found: campaign={campaign_id}, step={step}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Replaying Decision:[/bold]")
    console.print(f"  Campaign: {campaign_id}")
    console.print(f"  Step: {step}")
    console.print(f"  Timestamp: {snapshot.timestamp}")
    console.print(f"  Step seed: {snapshot.step_seed}")

    # Replay
    registry = TechniqueRegistry()
    registry.load_catalog()
    replayer = DecisionReplayer(registry)

    if verify:
        matches, divergences = replayer.verify(snapshot, campaign.target)
        if matches:
            console.print(f"\n[green]✓ Replay matches original decision[/green]")
        else:
            console.print(f"\n[red]✗ Replay diverges from original:[/red]")
            for div in divergences:
                console.print(f"  - {div}")
    else:
        plan = replayer.replay(snapshot, campaign.target)
        console.print(f"\n[bold]Replayed Plan ({len(plan.entries)} techniques):[/bold]\n")
        for entry in plan.entries:
            console.print(
                f"  [cyan]#{entry.rank}[/cyan] {entry.technique_name} "
                f"(score={entry.score.utility or entry.score.total:.2f})"
            )
            console.print(f"      {entry.rationale}")
            console.print()


@app.command()
def chains(
    target_file: Path = typer.Argument(..., help="Path to target profile YAML"),
    max_length: int = typer.Option(5, "--max-length", help="Max stages per chain"),
    max_chains: int = typer.Option(3, "--max-chains", help="Max chains to generate"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Write chains JSON to file"),
) -> None:
    """Generate multi-stage attack chains for a target."""
    import json

    from adversarypilot.models.plan import AttackPlan
    from adversarypilot.planner.chains import ChainPlanner
    from adversarypilot.taxonomy.registry import TechniqueRegistry

    target = _load_target(target_file)
    registry = TechniqueRegistry()
    registry.load_catalog()

    planner = ChainPlanner(registry, max_chain_length=max_length, max_chains=max_chains)
    plan = AttackPlan(target=target, entries=[])
    attack_chains = planner.plan_chains(target, plan)

    if output:
        data = [c.to_dict() for c in attack_chains]
        output.write_text(json.dumps(data, indent=2, default=str))
        console.print(f"[green]Chains written to {output}[/green]")
    else:
        console.print(f"\n[bold]Attack Chains for: {target.name}[/bold]")
        console.print(f"Generated {len(attack_chains)} kill chains\n")

        for chain in attack_chains:
            console.print(f"  [bold cyan]{chain.name}[/bold cyan]  (cost={chain.total_cost:.2f})")
            for stage in chain.stages:
                deps = f" [depends: {stage.depends_on}]" if stage.depends_on else ""
                console.print(
                    f"    Stage {stage.stage_number}: [{stage.phase.value}] "
                    f"{stage.technique_name} -> {stage.surface.value}{deps}"
                )
                console.print(f"      {stage.rationale}")
                if stage.fallback_techniques:
                    console.print(f"      Fallbacks: {', '.join(stage.fallback_techniques)}")
            console.print()


if __name__ == "__main__":
    app()
