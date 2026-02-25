"""Abstract base classes for tool importers and drivers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from adversarypilot.models.results import AttemptResult, EvaluationResult


class AbstractImporter(ABC):
    """Base class for importing results from external tools."""

    @abstractmethod
    def import_file(
        self, path: Path
    ) -> list[tuple[AttemptResult, EvaluationResult]]:
        """Parse an external tool's output file into AdversaryPilot result pairs."""
        ...

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Name of the external tool this importer handles."""
        ...


class AbstractDriver(ABC):
    """Base class for driving external tools (V2 — interface only)."""

    @abstractmethod
    def execute(
        self, technique_id: str, config: dict
    ) -> list[tuple[AttemptResult, EvaluationResult]]:
        """Execute a technique using the external tool and return results."""
        ...

    @property
    @abstractmethod
    def tool_name(self) -> str:
        """Name of the external tool this driver controls."""
        ...
