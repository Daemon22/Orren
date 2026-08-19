"""
Orren Engine — Orchestrator
===========================

End-to-end pipeline:

    .orn FILE
        │
        ▼
    CoParser           — 1 file → N expressions
        │
        ▼
    SIRBuilder         — expressions → SIR graph
        │
        ▼
    EquilibriumResolver — conflict detection + resolution
        │
        ▼
    RealizationCoordinator — SIR → realization artifacts
        │
        ▼
    SemanticEditor (optional) — path-based edits with undo/redo
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .data_model import (
    RealizationArtifact,
    SIRGraph,
)
from .database import ProjectDatabase
from .equilibrium_resolver import EquilibriumReport, EquilibriumResolver
from .parser import CoParser
from .realization_coordinator import RealizationCoordinator
from .semantic_editor import SemanticEditor
from .sir_builder import SIRBuilder


@dataclass
class EngineResult:
    """The full output of one engine run."""

    expressions_count: int = 0
    sir_node_count: int = 0
    equilibrium_outcomes: int = 0
    unresolved_conflicts: int = 0
    artifacts: List[RealizationArtifact] = field(default_factory=list)
    graph: Optional[SIRGraph] = None
    equilibrium_report: Optional[EquilibriumReport] = None
    revision_id: Optional[int] = None

    def summary(self) -> str:
        lines = [
            f"Expressions parsed: {self.expressions_count}",
            f"SIR nodes built:    {self.sir_node_count}",
            f"Equilibrium rules fired: {self.equilibrium_outcomes}",
            f"Unresolved conflicts:    {self.unresolved_conflicts}",
            f"Realization artifacts:   {len(self.artifacts)}",
        ]
        return "\n".join(lines)


class Engine:
    """Main orchestrator. Reusable across multiple .orn sources."""

    def __init__(self, db_path: Optional[str] = None, project_name: str = "orren-project") -> None:
        self.parser = CoParser()
        self.builder = SIRBuilder()
        self.resolver = EquilibriumResolver()
        self.coordinator = RealizationCoordinator()
        self._graph: Optional[SIRGraph] = None
        self._editor: Optional[SemanticEditor] = None
        self.database = ProjectDatabase(db_path, project_name) if db_path else None

    def run(self, source: str) -> EngineResult:
        """Run the full pipeline on one .orn source string."""
        expressions = self.parser.parse(source)
        graph = self.builder.build(expressions)
        report = self.resolver.resolve(graph)
        artifacts = self.coordinator.coordinate(graph)
        self._graph = graph
        self._editor = None  # invalidate previous editor
        revision_id = None
        if self.database is not None:
            from . import __version__
            revision_id = self.database.save_run("<memory>", source, graph, artifacts, __version__)
        return EngineResult(
            expressions_count=len(expressions),
            sir_node_count=len(graph.nodes),
            equilibrium_outcomes=len(report.outcomes),
            unresolved_conflicts=len(report.unresolved_conflicts),
            artifacts=artifacts,
            graph=graph,
            equilibrium_report=report,
            revision_id=revision_id,
        )

    def editor(self) -> SemanticEditor:
        """Return a SemanticEditor bound to the last-built graph.

        Lazily created so a single Engine can run, edit, re-coordinate
        without re-parsing.
        """
        if self._graph is None:
            raise RuntimeError("Engine.run() must be called before editor()")
        if self._editor is None:
            self._editor = SemanticEditor(self._graph)
        return self._editor

    def re_coordinate(self) -> List[RealizationArtifact]:
        """Re-run realization after edits. Does NOT re-parse or re-resolve
        equilibrium — only the coordinator runs."""
        if self._graph is None:
            raise RuntimeError("Engine.run() must be called before re_coordinate()")
        return self.coordinator.coordinate(self._graph)


__all__ = ["Engine", "EngineResult"]
