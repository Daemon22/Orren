"""Orren semantic repository package.

Exposes the backend-neutral :class:`~orren_engine.storage.repository.AbstractRepository`
contract and the default :class:`~orren_engine.storage.sqlite_repo.SQLiteRepo`
SQLite implementation.  The repository is Orren's durable state boundary for
provenance: raw source, materialized SIR, rules, targets, diagnostics, edit
history, artifacts, and build records.
"""
from .repository import AbstractRepository, NodeRef, Payload, SourceSpan
from .sqlite_repo import SQLiteRepo, SCHEMA_VERSION

__all__ = [
    "AbstractRepository",
    "NodeRef",
    "Payload",
    "SourceSpan",
    "SQLiteRepo",
    "SCHEMA_VERSION",
]
