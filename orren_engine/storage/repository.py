"""Semantic repository interface for Orren's durable state boundary.

This module defines :class:`AbstractRepository`, the backend-neutral contract
that every durable Orren store must implement.  The repository is the *single
source of truth* for a project's provenance: raw source, the resolved SIR
graph, equilibrium rules, realization targets, diagnostics, edit history,
generated artifacts, and build records.

The default concrete implementation lives in :mod:`orren_engine.storage.sqlite_repo`
and is backed by SQLite (WAL mode, foreign-key enforcement).  Callers never
touch SQL directly; they depend only on this abstract interface, which keeps
the engine, the CLI, and the conformance harness decoupled from storage
particulars.

Design rules enforced here:

* **Stable IDs.**  Entity identifiers are derived deterministically from
  ``(project_id, revision_id, path, kind)`` so that re-materializing the same
  input yields byte-identical rows.  A separately-generated runtime UUID is
  retained for transient correlation but is *never* used as a stable key.
* **Atomicity.**  Every multi-table operation is a single transaction.
* **Immutability of revisions.**  A revision is append-only; undo/redo is
  modelled by moving the *working head* rather than by inverting edits.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Value objects exchanged across the storage boundary
# ---------------------------------------------------------------------------

@dataclass
class SourceSpan:
    """A source-code provenance span.

    Attributes:
        line: 1-based line number in the originating source file.
        column: 1-based column number of the first character.
        offset: 0-based byte offset from the start of the source.
        length: Number of bytes covered by the span.
    """

    line: int = 0
    column: int = 0
    offset: int = 0
    length: int = 0

    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Return the span as a ``(line, column, offset, length)`` tuple.

        Returns:
            The four coordinate components in canonical order.
        """
        return (self.line, self.column, self.offset, self.length)

    @classmethod
    def from_tuple(cls, value: Tuple[int, int, int, int]) -> "SourceSpan":
        """Construct a span from a ``(line, column, offset, length)`` tuple.

        Args:
            value: A 4-tuple of integer coordinates.

        Returns:
            A :class:`SourceSpan` with the coordinates unpacked.
        """
        return cls(*value)


@dataclass
class Payload:
    """A single dimension payload resolved onto a node.

    Attributes:
        dimension: The dimension name (e.g. ``"cognitive"``).
        aspect: Sub-key within the dimension (may be empty).
        subject: The payload's owner subject, if any.
        ordinal: Position of the payload within its dimension.
        payload: The JSON-decoded payload document.
        source_span: Provenance span of the originating source.
    """

    dimension: str
    aspect: str
    subject: str
    ordinal: int
    payload: Any
    source_span: Optional[SourceSpan] = None


@dataclass
class NodeRef:
    """A lightweight, cycle-free reference to a reconstructed SIR node.

    Attributes:
        path: Dot-separated node path.
        name: Human-readable node name.
        kind: Node kind (``"entity"``, ``"subsystem"``, ``"equilibrium"``,
            ``"root"``).
        stable_id: Reproducible identifier derived from
            ``(project, revision, path, kind)``.
        runtime_uuid: Ephemeral UUID retained for correlation (not stable).
        parent_path: Path of the parent node, or ``None`` for roots.
        dimensions: Mapping of dimension name to its serialized payload list.
    """

    path: str
    name: str
    kind: str
    stable_id: str
    runtime_uuid: str
    parent_path: Optional[str] = None
    dimensions: Any = field(default_factory=dict)


