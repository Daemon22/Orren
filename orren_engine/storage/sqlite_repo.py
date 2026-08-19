"""SQLite-backed realization repository.

Concrete :class:`~orren_engine.storage.repository.AbstractRepository` backed by
SQLite.  This is Orren's *durable state boundary*: everything that must survive
a process restart — raw source, materialized SIR, equilibrium rules, targets,
diagnostics, edit history, artifacts, and build records — lives here.

Storage guarantees:

* **WAL journal mode** for concurrent read/write tolerance.
* **Foreign-key enforcement** on every connection (``PRAGMA foreign_keys = ON``).
* **Stable identifiers** derived from content (``sha256``) so re-materialising the
  same input yields identical rows; a separate ``runtime_uuid`` column
  preserves ephemeral correlation identifiers.
* **Atomicity**: every public mutation runs in a single transaction.
* **Immutability**: revisions are append-only; undo/redo is expressed by moving
  the project's working-head pointer (see :meth:`restore`).
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .repository import AbstractRepository, NodeRef, Payload, SourceSpan

try:  # Data-model bridge is optional so the package can be unit-tested alone.
    from ..data_model import Dimension, SIRGraph  # noqa: F401
    _HAS_DATA_MODEL = True
except Exception:  # pragma: no cover
    Dimension = None  # type: ignore[assignment]
    SIRGraph = None  # type: ignore[assignment]
    _HAS_DATA_MODEL = False

SCHEMA_VERSION = 1

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS projects(
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources(
    source_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    content BLOB NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(project_id, content_hash)
);
CREATE TABLE IF NOT EXISTS expressions(
    expression_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    source_span TEXT,
    raw_sections TEXT
);
CREATE TABLE IF NOT EXISTS revisions(
    revision_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    parent_revision_id TEXT REFERENCES revisions(revision_id) ON DELETE CASCADE,
    source_hash TEXT NOT NULL,
    sir_hash TEXT NOT NULL,
    config_hash TEXT NOT NULL DEFAULT '',
    compiler_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nodes(
    node_id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    parent_id TEXT REFERENCES nodes(node_id) ON DELETE SET NULL,
    runtime_uuid TEXT
);
CREATE TABLE IF NOT EXISTS dimension_payloads(
    payload_id TEXT PRIMARY KEY,
    revision_id TEXT NOT NULL,
    node_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
    dimension TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    aspect TEXT NOT NULL DEFAULT '',
    subject TEXT NOT NULL DEFAULT '',
    payload TEXT NOT NULL,
    source_span TEXT
);
CREATE TABLE IF NOT EXISTS equilibrium_rules(
    rule_id TEXT PRIMARY KEY,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    conditions TEXT NOT NULL,
    preserve TEXT NOT NULL,
    resolution TEXT
);
CREATE TABLE IF NOT EXISTS realization_targets(
    target_id TEXT PRIMARY KEY,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    language TEXT NOT NULL,
    capabilities TEXT NOT NULL,
    degradation TEXT NOT NULL,
    preservation_score REAL NOT NULL DEFAULT 1.0
);
CREATE TABLE IF NOT EXISTS diagnostics(
    diagnostic_id TEXT PRIMARY KEY,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE CASCADE,
    code TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    source_span TEXT
);
CREATE TABLE IF NOT EXISTS edit_events(
    event_id TEXT PRIMARY KEY,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE CASCADE,
    operation TEXT NOT NULL,
    path TEXT,
    dimension TEXT,
    old_json TEXT,
    new_json TEXT,
    rationale TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS artifacts(
    artifact_id TEXT PRIMARY KEY,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE CASCADE,
    target_id TEXT REFERENCES realization_targets(target_id) ON DELETE SET NULL,
    path TEXT NOT NULL,
    language TEXT NOT NULL,
    content_hash TEXT,
    storage_uri TEXT
);
CREATE TABLE IF NOT EXISTS builds(
    build_id TEXT PRIMARY KEY,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE CASCADE,
    target_id TEXT REFERENCES realization_targets(target_id) ON DELETE SET NULL,
    toolchain TEXT NOT NULL,
    status TEXT NOT NULL,
    log_uri TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS search_index(
    project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    key TEXT NOT NULL,
    value TEXT,
    node_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS project_heads(
    project_id TEXT PRIMARY KEY REFERENCES projects(project_id) ON DELETE CASCADE,
    revision_id TEXT NOT NULL REFERENCES revisions(revision_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_nodes_path ON nodes(revision_id, path);
CREATE INDEX IF NOT EXISTS idx_nodes_rev ON nodes(revision_id, node_id);
CREATE INDEX IF NOT EXISTS idx_payload_dim ON dimension_payloads(revision_id, dimension, aspect);
CREATE INDEX IF NOT EXISTS idx_sources_hash ON sources(project_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_targets_name ON realization_targets(revision_id, name);
CREATE INDEX IF NOT EXISTS idx_artifacts_path ON artifacts(revision_id, path);
CREATE INDEX IF NOT EXISTS idx_builds_status ON builds(revision_id, status);
CREATE INDEX IF NOT EXISTS idx_search ON search_index(project_id, kind, key);
CREATE INDEX IF NOT EXISTS idx_heads_rev ON project_heads(revision_id);
CREATE INDEX IF NOT EXISTS idx_dim_node ON dimension_payloads(node_id);
"""

