"""Technique registry — loads catalog, queries and filters techniques."""

from __future__ import annotations

from pathlib import Path

import yaml

from adversarypilot.models.enums import AccessLevel, Domain, Goal, Phase, Surface, TargetType
from adversarypilot.models.technique import AtlasReference, AttackTechnique, ComplianceReference

_DEFAULT_CATALOG = Path(__file__).parent / "catalog.yaml"


class TechniqueRegistry:
    """Load, store, and query attack techniques from catalog YAML files."""

    def __init__(self) -> None:
        self._techniques: dict[str, AttackTechnique] = {}

    def load_catalog(self, path: Path | None = None) -> None:
        """Load techniques from a YAML catalog file."""
        path = path or _DEFAULT_CATALOG
        with open(path) as f:
            data = yaml.safe_load(f)

        for entry in data.get("techniques", []):
            atlas_refs = [
                AtlasReference(**ref) for ref in entry.pop("atlas_refs", [])
            ]
            compliance_refs = [
                ComplianceReference(**ref) for ref in entry.pop("compliance_refs", [])
            ]
            technique = AttackTechnique(
                atlas_refs=atlas_refs, compliance_refs=compliance_refs, **entry
            )
            self._techniques[technique.id] = technique

    def get(self, technique_id: str) -> AttackTechnique | None:
        """Get a technique by ID."""
        return self._techniques.get(technique_id)

    def get_all(self) -> list[AttackTechnique]:
        """Return all registered techniques."""
        return list(self._techniques.values())

    def filter(
        self,
        *,
        domain: Domain | None = None,
        phase: Phase | None = None,
        surface: Surface | None = None,
        access_level: AccessLevel | None = None,
        goal: Goal | None = None,
        target_type: TargetType | None = None,
        tool: str | None = None,
        framework: str | None = None,
    ) -> list[AttackTechnique]:
        """Filter techniques by any combination of taxonomy axes."""
        results = self.get_all()

        if domain is not None:
            results = [t for t in results if t.domain == domain]
        if phase is not None:
            results = [t for t in results if t.phase == phase]
        if surface is not None:
            results = [t for t in results if t.surface == surface]
        if access_level is not None:
            results = [t for t in results if t.access_required == access_level]
        if goal is not None:
            results = [t for t in results if goal in t.goals_supported]
        if target_type is not None:
            results = [t for t in results if target_type in t.target_types]
        if tool is not None:
            results = [t for t in results if tool in t.tool_support]
        if framework is not None:
            results = [
                t for t in results
                if any(ref.framework == framework for ref in t.compliance_refs)
            ]

        return results

    def __len__(self) -> int:
        return len(self._techniques)

    def __contains__(self, technique_id: str) -> bool:
        return technique_id in self._techniques
