"""Stable intermediate representation between SIR and realization backends.

The Realization IR is deliberately backend-neutral. It records semantic nodes,
capability requirements, target declarations, degradation obligations, and
provenance without embedding source-language or runtime-specific code.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List

from .data_model import Dimension, RealizationTarget, SIRGraph

IR_VERSION = "1.0"


@dataclass(frozen=True)
class IRNode:
    path: str
    name: str
    kind: str
    dimensions: Dict[str, List[Any]]
    parent_path: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "name": self.name,
            "kind": self.kind,
            "parent_path": self.parent_path,
            "dimensions": self.dimensions,
        }


@dataclass(frozen=True)
class IRTarget:
    name: str
    language: str
    capabilities: List[str]
    can_express: List[str]
    needs_bridge: List[str]
    cannot_express: List[str]
    degradation: List[Dict[str, str]]
    preservation_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "language": self.language,
            "capabilities": list(self.capabilities),
            "can_express": list(self.can_express),
            "needs_bridge": list(self.needs_bridge),
            "cannot_express": list(self.cannot_express),
            "degradation": list(self.degradation),
            "preservation_score": round(self.preservation_score, 4),
        }


@dataclass(frozen=True)
class RealizationIR:
    version: str
    source_hash: str
    sir_hash: str
    nodes: List[IRNode]
    targets: List[IRTarget]
    provenance: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "source_hash": self.source_hash,
            "sir_hash": self.sir_hash,
            "nodes": [node.to_dict() for node in self.nodes],
            "targets": [target.to_dict() for target in self.targets],
            "provenance": dict(self.provenance),
        }

    def canonical_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), ensure_ascii=False)

    def content_hash(self) -> str:
        return hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def validate(self) -> None:
        if self.version != IR_VERSION:
            raise ValueError(f"unsupported Realization IR version: {self.version}")
        if len(self.source_hash) != 64 or len(self.sir_hash) != 64:
            raise ValueError("Realization IR provenance hashes must be SHA-256")
        paths = [node.path for node in self.nodes]
        if paths != sorted(paths):
            raise ValueError("Realization IR nodes must be path-sorted")
        if len(paths) != len(set(paths)):
            raise ValueError("Realization IR node paths must be unique")
        names = [target.name for target in self.targets]
        if len(names) != len(set(names)):
            raise ValueError("Realization IR target names must be unique")


def lower_graph(graph: SIRGraph, source: str = "", compiler: str = "orren") -> RealizationIR:
    """Lower an already-resolved SIR graph into deterministic backend-neutral IR."""
    source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
    sir_hash = hashlib.sha256(graph.signature().encode("utf-8")).hexdigest()
    nodes: List[IRNode] = []
    for node in sorted(graph.nodes, key=lambda item: item.path):
        dimensions = {
            dimension.value: list(node.dimensions.get(dimension, []))
            for dimension in Dimension
        }
        nodes.append(IRNode(
            path=node.path,
            name=node.name,
            kind=node.kind,
            parent_path=node.parent.path if node.parent else None,
            dimensions=dimensions,
        ))
    targets = [
        IRTarget(
            name=target.name,
            language=target.language,
            capabilities=sorted(target.capabilities),
            can_express=sorted(target.can_express),
            needs_bridge=sorted(target.needs_bridge),
            cannot_express=sorted(target.cannot_express),
            degradation=sorted(
                ({"level": item.level.value, "dimension": item.dimension, "aspect": item.aspect, "mode": item.mode} for item in target.degradation),
                key=lambda item: (item["dimension"], item["aspect"], item["level"]),
            ),
            preservation_score=target.preservation_score,
        )
        for target in sorted(graph.realization_targets, key=lambda item: item.name)
    ]
    ir = RealizationIR(
        version=IR_VERSION,
        source_hash=source_hash,
        sir_hash=sir_hash,
        nodes=nodes,
        targets=targets,
        provenance={"compiler": compiler},
    )
    ir.validate()
    return ir


__all__ = ["IR_VERSION", "IRNode", "IRTarget", "RealizationIR", "lower_graph"]