# Pending forward migrations keyed by target schema version.  Empty until a
# schema bump is required; the hook exists so ``migrate`` is forward-compatible.
_MIGRATIONS: Dict[int, str] = {}


# ---------------------------------------------------------------------------
# Identifier + serialization helpers
# ---------------------------------------------------------------------------


def _stable_id(*parts: Any) -> str:
    """Derive a deterministic, content-based identifier.

    Args:
        *parts: Values joined with ``|`` and hashed with SHA-256.

    Returns:
        A 24-character hexadecimal stable identifier.
    """
    raw = "|".join("" if p is None else str(p) for p in parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]


def _runtime_uuid() -> str:
    """Generate an ephemeral correlation UUID.

    Returns:
        A random 12-character hexadecimal UUID (not stable across runs).
    """
    return uuid.uuid4().hex[:12]


def _json(value: Any) -> str:
    """Serialize ``value`` to canonical JSON (sorted keys).

    Args:
        value: Any JSON-serialisable object.

    Returns:
        A compact, key-stable JSON string.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string.

    Returns:
        The current timestamp in UTC.
    """
    return datetime.now(timezone.utc).isoformat()


def _span_to_json(span: Optional[SourceSpan]) -> Optional[str]:
    """Serialize a :class:`SourceSpan` to JSON, or ``None``.

    Args:
        span: The span to serialize.

    Returns:
        JSON string, or ``None`` when ``span`` is falsy.
    """
    if not span:
        return None
    return _json(span.to_tuple())


def _json_to_span(value: Optional[str]) -> Optional[SourceSpan]:
    """Deserialize a :class:`SourceSpan` from JSON, or ``None``.

    Args:
        value: JSON string produced by :func:`_span_to_json`.

    Returns:
        A :class:`SourceSpan`, or ``None`` when ``value`` is falsy.
    """
    if not value:
        return None
    data = json.loads(value)
    return SourceSpan.from_tuple(tuple(data))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Serializers for dataclass rules/targets supplied to put_graph
# ---------------------------------------------------------------------------


def _serialize_rule(rule: Any) -> Dict[str, Any]:
    """Serialize an :class:`EquilibriumRule` to a plain dict.

    Args:
        rule: An equilibrium-rule dataclass.

    Returns:
        A dictionary with name/conditions/preserve/resolution keys.
    """
    conditions: List[Dict[str, Any]] = []
    for cond in getattr(rule, "conditions", []) or []:
        if isinstance(cond, dict):
            conditions.append(cond)
        else:
            conditions.append({
                "dimension": getattr(cond, "dimension", ""),
                "predicate": getattr(cond, "predicate", ""),
            })
    preserve = list(getattr(rule, "preserve", []) or [])
    resolution = getattr(rule, "resolution", None)
    res_dict = None
    if resolution is not None:
        res_dict = {"text": getattr(resolution, "text", ""),
                    "bridge_to": getattr(resolution, "bridge_to", None)}
    return {
        "name": getattr(rule, "name", ""),
        "conditions": conditions,
        "preserve": preserve,
        "resolution": res_dict,
    }


