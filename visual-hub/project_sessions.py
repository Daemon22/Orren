"""Durable, isolated project sessions for the Visual Hub API.

Each Studio project receives its own SQLite database file and a replayable,
idempotent command log. The live SIR graph remains owned by RuntimeSession;
the command log reconstructs it after a process restart while ProjectDatabase
stores immutable materialized revisions.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from threading import RLock
from typing import Any, Callable


class ProjectRevisionConflict(Exception):
    def __init__(self, current_revision: int) -> None:
        super().__init__("The semantic project changed since it was read.")
        self.current_revision = current_revision


class ProjectIdempotencyConflict(Exception):
    pass


class ProjectSessionManager:
    def __init__(self, data_dir: str | Path, session_factory: Callable[[str], Any]) -> None:
        self.data_dir = Path(data_dir).expanduser().resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.session_factory = session_factory
        self._sessions: dict[str, Any] = {}
        self._revisions: dict[str, int] = {}
        self._locks: dict[str, RLock] = {}
        self._manager_lock = RLock()

    def _project_lock(self, project_id: str) -> RLock:
        with self._manager_lock:
            return self._locks.setdefault(project_id, RLock())

    def _database_path(self, project_id: str) -> str:
        # Never use caller-controlled project IDs as filesystem paths.
        name = hashlib.sha256(project_id.encode("utf-8")).hexdigest()
        return str(self.data_dir / f"{name}.sqlite3")

    def _session(self, project_id: str):
        with self._manager_lock:
            session = self._sessions.get(project_id)
            if session is not None:
                return session
            session = self.session_factory(self._database_path(project_id))
            database = session.engine.database
            if database is None:
                raise RuntimeError("Project sessions require an Orren ProjectDatabase.")
            connection = database.connection
            connection.execute("""
                CREATE TABLE IF NOT EXISTS api_commands (
                    revision INTEGER PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    action_json TEXT NOT NULL,
                    result_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            connection.commit()
            rows = connection.execute(
                "SELECT revision, action_json FROM api_commands ORDER BY revision"
            ).fetchall()
            for row in rows:
                session.apply(json.loads(row["action_json"]))
            current_revision = int(rows[-1]["revision"]) if rows else 0
            self._sessions[project_id] = session
            self._revisions[project_id] = current_revision
            return session

    @staticmethod
    def _envelope(project_id: str, revision: int, field: dict) -> dict:
        return {"projectId": project_id, "revision": revision, "field": field}

    def snapshot(self, project_id: str) -> dict:
        with self._project_lock(project_id):
            session = self._session(project_id)
            return self._envelope(project_id, self._revisions[project_id], session.snapshot())

    def execute(
        self, project_id: str, expected_revision: int, idempotency_key: str, action: dict
    ) -> tuple[dict, bool]:
        canonical_action = json.dumps(action, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self._project_lock(project_id):
            session = self._session(project_id)
            database = session.engine.database
            connection = database.connection
            previous = connection.execute(
                "SELECT action_json, result_json FROM api_commands WHERE idempotency_key=?",
                (idempotency_key,),
            ).fetchone()
            if previous is not None:
                if previous["action_json"] != canonical_action:
                    raise ProjectIdempotencyConflict("This idempotency key was already used for a different command.")
                return json.loads(previous["result_json"]), False

            current_revision = self._revisions[project_id]
            if expected_revision != current_revision:
                raise ProjectRevisionConflict(current_revision)

            field = session.apply(action)
            # Save the materialized SIR revision and all derived realization plans.
            database.save_run(
                session.source_name,
                session.source_text,
                session.graph,
                session.artifacts,
                session.engine_version,
            )
            next_revision = current_revision + 1
            result = self._envelope(project_id, next_revision, field)
            connection.execute(
                "INSERT INTO api_commands(revision, idempotency_key, action_json, result_json) VALUES(?,?,?,?)",
                (next_revision, idempotency_key, canonical_action, json.dumps(result, ensure_ascii=False, separators=(",", ":"))),
            )
            connection.commit()
            self._revisions[project_id] = next_revision
            return result, True


__all__ = [
    "ProjectIdempotencyConflict",
    "ProjectRevisionConflict",
    "ProjectSessionManager",
]
