"""
Orren Engine — Semantic Editor Protocol
=======================================

Path-based editing of the SIR graph, with full undo/redo history.

Per 07_VALIDATION_v3.md (Gap 6):
    editor.modify(
        "application.home.microphone_control.icon",
        Dimension.VIBE,
        "color_character",
        "calmer",
        rationale="User wants a more subdued look"
    )

Operations:
    modify(path, dim, prop, new_value, rationale=...)
    relocate(path, new_parent_path)
    redefine(path, new_kind)
    add(path, dim, payload)
    remove(path, dim, prop)

All operations return an EditOperation record and push to history.
Undo/redo navigate the history stack.
Dirty nodes are marked for re-realization.
"""

from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .data_model import (
    Dimension,
    EditOp,
    EditOperation,
    SIRGraph,
    SIRNode,
)


# For dimensions whose payload entries use a (key_field, value_field)
# pattern, this maps Dimension → list of (key_field, value_field) pairs.
# When the editor is asked to modify a property by name, it matches the
# name against key_field's value and updates value_field.
_KEY_VALUE_FIELDS: Dict[Dimension, List[tuple]] = {
    Dimension.VIBE: [("aspect", "term")],
    Dimension.COGNITIVE: [("predicate", "value")],
    Dimension.SPATIAL: [("relation", "target")],
    Dimension.TEMPORAL: [("kind", "source")],
    Dimension.RELATIONAL: [("relation", "target")],
    Dimension.CONDITIONAL: [("action", "condition")],
    Dimension.BEHAVIORAL: [("kind", "role")],
}


