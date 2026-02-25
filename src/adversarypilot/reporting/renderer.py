"""Report renderer — outputs DefenderReport as JSON, markdown, or Rich terminal."""

from __future__ import annotations

import json
from typing import Any

from adversarypilot.models.report import DefenderReport


class ReportRenderer:
    """Renders DefenderReport in multiple formats."""

    def to_json(self, report: DefenderReport, indent: int = 2) -> str:
        """Render report as JSON string."""
        return report.model_dump_json(indent=indent)

    def to_dict(self, report: DefenderReport) -> dict[str, Any]:
        """Render report as a dictionary."""
        return json.loads(report.model_dump_json())

    def to_markdown(self, report: DefenderReport) -> str:
        """Render report as a markdown string."""
        lines = []
        lines.append(f"# Defender Report: {report.target_profile.name}")
        lines.append("")
        lines.append(f"**Campaign:** {report.campaign_id}")
        lines.append(f"**Generated:** {report.generated_at.isoformat()}")
        lines.append(f"**Target Type:** {report.target_profile.target_type.value}")
        lines.append(f"**Access Level:** {report.target_profile.access_level.value}")
        lines.append("")

        # Risk summary
        lines.append("## Risk Summary")
        lines.append("")
        if report.primary_weak_layer:
            lines.append(
                f"**Primary Weakness:** {report.primary_weak_layer.value} layer"
            )
        if report.secondary_weak_layers:
            secondary = ", ".join(l.value for l in report.secondary_weak_layers)
            lines.append(f"**Secondary Concerns:** {secondary}")
        lines.append("")
        if report.overall_risk_summary:
            lines.append(report.overall_risk_summary)
            lines.append("")

        # Layer assessments
        lines.append("## Layer Assessments")
        lines.append("")
        for assessment in report.layer_assessments:
            status = "INSUFFICIENT DATA" if assessment.is_insufficient_evidence else ""
            primary = " (PRIMARY WEAKNESS)" if assessment.is_primary_weakness else ""
            lines.append(
                f"### {assessment.layer.value.title()} Layer "
                f"(risk: {assessment.risk_score:.2f}){primary} {status}"
            )
            lines.append("")

            ev = assessment.evidence
            lines.append(
                f"- **Attempts:** {ev.total_attempts} "
                f"({ev.success_count} succeeded)"
            )
            lines.append(
                f"- **Success Rate (smoothed):** {ev.smoothed_success_rate:.1%}"
            )
            ci_lo, ci_hi = ev.confidence_interval
            lines.append(f"- **95% CI:** [{ci_lo:.1%}, {ci_hi:.1%}]")
            lines.append(f"- **Evidence Quality:** {ev.evidence_quality:.2f}")

            if ev.caveats:
                lines.append("- **Caveats:**")
                for caveat in ev.caveats:
                    lines.append(f"  - {caveat}")

            if assessment.techniques_tested:
                lines.append(
                    f"- **Techniques Tested:** {', '.join(assessment.techniques_tested)}"
                )

            if assessment.recommendations:
                lines.append("- **Recommendations:**")
                for rec in assessment.recommendations:
                    lines.append(f"  - {rec}")

            lines.append("")

        # Comparability warnings
        if report.comparability_warnings:
            lines.append("## Comparability Warnings")
            lines.append("")
            for warning in report.comparability_warnings:
                lines.append(f"- {warning}")
            lines.append("")

        # Next steps
        if report.next_recommended_tests:
            lines.append("## Recommended Next Tests")
            lines.append("")
            for tid in report.next_recommended_tests:
                lines.append(f"- {tid}")
            lines.append("")

        return "\n".join(lines)

    def to_terminal(self, report: DefenderReport) -> str:
        """Render report for terminal output using Rich-compatible formatting."""
        try:
            from rich.console import Console
            from rich.panel import Panel
            from rich.table import Table

            console = Console(record=True, width=100)

            console.print(
                Panel(
                    f"[bold]{report.target_profile.name}[/bold]\n"
                    f"Campaign: {report.campaign_id}\n"
                    f"Target: {report.target_profile.target_type.value} "
                    f"({report.target_profile.access_level.value})",
                    title="Defender Report",
                )
            )

            if report.primary_weak_layer:
                console.print(
                    f"\n[bold red]Primary Weakness: "
                    f"{report.primary_weak_layer.value} layer[/bold red]\n"
                )

            table = Table(title="Layer Risk Assessment")
            table.add_column("Layer", style="cyan")
            table.add_column("Risk", justify="right")
            table.add_column("Attempts", justify="right")
            table.add_column("Success Rate", justify="right")
            table.add_column("Status")

            for a in report.layer_assessments:
                risk_style = (
                    "red" if a.risk_score > 0.5
                    else "yellow" if a.risk_score > 0.2
                    else "green"
                )
                status = (
                    "PRIMARY" if a.is_primary_weakness
                    else "INSUFFICIENT" if a.is_insufficient_evidence
                    else "OK"
                )
                table.add_row(
                    a.layer.value,
                    f"[{risk_style}]{a.risk_score:.2f}[/{risk_style}]",
                    str(a.evidence.total_attempts),
                    f"{a.evidence.smoothed_success_rate:.0%}",
                    status,
                )

            console.print(table)

            if report.comparability_warnings:
                console.print("\n[yellow]Comparability Warnings:[/yellow]")
                for w in report.comparability_warnings:
                    console.print(f"  - {w}")

            return console.export_text()

        except ImportError:
            return self.to_markdown(report)