def _serialize_target(target: Any) -> Dict[str, Any]:
    """Serialize a :class:`RealizationTarget` to a plain dict.

    Args:
        target: A realization-target dataclass.

    Returns:
        A dictionary with name/language/capabilities/degradation keys.
    """
    degradation: List[Dict[str, Any]] = []
    for entry in getattr(target, "degradation", []) or []:
        if isinstance(entry, dict):
            degradation.append(entry)
        else:
            degradation.append({
                "level": getattr(entry, "level", None),
                "dimension": getattr(entry, "dimension", ""),
                "aspect": getattr(entry, "aspect", ""),
                "mode": getattr(entry, "mode", "tolerate"),
            })
    return {
        "name": getattr(target, "name", ""),
        "language": getattr(target, "language", ""),
        "capabilities": list(getattr(target, "capabilities", []) or []),
        "degradation": degradation,
        "preservation_score": getattr(target, "preservation_score", 1.0),
    }


class SQLiteRepo(AbstractRepository):
    """SQLite realization repository.

    Implements the full :class:`AbstractRepository` contract on a single
    SQLite database file.  All writes occur inside explicit transactions.
    """

    def __init__(self, path: str, project_name: str = "orren-project",
                 schema_version: int = SCHEMA_VERSION) -> None:
        """Open (creating if necessary) the backing SQLite store.

        Args:
            path: Filesystem path to the SQLite database file.
            project_name: Name used when auto-creating the project.
            schema_version: Target schema version to open/migrate to.
        """
        self.path = path
        self.project_name = project_name
        self._sqlite3 = __import__("sqlite3")
        directory = os.path.dirname(os.path.abspath(path)) or "."
        os.makedirs(directory, exist_ok=True)
        self.connection = self._sqlite3.connect(str(path))
        self.connection.row_factory = self._sqlite3.Row
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA synchronous = NORMAL")
        self.connection.executescript(_SCHEMA)
        self.connection.commit()
        self.project_id = self.open_project(project_name, schema_version)

    # ------------------------------------------------------------------
    # Schema + lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def init(cls, path: str, name: str = "orren-project",
             schema_version: int = SCHEMA_VERSION) -> str:
        """Create an initialised project database and return its project id.

        Args:
            path: Database file path to initialise.
            name: Project name.
            schema_version: Schema version to initialise.

        Returns:
            The stable project identifier of the new database.
        """
        directory = os.path.dirname(os.path.abspath(path)) or "."
        os.makedirs(directory, exist_ok=True)
        sqlite3 = __import__("sqlite3")
        conn = sqlite3.connect(str(path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(_SCHEMA)
        conn.commit()
        project_id = _stable_id("project", name)
        now = _now()
        conn.execute(
            "INSERT OR IGNORE INTO projects(project_id,name,schema_version,created_at,updated_at) "
            "VALUES(?,?,?,?,?)",
            (project_id, name, schema_version, now, now),
        )
        conn.commit()
        conn.close()
        return project_id

    def migrate(self, schema_version: int) -> None:
        """Migrate the database schema to ``schema_version``.

        Args:
            schema_version: Target schema version (must be >= current).
        """
        current = self.connection.execute(
            "SELECT MAX(schema_version) FROM projects"
        ).fetchone()[0] or SCHEMA_VERSION
        with self.connection:
            for version in range(current + 1, schema_version + 1):
                ddl = _MIGRATIONS.get(version)
                if ddl:
                    self.connection.executescript(ddl)
                self.connection.execute(
                    "UPDATE projects SET schema_version = ?, updated_at = ? "
                    "WHERE project_id = ?",
                    (version, _now(), self.project_id),
                )

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self.connection.close()

    # ------------------------------------------------------------------
    # Project + revision lifecycle
    # ------------------------------------------------------------------

    def open_project(self, name: str, schema_version: int = SCHEMA_VERSION) -> str:
        """Open or create a project, returning its stable id.

        Args:
            name: Project name.
            schema_version: Target schema version.

        Returns:
            The stable project identifier.
        """
        project_id = _stable_id("project", name)
        now = _now()
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO projects(project_id,name,schema_version,created_at,updated_at) "
                "VALUES(?,?,?,?,?)",
                (project_id, name, schema_version, now, now),
            )
            self.connection.execute(
                "UPDATE projects SET updated_at=? WHERE project_id=?", (now, project_id),
            )
        return project_id

    def begin_revision(self, parent_id: Optional[str], source_hash: str,
                       sir_hash: str, config_hash: str = "",
                       compiler_version: str = "") -> str:
        """Create a new immutable revision beneath ``parent_id``.

        Args:
            parent_id: Stable id of the parent revision, or ``None``.
            source_hash: SHA-256 of the canonical source bytes.
            sir_hash: SHA-256 of the resolved SIR signature.
            config_hash: Optional configuration hash.
            compiler_version: Orren compiler version.

        Returns:
            The stable revision identifier.
        """
        revision_id = _stable_id("revision", self.project_id,
                                 parent_id or "", source_hash, sir_hash, config_hash)
        now = _now()
        with self.connection:
            self.connection.execute(
                "INSERT INTO revisions(revision_id,project_id,parent_revision_id,source_hash,"
                "sir_hash,config_hash,compiler_version,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (revision_id, self.project_id, parent_id, source_hash, sir_hash,
                 config_hash, compiler_version, now),
            )
            # Advance the durable working head to the new revision (redo by
            # pointer movement, never by inverting prior mutations).
            self.connection.execute(
                "INSERT INTO project_heads(project_id,revision_id) VALUES(?,?) "
                "ON CONFLICT(project_id) DO UPDATE SET revision_id=excluded.revision_id",
                (self.project_id, revision_id),
            )
        return revision_id

    @property
    def latest_revision(self) -> Optional[str]:
        """The stable id of the current working-head revision, if any.

        Returns:
            The working-head revision id, or ``None`` when none exists.
        """
        row = self.connection.execute(
            "SELECT revision_id FROM project_heads WHERE project_id=?",
            (self.project_id,),
        ).fetchone()
        return row["revision_id"] if row else None

    # ------------------------------------------------------------------
    # Sources + graph materialisation
    # ------------------------------------------------------------------

    def put_source(self, project_id: str, path: str, content: bytes,
                   content_hash: str) -> str:
        """Store a source blob immutably.

        Args:
            project_id: Owning project.
            path: Logical source path.
            content: Raw source bytes.
            content_hash: SHA-256 of ``content``.

        Returns:
            The stable source identifier.
        """
        source_id = _stable_id("source", project_id, path, content_hash)
        now = _now()
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO sources(source_id,project_id,path,content_hash,content,created_at) "
                "VALUES(?,?,?,?,?,?)",
                (source_id, project_id, path, content_hash,
                 self._sqlite3.Binary(content), now),
            )
        return source_id

    def put_graph(self, revision_id: str, nodes: List[NodeRef],
                  edges: List[Tuple[str, str]], rules: List[Any],
                  targets: List[Any]) -> None:
        """Persist a materialised SIR graph for a revision.

        Args:
            revision_id: Revision to materialise.
            nodes: Node references (parents must precede children by depth, or
                be inferable by path).
            edges: ``(parent_path, child_path)`` relationships.
            rules: Equilibrium rules (dataclass or dict form).
            targets: Realisation targets (dataclass or dict form).
        """
        node_ids: Dict[str, str] = {}
        ordered = sorted(nodes, key=lambda n: (n.path.count("."), n.path))
        with self.connection:
            for node in ordered:
                node_id = _stable_id(self.project_id, revision_id, node.path, node.kind)
                node_ids[node.path] = node_id
                parent_id: Optional[str] = None
                if node.parent_path:
                    parent_id = node_ids.get(node.parent_path)
                    if parent_id is None:
                        parent_id = _stable_id(self.project_id, revision_id,
                                               node.parent_path, "entity")
                self.connection.execute(
                    "INSERT OR REPLACE INTO nodes(node_id,project_id,revision_id,path,name,kind,parent_id,runtime_uuid) "
                    "VALUES(?,?,?,?,?,?,?,?)",
                    (node_id, self.project_id, revision_id, node.path, node.name,
                     node.kind, parent_id, node.runtime_uuid),
                )
                for dim, payloads in (node.dimensions or {}).items():
                    for ordinal, payload in enumerate(payloads):
                        aspect = ""
                        subject = ""
                        if isinstance(payload, dict):
                            aspect = str(payload.get("aspect", ""))
                            subject = str(payload.get("subject", ""))
                        payload_id = _stable_id("payload", revision_id, node_id, dim, ordinal)
                        self.connection.execute(
                            "INSERT OR REPLACE INTO dimension_payloads(payload_id,revision_id,node_id,dimension,"
                            "ordinal,aspect,subject,payload,source_span) VALUES(?,?,?,?,?,?,?,?,?)",
                            (payload_id, revision_id, node_id, dim, ordinal,
                             aspect, subject, _json(payload), None),
                        )
                        self.connection.execute(
                            "INSERT INTO search_index(project_id,kind,key,value,node_id) VALUES(?,?,?,?,?)",
                            (self.project_id, dim, "subject", subject or None, node_id),
                        )
            for parent_path, child_path in edges:
                child_id = node_ids.get(child_path)
                if not child_id:
                    continue
                parent_id = node_ids.get(parent_path) or _stable_id(
                    self.project_id, revision_id, parent_path, "entity"
                )
                self.connection.execute(
                    "UPDATE nodes SET parent_id=? WHERE node_id=?",
                    (parent_id, child_id),
                )
            self._store_rules(revision_id, rules)
            self._store_targets(revision_id, targets)

    def _store_rules(self, revision_id: str, rules: List[Any]) -> None:
        """Persist equilibrium rules for a revision.

        Args:
            revision_id: Owning revision.
            rules: Rules as dataclasses or dicts.
        """
        for rule in rules:
            data = rule if isinstance(rule, dict) else _serialize_rule(rule)
            rule_id = _stable_id("rule", revision_id, data.get("name", ""))
            self.connection.execute(
                "INSERT OR REPLACE INTO equilibrium_rules(rule_id,revision_id,name,conditions,preserve,resolution) "
                "VALUES(?,?,?,?,?,?)",
                (rule_id, revision_id, data.get("name", ""),
                 _json(data.get("conditions", [])),
                 _json(data.get("preserve", [])),
                 _json(data.get("resolution"))),
            )

    def _store_targets(self, revision_id: str, targets: List[Any]) -> None:
        """Persist realization targets for a revision.

        Args:
            revision_id: Owning revision.
            targets: Targets as dataclasses or dicts.
        """
        for target in targets:
            data = target if isinstance(target, dict) else _serialize_target(target)
            target_id = _stable_id("target", revision_id,
                                   data.get("name", ""), data.get("language", ""))
            self.connection.execute(
                "INSERT OR REPLACE INTO realization_targets(target_id,revision_id,name,language,capabilities,degradation,preservation_score) "
                "VALUES(?,?,?,?,?,?,?)",
                (target_id, revision_id, data.get("name", ""), data.get("language", ""),
                 _json(data.get("capabilities", [])),
                 _json(data.get("degradation", [])),
                 float(data.get("preservation_score", 1.0))),
            )

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_node(self, revision_id: str, path: str) -> Optional[NodeRef]:
        """Fetch a single node by path within a revision.

        Args:
            revision_id: Revision to read from.
            path: Dot-separated node path.

        Returns:
            The reconstructed :class:`NodeRef`, or ``None``.
        """
        row = self.connection.execute(
            "SELECT node_id,parent_id,name,kind,runtime_uuid FROM nodes "
            "WHERE revision_id=? AND path=?", (revision_id, path),
        ).fetchone()
        if row is None:
            return None
        payloads = self.connection.execute(
            "SELECT dimension,ordinal,aspect,subject,payload FROM dimension_payloads "
            "WHERE node_id=? ORDER BY dimension,ordinal",
            (row["node_id"],),
        ).fetchall()
        dimensions: Dict[str, List[Any]] = {}
        for pl in payloads:
            dimensions.setdefault(pl["dimension"], []).append(json.loads(pl["payload"]))
        return NodeRef(
            path=path,
            name=row["name"],
            kind=row["kind"],
            stable_id=row["node_id"],
            runtime_uuid=row["runtime_uuid"] or "",
            parent_path=row["parent_id"],
            dimensions=dimensions,
        )

    def query_dimension(self, revision_id: str, dimension: str,
                        aspect: Optional[str] = None,
                        subject: Optional[str] = None) -> List[Payload]:
        """Query dimension payloads attached to a revision's nodes.

        Args:
            revision_id: Revision to query.
            dimension: Dimension name to filter on.
            aspect: Optional aspect sub-filter.
            subject: Optional subject sub-filter.

        Returns:
            A list of matching :class:`Payload` values.
        """
        sql = ("SELECT node_id,dimension,ordinal,aspect,subject,payload "
               "FROM dimension_payloads WHERE node_id IN "
               "(SELECT node_id FROM nodes WHERE revision_id=?) AND dimension=?")
        params: List[Any] = [revision_id, dimension]
        if aspect is not None:
            sql += " AND aspect=?"
            params.append(aspect)
        if subject is not None:
            sql += " AND subject=?"
            params.append(subject)
        sql += " ORDER BY node_id,ordinal"
        results: List[Payload] = []
        for row in self.connection.execute(sql, params).fetchall():
            results.append(Payload(
                dimension=row["dimension"],
                aspect=row["aspect"],
                subject=row["subject"],
                ordinal=row["ordinal"],
                payload=json.loads(row["payload"]),
                source_span=None,
            ))
        return results

    # ------------------------------------------------------------------
    # Edits + artifacts + builds
    # ------------------------------------------------------------------

    def append_edit(self, revision_id: str, operation: str, path: Optional[str],
                    dimension: Optional[str], old: Any, new: Any,
                    rationale: str) -> str:
        """Record a semantic edit event.

        Args:
            revision_id: Revision the edit applies to.
            operation: Edit operation code.
            path: Target path, if any.
            dimension: Target dimension, if any.
            old: Pre-edit value.
            new: Post-edit value.
            rationale: Human-readable rationale.

        Returns:
            The stable edit-event identifier.
        """
        event_id = _stable_id("event", revision_id, operation, path or "", dimension or "")
        now = _now()
        with self.connection:
            self.connection.execute(
                "INSERT INTO edit_events(event_id,revision_id,operation,path,dimension,old_json,new_json,rationale,created_at) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (event_id, revision_id, operation, path, dimension,
                 _json(old) if old is not None else None,
                 _json(new) if new is not None else None,
                 rationale, now),
            )
        return event_id

    def store_artifact(self, revision_id: str, target_id: str, path: str,
                       language: str, content_hash: str, storage_uri: str) -> str:
        """Register a generated artifact.

        Args:
            revision_id: Revision the artifact came from.
            target_id: Target the artifact belongs to.
            path: Artifact path within the target namespace.
            language: Artifact language.
            content_hash: SHA-256 of the artifact bytes.
            storage_uri: Opaque storage reference.

        Returns:
            The stable artifact identifier.
        """
        artifact_id = _stable_id("artifact", revision_id, target_id, path,
                                 language, content_hash)
        with self.connection:
            self.connection.execute(
                "INSERT OR REPLACE INTO artifacts(artifact_id,revision_id,target_id,path,language,content_hash,storage_uri) "
                "VALUES(?,?,?,?,?,?,?)",
                (artifact_id, revision_id, target_id, path, language, content_hash, storage_uri),
            )
        return artifact_id

    def record_build(self, revision_id: str, target_id: str, toolchain: Any,
                     status: str, log_uri: str) -> str:
        """Record a backend build result.

        Args:
            revision_id: Revision the build targeted.
            target_id: Target the build produced.
            toolchain: JSON-serialisable toolchain descriptor.
            status: Build status.
            log_uri: Opaque reference to the build log.

        Returns:
            The stable build identifier.
        """
        build_id = _stable_id("build", revision_id, target_id, status, _json(toolchain))
        now = _now()
        with self.connection:
            self.connection.execute(
                "INSERT INTO builds(build_id,revision_id,target_id,toolchain,status,log_uri,created_at) "
                "VALUES(?,?,?,?,?,?,?)",
                (build_id, revision_id, target_id, _json(toolchain), status, log_uri, now),
            )
        return build_id

    # ------------------------------------------------------------------
    # Snapshot / restore / gc
    # ------------------------------------------------------------------

    def _snapshot_nodes(self, revision_id: str) -> List[Dict[str, Any]]:
        """Rebuild the node list (with dimension payloads) for a snapshot.

        Args:
            revision_id: Revision to snapshot.

        Returns:
            A list of node dictionaries with grouped dimension payloads.
        """
        nodes = self.connection.execute(
            "SELECT node_id,path,name,kind,parent_id,runtime_uuid FROM nodes "
            "WHERE revision_id=? ORDER BY path", (revision_id,)).fetchall()
        payloads = self.connection.execute(
            "SELECT node_id,dimension,ordinal,aspect,subject,payload FROM dimension_payloads "
            "WHERE revision_id=? ORDER BY node_id,dimension,ordinal", (revision_id,)).fetchall()
        grouped: Dict[str, Dict[str, List[Any]]] = {}
        for p in payloads:
            grouped.setdefault(p["node_id"], {}).setdefault(p["dimension"], []).append(
                json.loads(p["payload"]))
        return [
            {
                "node_id": n["node_id"],
                "path": n["path"],
                "name": n["name"],
                "kind": n["kind"],
                "parent_id": n["parent_id"],
                "runtime_uuid": n["runtime_uuid"],
                "dimensions": grouped.get(n["node_id"], {}),
            }
            for n in nodes
        ]

    def snapshot(self, revision_id: str) -> bytes:
        """Produce a deterministic byte snapshot of a revision.

        The snapshot is canonical JSON (sorted keys, stable ordering) and
        contains every table row belonging to the revision, so two calls for
        the same revision id produce byte-identical output.

        Args:
            revision_id: Revision to snapshot.

        Returns:
            Canonical bytes representing the full revision.
        """
        rev = self.connection.execute(
            "SELECT project_id,parent_revision_id,source_hash,sir_hash,config_hash,"
            "compiler_version,created_at FROM revisions WHERE revision_id=?",
            (revision_id,),
        ).fetchone()
        if rev is None:
            raise KeyError(f"unknown revision: {revision_id}")
        project_id = rev["project_id"]
        doc = {
            "schema_version": SCHEMA_VERSION,
            "revision": {
                "revision_id": revision_id,
                "project_id": project_id,
                "parent_revision_id": rev["parent_revision_id"],
                "source_hash": rev["source_hash"],
                "sir_hash": rev["sir_hash"],
                "config_hash": rev["config_hash"],
                "compiler_version": rev["compiler_version"],
                "created_at": rev["created_at"],
            },
            "sources": [
                {"source_id": r["source_id"], "path": r["path"],
                 "content_hash": r["content_hash"]}
                for r in self.connection.execute(
                    "SELECT source_id,path,content_hash FROM sources WHERE project_id=? ORDER BY path",
                    (project_id,)).fetchall()
            ],
            "nodes": self._snapshot_nodes(revision_id),
            "rules": [dict(r) for r in self.connection.execute(
                "SELECT rule_id,name,conditions,preserve,resolution FROM equilibrium_rules "
                "WHERE revision_id=? ORDER BY name", (revision_id,)).fetchall()],
            "targets": [
                {"target_id": r["target_id"], "name": r["name"],
                 "language": r["language"],
                 "capabilities": json.loads(r["capabilities"]),
                 "degradation": json.loads(r["degradation"]),
                 "preservation_score": r["preservation_score"]}
                for r in self.connection.execute(
                    "SELECT target_id,name,language,capabilities,degradation,preservation_score "
                    "FROM realization_targets WHERE revision_id=? ORDER BY name",
                    (revision_id,)).fetchall()
            ],
            "diagnostics": [dict(r) for r in self.connection.execute(
                "SELECT diagnostic_id,code,severity,message,source_span FROM diagnostics "
                "WHERE revision_id=? ORDER BY code", (revision_id,)).fetchall()],
            "edits": [dict(r) for r in self.connection.execute(
                "SELECT event_id,operation,path,dimension,old_json,new_json,rationale,created_at "
                "FROM edit_events WHERE revision_id=? ORDER BY event_id",
                (revision_id,)).fetchall()],
            "artifacts": [dict(r) for r in self.connection.execute(
                "SELECT artifact_id,target_id,path,language,content_hash,storage_uri "
                "FROM artifacts WHERE revision_id=? ORDER BY path", (revision_id,)).fetchall()],
            "builds": [
                {"build_id": r["build_id"], "target_id": r["target_id"],
                 "toolchain": json.loads(r["toolchain"]),
                 "status": r["status"], "log_uri": r["log_uri"],
                 "created_at": r["created_at"]}
                for r in self.connection.execute(
                    "SELECT build_id,target_id,toolchain,status,log_uri,created_at "
                    "FROM builds WHERE revision_id=? ORDER BY build_id",
                    (revision_id,)).fetchall()
            ],
        }
        return _json(doc).encode("utf-8")

    def restore(self, project_id: str, revision_id: str) -> None:
        """Move the working head to ``revision_id`` (redo/undo by pointer).

        Restoration never deletes rows; it advances the project's working-head
        pointer, implementing undo/redo without inverting operations.

        Args:
            project_id: Project to operate on.
            revision_id: Revision to restore to.
        """
        with self.connection:
            exists = self.connection.execute(
                "SELECT 1 FROM revisions WHERE revision_id=? AND project_id=?",
                (revision_id, project_id),
            ).fetchone()
            if exists is None:
                raise KeyError(f"revision {revision_id} not found in project {project_id}")
            self.connection.execute(
                "INSERT INTO project_heads(project_id,revision_id) VALUES(?,?) "
                "ON CONFLICT(project_id) DO UPDATE SET revision_id=excluded.revision_id",
                (project_id, revision_id),
            )

    def gc(self, dry_run: bool = True) -> Dict[str, int]:
        """Garbage-collect rows unreachable from any revision.

        Removes source blobs, artifacts, and builds that have no parent
        revision.  Revisions themselves are immutable and are never deleted.

        Args:
            dry_run: When ``True``, only report what would be removed.

        Returns:
            A summary of removed (or removable) row counts keyed by type.
        """
        summary: Dict[str, int] = {
            "orphan_sources": 0,
            "orphan_artifacts": 0,
            "orphan_builds": 0,
        }
        with self.connection:
            for table, label in (("sources", "orphan_sources"),
                                 ("artifacts", "orphan_artifacts"),
                                 ("builds", "orphan_builds")):
                id_col = "source_id" if table == "sources" else f"{table[:-1]}_id"
                # Sources are referenced by revision.source_hash == source.content_hash.
                if table == "sources":
                    orphans = self.connection.execute(
                        "SELECT source_id FROM sources s "
                        "WHERE NOT EXISTS (SELECT 1 FROM revisions r WHERE r.source_hash = s.content_hash)"
                    ).fetchall()
                else:
                    orphans = self.connection.execute(
                        f"SELECT {id_col} FROM {table} t "
                        f"WHERE t.revision_id IS NULL OR "
                        f"NOT EXISTS (SELECT 1 FROM revisions r WHERE r.revision_id = t.revision_id)"
                    ).fetchall()
                summary[label] = len(orphans)
                if not dry_run:
                    for (rid,) in orphans:
                        self.connection.execute(f"DELETE FROM {table} WHERE {id_col}=?", (rid,))
        return summary

    # ------------------------------------------------------------------
    # SIRGraph bridge (convenience, not part of the abstract contract)
    # ------------------------------------------------------------------

    def compute_target_id(self, revision_id: str, name: str, language: str) -> str:
        """Compute the stable target id for a declared target.

        Lets callers reference targets they registered via :meth:`put_graph`
        (whose stable id is derived from ``(revision, name, language)``) when
        recording artifacts or builds, without a round-trip query.

        Args:
            revision_id: Owning revision.
            name: Target name.
            language: Target language.

        Returns:
            The stable target identifier.
        """
        return _stable_id("target", revision_id, name, language)

    def put_sir_graph(self, revision_id: str, graph: Any) -> None:
        """Materialise an :class:`~orren_engine.data_model.SIRGraph`.

        Convenience wrapper converting SIR nodes/edges, equilibrium rules and
        realization targets into the repository's node/payload form.

        Args:
            revision_id: Revision to materialise.
            graph: An :class:`SIRGraph`-shaped object.
        """
        if not _HAS_DATA_MODEL or graph is None:
            return
        dimension_enum = Dimension if Dimension is not None else ()
        nodes = [
            NodeRef(
                path=node.path,
                name=node.name,
                kind=node.kind,
                stable_id=_stable_id(self.project_id, revision_id, node.path, node.kind),
                runtime_uuid=getattr(node, "node_id", "") or _runtime_uuid(),
                parent_path=node.parent.path if getattr(node, "parent", None) else None,
                dimensions={
                    dim.value: list(node.dimensions.get(dim, []) or [])
                    for dim in dimension_enum
                },
            )
            for node in graph.nodes
        ]
        edges = [
            (getattr(node, "parent").path, node.path)
            for node in graph.nodes
            if getattr(node, "parent", None)
        ]
        self.put_graph(revision_id, nodes, edges,
                       list(getattr(graph, "equilibrium_rules", [])),
                       list(getattr(graph, "realization_targets", [])))


__all__ = ["SCHEMA_VERSION", "SQLiteRepo"]