class SemanticEditor:
    """Operates on semantic paths, not file paths."""

    def __init__(self, graph: SIRGraph) -> None:
        self.graph = graph
        self.history: List[EditOperation] = []
        self.redo_stack: List[EditOperation] = []

    # -----------------------------------------------------------------
    # Path resolution
    # -----------------------------------------------------------------

    def resolve(self, path: str) -> Optional[SIRNode]:
        """Resolve a semantic path to a SIRNode.

        Tries exact match first, then suffix match (so 'icon' resolves
        to 'application.home.microphone_control.icon' if unique).
        """
        exact = self.graph.find(path)
        if exact is not None:
            return exact
        # Suffix match
        candidates = [n for n in self.graph.nodes if n.path.endswith("." + path)]
        if len(candidates) == 1:
            return candidates[0]
        # Try matching by short name
        by_name = [n for n in self.graph.nodes if n.name == path]
        if len(by_name) == 1:
            return by_name[0]
        return None

    def search(
        self,
        dimension: Optional[Dimension] = None,
        property_name: Optional[str] = None,
        value: Optional[str] = None,
    ) -> List[SIRNode]:
        """Search nodes by dimension / property / value (any subset)."""
        return self.graph.search(dimension, property_name, value)

    # -----------------------------------------------------------------
    # Edit operations
    # -----------------------------------------------------------------

    def modify(
        self,
        path: str,
        dimension: Dimension,
        property_name: str,
        new_value: Any,
        rationale: Optional[str] = None,
    ) -> EditOperation:
        """Modify a property on a dimension payload of a node."""
        node = self._require(path)
        old_value = self._read_property(node, dimension, property_name)
        self._write_property(node, dimension, property_name, new_value)
        node.dirty = True
        op = EditOperation(
            op=EditOp.MODIFY,
            target_path=path,
            dimension=dimension,
            property_name=property_name,
            old_value=old_value,
            new_value=new_value,
            rationale=rationale,
            timestamp=_now_iso(),
        )
        self.history.append(op)
        self.redo_stack.clear()
        return op

    def relocate(
        self, path: str, new_parent_path: str, rationale: Optional[str] = None
    ) -> EditOperation:
        """Move a node to a new parent. Updates paths of the moved
        subtree."""
        node = self._require(path)
        # Capture the FULL original path before any mutation, so undo
        # can restore it exactly. (The input `path` may be a short name
        # or suffix; we record the resolved full path.)
        original_full_path = node.path
        new_parent = self._require(new_parent_path)
        old_parent = node.parent
        old_parent_path = old_parent.path if old_parent else None
        if old_parent is not None and node in old_parent.children:
            old_parent.children.remove(node)
        new_parent.children.append(node)
        node.parent = new_parent
        # Re-path the subtree.
        old_prefix = original_full_path
        new_prefix = f"{new_parent.path}.{node.name}"
        node.path = new_prefix
        self._repath_subtree(node, old_prefix, new_prefix)
        node.dirty = True
        op = EditOperation(
            op=EditOp.RELOCATE,
            target_path=original_full_path,
            property_name="parent",
            old_value=old_parent_path,
            new_value=new_parent_path,
            rationale=rationale,
            timestamp=_now_iso(),
        )
        self.history.append(op)
        self.redo_stack.clear()
        return op

    def redefine(
        self, path: str, new_kind: str, rationale: Optional[str] = None
    ) -> EditOperation:
        """Change the kind of a node (e.g. 'entity' → 'subsystem')."""
        node = self._require(path)
        old_kind = node.kind
        node.kind = new_kind
        node.dirty = True
        op = EditOperation(
            op=EditOp.REDEFINE,
            target_path=path,
            property_name="kind",
            old_value=old_kind,
            new_value=new_kind,
            rationale=rationale,
            timestamp=_now_iso(),
        )
        self.history.append(op)
        self.redo_stack.clear()
        return op

    def add(
        self,
        path: str,
        dimension: Dimension,
        payload: Any,
        rationale: Optional[str] = None,
    ) -> EditOperation:
        """Append a new payload entry to a node's dimension."""
        node = self._require(path)
        node.set_dimension(dimension, payload)
        node.dirty = True
        op = EditOperation(
            op=EditOp.ADD,
            target_path=path,
            dimension=dimension,
            new_value=payload,
            rationale=rationale,
            timestamp=_now_iso(),
        )
        self.history.append(op)
        self.redo_stack.clear()
        return op

    def remove(
        self,
        path: str,
        dimension: Dimension,
        property_name: str,
        rationale: Optional[str] = None,
    ) -> EditOperation:
        """Remove the first payload entry matching property_name."""
        node = self._require(path)
        old_value = self._read_property(node, dimension, property_name)
        self._delete_property(node, dimension, property_name)
        node.dirty = True
        op = EditOperation(
            op=EditOp.REMOVE,
            target_path=path,
            dimension=dimension,
            property_name=property_name,
            old_value=old_value,
            rationale=rationale,
            timestamp=_now_iso(),
        )
        self.history.append(op)
        self.redo_stack.clear()
        return op

    # -----------------------------------------------------------------
    # Undo / redo
    # -----------------------------------------------------------------

    def undo(self) -> Optional[EditOperation]:
        if not self.history:
            return None
        op = self.history.pop()
        self._apply_reverse(op)
        self.redo_stack.append(op)
        return op

    def redo(self) -> Optional[EditOperation]:
        if not self.redo_stack:
            return None
        op = self.redo_stack.pop()
        self._apply_forward(op)
        self.history.append(op)
        return op

    def can_undo(self) -> bool:
        return bool(self.history)

    def can_redo(self) -> bool:
        return bool(self.redo_stack)

    # -----------------------------------------------------------------
    # Dirty tracking
    # -----------------------------------------------------------------

    def dirty_nodes(self) -> List[SIRNode]:
        return [n for n in self.graph.nodes if n.dirty]

    def mark_clean(self) -> None:
        for n in self.graph.nodes:
            n.dirty = False

    # -----------------------------------------------------------------
    # Internals
    # -----------------------------------------------------------------

    def _require(self, path: str) -> SIRNode:
        node = self.resolve(path)
        if node is None:
            raise KeyError(f"semantic path not found: {path}")
        return node

    def _read_property(
        self, node: SIRNode, dim: Dimension, prop: str
    ) -> Optional[Any]:
        """Read a property value from a dimension payload.

        For dimensions whose payload entries use a (key_field, value_field)
        pattern — e.g. vibe uses (aspect, term), cognitive uses
        (predicate, value) — `prop` matches the KEY FIELD's value and we
        return the VALUE FIELD.

        For dimensions whose payload entries are flat dicts with `prop`
        as a direct key, return entry[prop].
        """
        key_value_fields = _KEY_VALUE_FIELDS.get(dim, [])
        for entry in node.get_dimension(dim):
            if not isinstance(entry, dict):
                continue
            # Flat-key form: prop is a direct key.
            if prop in entry:
                return entry[prop]
            # (key_field, value_field) form: prop matches key_field's value.
            for kf, vf in key_value_fields:
                if entry.get(kf) == prop:
                    return entry.get(vf)
        return None

    def _write_property(
        self, node: SIRNode, dim: Dimension, prop: str, value: Any
    ) -> None:
        """Write a property value to a dimension payload.

        Mirrors _read_property: writes to the value_field of the entry
        whose key_field matches `prop`. If no such entry exists, appends
        a new dict in the (key_field, value_field) form.
        """
        key_value_fields = _KEY_VALUE_FIELDS.get(dim, [])
        for entry in node.get_dimension(dim):
            if not isinstance(entry, dict):
                continue
            if prop in entry:
                entry[prop] = value
                return
            for kf, vf in key_value_fields:
                if entry.get(kf) == prop:
                    entry[vf] = value
                    return
        # Not found — append a new entry in the (key, value) form.
        if key_value_fields:
            kf, vf = key_value_fields[0]
            node.set_dimension(dim, {kf: prop, vf: value})
        else:
            node.set_dimension(dim, {prop: value})

    def _delete_property(
        self, node: SIRNode, dim: Dimension, prop: str
    ) -> None:
        """Remove the first payload entry matching `prop`."""
        key_value_fields = _KEY_VALUE_FIELDS.get(dim, [])
        payload = node.get_dimension(dim)
        for entry in list(payload):
            if not isinstance(entry, dict):
                continue
            matched = False
            if prop in entry:
                del entry[prop]
                matched = True
            for kf, vf in key_value_fields:
                if entry.get(kf) == prop:
                    # Remove the whole entry — a vibe statement with no
                    # term is meaningless.
                    payload.remove(entry)
                    matched = True
                    break
            if matched:
                if isinstance(entry, dict) and not entry:
                    payload.remove(entry)
                return

    def _repath_subtree(
        self, node: SIRNode, old_prefix: str, new_prefix: str
    ) -> None:
        for child in node.children:
            child.path = child.path.replace(old_prefix, new_prefix, 1)
            self._repath_subtree(child, old_prefix, new_prefix)

    def _apply_reverse(self, op: EditOperation) -> None:
        # For relocate, the node moved away from target_path (the
        # original path) to a new path. To undo, we must find the node
        # by its current path (new_value is the new parent; current
        # path is new_parent.name + node.name). For other ops, the node
        # is still at target_path.
        node = None
        if op.op == EditOp.RELOCATE and op.new_value:
            # Locate by suffix: the node's name is the last segment of
            # op.target_path.
            node_name = op.target_path.rsplit(".", 1)[-1]
            new_parent = self.resolve(op.new_value)
            if new_parent is not None:
                for child in new_parent.children:
                    if child.name == node_name:
                        node = child
                        break
        if node is None:
            node = self.resolve(op.target_path)
        if node is None:
            return
        if op.op == EditOp.MODIFY:
            if op.dimension and op.property_name:
                self._write_property(
                    node, op.dimension, op.property_name, op.old_value
                )
        elif op.op == EditOp.RELOCATE:
            # Restore: move node back to old_parent, restore original path.
            if op.old_value:
                old_parent = self.resolve(op.old_value)
                if old_parent is not None:
                    cur_parent = node.parent
                    if cur_parent is not None and node in cur_parent.children:
                        cur_parent.children.remove(node)
                    old_parent.children.append(node)
                    node.parent = old_parent
                    # Restore the original path and re-path subtree.
                    cur_prefix = node.path
                    original_prefix = op.target_path
                    node.path = original_prefix
                    self._repath_subtree(node, cur_prefix, original_prefix)
        elif op.op == EditOp.REDEFINE:
            node.kind = op.old_value
        elif op.op == EditOp.ADD:
            # Remove the last-added payload.
            if op.dimension:
                payload = node.get_dimension(op.dimension)
                if payload:
                    payload.pop()
        elif op.op == EditOp.REMOVE:
            if op.dimension and op.property_name and op.old_value is not None:
                # Re-add the removed entry. We can't fully reconstruct
                # the original entry shape, so we store the value via
                # the (key_field, value_field) pattern if applicable.
                key_value_fields = _KEY_VALUE_FIELDS.get(op.dimension, [])
                if key_value_fields:
                    kf, vf = key_value_fields[0]
                    node.set_dimension(
                        op.dimension, {kf: op.property_name, vf: op.old_value}
                    )
                else:
                    node.set_dimension(
                        op.dimension, {op.property_name: op.old_value}
                    )
        node.dirty = True

    def _apply_forward(self, op: EditOperation) -> None:
        # After undo, the node is back at target_path (for relocate, this
        # is the original path). Redo by re-applying.
        node = self.resolve(op.target_path)
        if node is None and op.op == EditOp.RELOCATE:
            # Maybe the node is at the original path now after undo.
            node = self.resolve(op.target_path)
        if node is None:
            return
        if op.op == EditOp.MODIFY:
            if op.dimension and op.property_name:
                self._write_property(
                    node, op.dimension, op.property_name, op.new_value
                )
        elif op.op == EditOp.RELOCATE:
            if op.new_value:
                new_parent = self.resolve(op.new_value)
                if new_parent is not None:
                    cur_parent = node.parent
                    if cur_parent is not None and node in cur_parent.children:
                        cur_parent.children.remove(node)
                    new_parent.children.append(node)
                    node.parent = new_parent
                    original_prefix = node.path
                    new_prefix = f"{new_parent.path}.{node.name}"
                    node.path = new_prefix
                    self._repath_subtree(node, original_prefix, new_prefix)
        elif op.op == EditOp.REDEFINE:
            node.kind = op.new_value
        elif op.op == EditOp.ADD:
            if op.dimension:
                node.set_dimension(op.dimension, op.new_value)
        elif op.op == EditOp.REMOVE:
            if op.dimension and op.property_name:
                self._delete_property(node, op.dimension, op.property_name)
        node.dirty = True


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


__all__ = ["SemanticEditor"]