class AbstractRepository(ABC):
    """Backend-neutral contract for durable Orren state.

    Concrete stores implement these methods against a particular engine
    (SQLite, in-memory test doubles, etc.).  All mutating methods run inside
    an atomic transaction and return stable identifiers.
    """

    @abstractmethod
    def open_project(self, name: str, schema_version: int = 1) -> str:
        """Open (or create) a project, returning its stable project id.

        Args:
            name: Human-readable project name.
            schema_version: Target schema version to migrate to.

        Returns:
              The project's stable identifier.
        """

    @abstractmethod
    def begin_revision(
        self,
        parent_id: Optional[str],
        source_hash: str,
        sir_hash: str,
        config_hash: str = "",
        compiler_version: str = "",
    ) -> str:
        """Start a new immutable revision beneath a parent revision.

        Args:
            parent_id: Stable id of the parent revision, or ``None`` for a
                root revision.
            source_hash: SHA-256 of the canonical source bytes.
            sir_hash: SHA-256 of the resolved SIR signature.
            config_hash: Optional hash of resolution configuration.
            compiler_version: Orren compiler version that produced the revision.

        Returns:
            The stable id of the newly created revision.
        """

    @abstractmethod
    def put_source(
        self,
        project_id: str,
        path: str,
        content: bytes,
        content_hash: str,
    ) -> str:
        """Store an immutable source blob, returning its source id.

        Args:
            project_id: Project the source belongs to.
            path: Logical path of the source file.
            content: Raw source bytes.
            content_hash: SHA-256 of ``content``.

        Returns:
            The stable source identifier.
        """

    @abstractmethod
    def put_graph(
        self,
        revision_id: str,
        nodes: List[NodeRef],
        edges: List[Tuple[str, str]],
        rules: List[Any],
        targets: List[Any],
    ) -> None:
        """Persist the materialised SIR graph for a revision.

        Args:
            revision_id: The revision being materialised.
            nodes: All node references in the graph.
            edges: ``(parent_path, child_path)`` relationships.
            rules: Equilibrium rules attached to the revision.
            targets: Realization targets attached to the revision.
        """

    @abstractmethod
    def get_node(self, revision_id: str, path: str) -> Optional[NodeRef]:
        """Fetch a single node by path within a revision.

        Args:
            revision_id: Revision to read from.
            path: Dot-separated node path.

        Returns:
            The matching :class:`NodeRef`, or ``None`` if absent.
        """

    @abstractmethod
    def query_dimension(
        self,
        revision_id: str,
        dimension: str,
        aspect: Optional[str] = None,
        subject: Optional[str] = None,
    ) -> List[Payload]:
        """Query dimension payloads attached to a revision's nodes.

        Args:
            revision_id: Revision to query.
            dimension: Dimension name to filter on.
            aspect: Optional aspect sub-filter.
            subject: Optional subject sub-filter.

        Returns:
            A list of matching :class:`Payload` values.
        """

    @abstractmethod
    def append_edit(
        self,
        revision_id: str,
        operation: str,
        path: Optional[str],
        dimension: Optional[str],
        old: Any,
        new: Any,
        rationale: str,
    ) -> str:
        """Record a semantic edit event against a revision.

        Args:
            revision_id: Revision the edit applies to.
            operation: Edit operation code (``"add"``, ``"modify"``, ...).
            path: Target path of the edit, if any.
            dimension: Target dimension, if any.
            old: Pre-edit value (JSON-serialisable).
            new: Post-edit value (JSON-serialisable).
            rationale: Human-readable reason for the edit.

        Returns:
            The stable id of the recorded edit event.
        """

    @abstractmethod
    def store_artifact(
        self,
        revision_id: str,
        target_id: str,
        path: str,
        language: str,
        content_hash: str,
        storage_uri: str,
    ) -> str:
        """Register a generated artifact for a target.

        Args:
            revision_id: Revision the artifact was produced from.
            target_id: Realization target the artifact belongs to.
            path: Artifact path within the target's output namespace.
            language: Artifact language (e.g. ``"rust"``).
            content_hash: SHA-256 of the artifact bytes.
            storage_uri: Opaque storage location reference.

        Returns:
            The stable artifact identifier.
        """

    @abstractmethod
    def record_build(
        self,
        revision_id: str,
        target_id: str,
        toolchain: Any,
        status: str,
        log_uri: str,
    ) -> str:
        """Record a backend build result.

        Args:
            revision_id: Revision the build was invoked against.
            target_id: Target the build produced.
            toolchain: JSON-serialisable toolchain descriptor.
            status: Build status (``"PASS"``, ``"FAIL"``, ``"SKIP"``,
                ``"DEGRADED"``).
            log_uri: Opaque reference to the build log.

        Returns:
            The stable build identifier.
        """

    @abstractmethod
    def snapshot(self, revision_id: str) -> bytes:
        """Produce a deterministic byte snapshot of an entire revision.

        The snapshot is canonical (sorted keys, stable ordering, no volatile
        timestamps) so that two calls for the same revision produce
        byte-identical output.

        Args:
            revision_id: Revision to snapshot.

        Returns:
            Canonical bytes representing the full revision.
        """

    @abstractmethod
    def restore(self, project_id: str, revision_id: str) -> None:
        """Mark a revision as the durable working head (undo/redo semantics).

        Per the fail-closed / immutability rules, restoration never mutates
        stored rows — it advances the project's working-head pointer.

        Args:
            project_id: Project to operate on.
            revision_id: Revision to restore to.
        """

    @abstractmethod
    def migrate(self, schema_version: int) -> None:
        """Migrate the store's schema to ``schema_version``.

        Args:
            schema_version: Target schema version.
        """


__all__ = [
    "SourceSpan",
    "Payload",
    "NodeRef",
    "AbstractRepository",
]
