"""Durable, project-local persistence for Orren semantic runs.

The database is deliberately independent of generated applications.  It stores
Orren source snapshots, materialized SIR facts, realization metadata, and
provenance.  Flexible semantic payloads remain JSON while stable query keys
are ordinary SQLite columns.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .data_model import Dimension, SIRGraph

SCHEMA_VERSION = 1

_SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS projects (
    project_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    schema_version INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sources (
    source_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(project_id),
    path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(project_id, content_hash)
);
CREATE TABLE IF NOT EXISTS revisions (
    revision_id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id TEXT NOT NULL REFERENCES projects(project_id),
    source_id INTEGER NOT NULL REFERENCES sources(source_id),
    parent_revision_id INTEGER REFERENCES revisions(revision_id),
    source_hash TEXT NOT NULL,
    sir_hash TEXT NOT NULL,
    compiler_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS nodes (
    node_id TEXT NOT NULL,
    revision_id INTEGER NOT NULL REFERENCES revisions(revision_id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    name TEXT NOT NULL,
    kind TEXT NOT NULL,
    parent_id TEXT,
    PRIMARY KEY(revision_id, node_id),
    UNIQUE(revision_id, path)
);
CREATE TABLE IF NOT EXISTS dimension_payloads (
    payload_id INTEGER PRIMARY KEY AUTOINCREMENT,
    revision_id INTEGER NOT NULL,
    node_id TEXT NOT NULL,
    dimension TEXT NOT NULL,
    ordinal INTEGER NOT NULL,
    payload_json TEXT NOT NULL,
    source_span TEXT,
    FOREIGN KEY(revision_id, node_id) REFERENCES nodes(revision_id, node_id) ON DELETE CASCADE
);
CREATE TABLE IF NOT EXISTS realization_targets (
    target_id INTEGER PRIMARY KEY AUTOINCREMENT,
    revision_id INTEGER NOT NULL REFERENCES revisions(revision_id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    language TEXT NOT NULL,
    capabilities_json TEXT NOT NULL,
    degradation_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    revision_id INTEGER NOT NULL REFERENCES revisions(revision_id) ON DELETE CASCADE,
    target_id INTEGER REFERENCES realization_targets(target_id),
    path TEXT NOT NULL,
    language TEXT NOT NULL,
    content_hash TEXT,
    metadata_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS builds (
    build_id INTEGER PRIMARY KEY AUTOINCREMENT,
    revision_id INTEGER NOT NULL REFERENCES revisions(revision_id),
    target_id INTEGER,
    status TEXT NOT NULL,
    toolchain_json TEXT NOT NULL,
    log TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS edit_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    revision_id INTEGER NOT NULL REFERENCES revisions(revision_id),
    operation TEXT NOT NULL,
    path TEXT,
    dimension TEXT,
    old_json TEXT,
    new_json TEXT,
    rationale TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_nodes_path ON nodes(revision_id, path);
CREATE INDEX IF NOT EXISTS idx_payload_dimension ON dimension_payloads(revision_id, dimension);
CREATE INDEX IF NOT EXISTS idx_artifacts_hash ON artifacts(content_hash);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_default(value: Any) -> Any:
    if isinstance(value, (Dimension,)):
        return value.value
    if dataclasses.is_dataclass(value):
        return dataclasses.asdict(value)
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"not JSON serializable: {type(value).__name__}")


def _json(value: Any) -> str:
    return json.dumps(value, default=_json_default, sort_keys=True, separators=(",", ":"))


def graph_hash(graph: SIRGraph) -> str:
    return hashlib.sha256(graph.signature().encode("utf-8")).hexdigest()


class ProjectDatabase:
    """SQLite-backed Orren project store with explicit transaction boundaries."""

    def __init__(self, path: str | Path, project_name: str = "orren-project") -> None:
        self.path = Path(path)
        self.project_name = project_name
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.executescript(_SCHEMA)
        now = _now()
        self.connection.execute(
            "INSERT OR IGNORE INTO projects(project_id,name,schema_version,created_at,updated_at) VALUES(?,?,?,?,?)",
            (self.project_id, project_name, SCHEMA_VERSION, now, now),
        )
        self.connection.commit()

    @property
    def project_id(self) -> str:
        return hashlib.sha256(str(self.path.resolve()).encode()).hexdigest()[:24]

    def close(self) -> None:
        self.connection.close()

    def save_run(self, source_path: str, source: str, graph: SIRGraph, artifacts: list[Any], compiler_version: str) -> int:
        """Atomically persist a source snapshot, SIR materialization, and artifacts."""
        source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
        sir_hash = graph_hash(graph)
        now = _now()
        with self.connection:
            row = self.connection.execute(
                "SELECT source_id FROM sources WHERE project_id=? AND content_hash=?",
                (self.project_id, source_hash),
            ).fetchone()
            if row:
                source_id = row["source_id"]
            else:
                source_id = self.connection.execute(
                    "INSERT INTO sources(project_id,path,content_hash,content,created_at) VALUES(?,?,?,?,?)",
                    (self.project_id, source_path, source_hash, source, now),
                ).lastrowid
            parent = self.connection.execute(
                "SELECT revision_id FROM revisions WHERE project_id=? ORDER BY revision_id DESC LIMIT 1",
                (self.project_id,),
            ).fetchone()
            revision_id = self.connection.execute(
                "INSERT INTO revisions(project_id,source_id,parent_revision_id,source_hash,sir_hash,compiler_version,created_at) VALUES(?,?,?,?,?,?,?)",
                (self.project_id, source_id, parent["revision_id"] if parent else None, source_hash, sir_hash, compiler_version, now),
            ).lastrowid
            for node in graph.nodes:
                self.connection.execute(
                    "INSERT INTO nodes(node_id,revision_id,path,name,kind,parent_id) VALUES(?,?,?,?,?,?)",
                    (node.node_id, revision_id, node.path, node.name, node.kind, node.parent.node_id if node.parent else None),
                )
                for dim in Dimension:
                    for ordinal, payload in enumerate(node.dimensions.get(dim, [])):
                        self.connection.execute(
                            "INSERT INTO dimension_payloads(revision_id,node_id,dimension,ordinal,payload_json) VALUES(?,?,?,?,?)",
                            (revision_id, node.node_id, dim.value, ordinal, _json(payload)),
                        )
            target_ids: dict[str, int] = {}
            for target in graph.realization_targets:
                target_id = self.connection.execute(
                    "INSERT INTO realization_targets(revision_id,name,language,capabilities_json,degradation_json) VALUES(?,?,?,?,?)",
                    (revision_id, target.name, target.language, _json(target.capabilities), _json(target.degradation)),
                ).lastrowid
                target_ids[target.name] = target_id
            for artifact in artifacts:
                for output in artifact.output_files:
                    self.connection.execute(
                        "INSERT INTO artifacts(revision_id,target_id,path,language,content_hash,metadata_json) VALUES(?,?,?,?,?,?)",
                        (revision_id, target_ids.get(artifact.target_name), output.path, output.language, None, _json(artifact.to_dict())),
                    )
            self.connection.execute("UPDATE projects SET updated_at=? WHERE project_id=?", (now, self.project_id))
            self.connection.execute(
                "INSERT INTO edit_events(revision_id,operation,rationale,created_at) VALUES(?,?,?,?)",
                (revision_id, "realize", "materialize parsed source and SIR snapshot", now),
            )
        return int(revision_id)

    def latest_revision(self) -> Optional[sqlite3.Row]:
        return self.connection.execute(
            "SELECT revision_id, source_hash, sir_hash, compiler_version, created_at FROM revisions WHERE project_id=? ORDER BY revision_id DESC LIMIT 1",
            (self.project_id,),
        ).fetchone()

    def counts(self, revision_id: Optional[int] = None) -> dict[str, int]:
        revision = revision_id or (self.latest_revision()["revision_id"] if self.latest_revision() else None)
        if revision is None:
            return {"nodes": 0, "payloads": 0, "targets": 0, "artifacts": 0, "builds": 0, "events": 0}
        tables = {
            "nodes": "nodes",
            "payloads": "dimension_payloads",
            "targets": "realization_targets",
            "artifacts": "artifacts",
            "builds": "builds",
            "events": "edit_events",
        }
        return {
            name: int(self.connection.execute(f"SELECT COUNT(*) FROM {table} WHERE revision_id=?", (revision,)).fetchone()[0])
            for name, table in tables.items()
        }

    def record_build(self, revision_id: int, status: str, toolchain: dict[str, Any], log: str, target_id: Optional[int] = None) -> int:
        with self.connection:
            return int(self.connection.execute(
                "INSERT INTO builds(revision_id,target_id,status,toolchain_json,log,created_at) VALUES(?,?,?,?,?,?)",
                (revision_id, target_id, status, _json(toolchain), log, _now()),
            ).lastrowid)


__all__ = ["ProjectDatabase", "SCHEMA_VERSION", "graph_hash"]
