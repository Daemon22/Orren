"""
Orren Engine — Equilibrium Resolver
===================================

Detects cross-dimension conflicts and applies preservation contracts.

Per 07_VALIDATION_v3.md:
  - Pattern matching → rule application
  - Semantic condition evaluation
  - Preservation analysis

Determinism contract (CRITICAL):
    For the same SIR graph + same rule set, the resolver MUST produce
    the same output every time. Rule application order is the order in
    which rules appear in the .orn file; ties are broken by rule name.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .data_model import (
    Dimension,
    EquilibriumRule,
    SIRGraph,
    SIRNode,
)


@dataclass
class ResolutionOutcome:
    """The result of applying one rule to one node."""

    rule_name: str
    node_path: str
    preserve: List[str]
    resolution_text: Optional[str]
    rationale: Optional[str]


@dataclass
class EquilibriumReport:
    """Full output of an equilibrium resolution pass."""

    outcomes: List[ResolutionOutcome] = field(default_factory=list)
    unresolved_conflicts: List[Dict[str, str]] = field(default_factory=list)

    def signature(self) -> str:
        """Stable signature for determinism tests."""
        lines = []
        for o in self.outcomes:
            lines.append(
                f"{o.rule_name}@{o.node_path}:"
                f"preserve={','.join(sorted(o.preserve))};"
                f"resolution={o.resolution_text or ''}"
            )
        for c in self.unresolved_conflicts:
            keys = sorted(c.keys())
            lines.append(
                "UNRESOLVED:" + ",".join(f"{k}={c[k]}" for k in keys)
            )
        return "\n".join(lines)


class EquilibriumResolver:
    """Apply equilibrium rules to a SIR graph.

    Two passes:
      1. Conflict detection — find nodes where two dimensions make
         incompatible demands (e.g. calm vibe + urgent cognitive state).
      2. Rule application — for each rule that fires, record a
         ResolutionOutcome and stamp the resolution text onto the node
         as an EQUILIBRIUM dimension payload.
    """

    # Well-known conflict patterns. Each entry is
    # (dim_a, predicate_a, dim_b, predicate_b, conflict_name).
    # A rule whose `when` clause matches both halves of a pattern
    # resolves that conflict.
    CONFLICT_PATTERNS: List[Tuple[str, str, str, str, str]] = [
        ("vibe", "calm", "cognitive", "activation", "calm_vs_urgency"),
        ("vibe", "aesthetic", "cognitive", "recording", "aesthetic_vs_function"),
        ("cognitive", "preservation", "cognitive", "transcription", "preserve_vs_transform"),
    ]

    def resolve(self, graph: SIRGraph) -> EquilibriumReport:
        report = EquilibriumReport()
        # Detect conflicts first.
        conflicts = self._detect_conflicts(graph)
        # Apply rules in file order; if multiple rules match the same
        # conflict, the first one wins (deterministic).
        resolved_conflicts: set = set()
        for rule in graph.equilibrium_rules:
            for node in graph.nodes:
                if rule.applies_to(node):
                    outcome = ResolutionOutcome(
                        rule_name=rule.name,
                        node_path=node.path,
                        preserve=list(rule.preserve),
                        resolution_text=(
                            rule.resolution.text if rule.resolution else None
                        ),
                        rationale=rule.rationale,
                    )
                    report.outcomes.append(outcome)
                    # Stamp the resolution onto the node.
                    node.set_dimension(
                        Dimension.EQUILIBRIUM,
                        {
                            "rule": rule.name,
                            "preserve": list(rule.preserve),
                            "resolution": outcome.resolution_text,
                            "rationale": outcome.rationale,
                        },
                    )
                    # Mark any matching conflict as resolved.
                    for c in conflicts:
                        if c["node"] == node.path:
                            resolved_conflicts.add(c["name"])
        # Report unresolved conflicts.
        for c in conflicts:
            if c["name"] not in resolved_conflicts:
                report.unresolved_conflicts.append(c)
        return report

    # -----------------------------------------------------------------
    # Conflict detection
    # -----------------------------------------------------------------

    def _detect_conflicts(self, graph: SIRGraph) -> List[Dict[str, str]]:
        conflicts: List[Dict[str, str]] = []
        for node in graph.nodes:
            for (
                dim_a,
                pred_a,
                dim_b,
                pred_b,
                conflict_name,
            ) in self.CONFLICT_PATTERNS:
                try:
                    da = Dimension(dim_a)
                    db = Dimension(dim_b)
                except ValueError:
                    continue
                if not _node_has_predicate(node, da, pred_a):
                    continue
                if not _node_has_predicate(node, db, pred_b):
                    continue
                conflicts.append(
                    {
                        "node": node.path,
                        "name": conflict_name,
                        "dim_a": dim_a,
                        "pred_a": pred_a,
                        "dim_b": dim_b,
                        "pred_b": pred_b,
                    }
                )
        return conflicts


def _node_has_predicate(node: SIRNode, dim: Dimension, predicate: str) -> bool:
    """True if the predicate string appears in any value of the given
    dimension on the node."""
    payload = node.dimensions.get(dim, [])
    if not payload:
        return False
    blob = _serialize(node.dimensions.get(dim, []))
    return predicate.lower() in blob.lower()


def _serialize(payload: object) -> str:
    if payload is None:
        return ""
    if isinstance(payload, list):
        parts = []
        for item in payload:
            if isinstance(item, dict):
                parts.append(
                    ",".join(f"{k}={item[k]}" for k in sorted(item.keys()))
                )
            elif hasattr(item, "__dataclass_fields__"):
                parts.append(
                    ",".join(
                        f"{f}={getattr(item, f)}"
                        for f in item.__dataclass_fields__
                        if getattr(item, f) not in (None, [], {})
                    )
                )
            else:
                parts.append(str(item))
        return ";".join(parts)
    return str(payload)


__all__ = ["EquilibriumResolver", "EquilibriumReport", "ResolutionOutcome"]
