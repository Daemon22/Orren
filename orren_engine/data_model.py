"""
Orren Engine — Core Data Model
==============================

27 classes defining the atomic units of the semantic object graph.

Architecture (per 07_VALIDATION_v3.md):
  - Every SIR node carries ALL 9 dimensions simultaneously.
  - 9 dimensions = 8 semantic + equilibrium (cross-cutting).
  - 6 tolerance levels: full, faithful, conventional, proxy, documented, optional.
  - RealizationArtifact schema with capabilities, output_files,
    degradation_report, preservation_score.

This module is the authoritative type surface for the engine. Other modules
MUST NOT define parallel ad-hoc structures.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations (5)
# ---------------------------------------------------------------------------


class Dimension(str, Enum):
    """The 9 dimensions every SIR node carries.

    8 semantic dimensions (EXPRESSION through BEHAVIORAL) plus EQUILIBRIUM,
    which is cross-cutting — it does not exist as a parsed section but is
    attached during resolution.
    """

    EXPRESSION = "expression"
    COGNITIVE = "cognitive"
    VIBE = "vibe"
    SPATIAL = "spatial"
    TEMPORAL = "temporal"
    RELATIONAL = "relational"
    CONDITIONAL = "conditional"
    BEHAVIORAL = "behavioral"
    EQUILIBRIUM = "equilibrium"

    @classmethod
    def semantic(cls) -> Tuple["Dimension", ...]:
        """The 8 semantic dimensions, excluding the cross-cutting equilibrium."""
        return (
            cls.EXPRESSION,
            cls.COGNITIVE,
            cls.VIBE,
            cls.SPATIAL,
            cls.TEMPORAL,
            cls.RELATIONAL,
            cls.CONDITIONAL,
            cls.BEHAVIORAL,
        )


class ToleranceLevel(str, Enum):
    """Six tolerance levels, ordered from strongest to weakest."""

    FULL = "full"
    FAITHFUL = "faithful"
    CONVENTIONAL = "conventional"
    PROXY = "proxy"
    DOCUMENTED = "documented"
    OPTIONAL = "optional"

    @classmethod
    def ordered(cls) -> Tuple["ToleranceLevel", ...]:
        return (
            cls.FULL,
            cls.FAITHFUL,
            cls.CONVENTIONAL,
            cls.PROXY,
            cls.DOCUMENTED,
            cls.OPTIONAL,
        )

    def strength(self) -> int:
        """Higher = stronger preservation contract."""
        return len(ToleranceLevel.ordered()) - self.ordered().index(self)


class Severity(str, Enum):
    """Severity of a realization degradation."""

    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    OUT_OF_SCOPE = "out_of_scope"


class ExpressionType(str, Enum):
    """What a `create` block declares."""

    APPLICATION = "Application"
    SUBSYSTEM = "Subsystem"
    EQUILIBRIUM = "Equilibrium"
    INTERFACE = "Interface"
    DOCUMENT = "Document"
    DEVICE = "Device"
    SERVICE = "Service"
    UNSPECIFIED = "Unspecified"


class EditOp(str, Enum):
    """Semantic Editor Protocol operations."""

    MODIFY = "modify"
    RELOCATE = "relocate"
    REDEFINE = "redefine"
    ADD = "add"
    REMOVE = "remove"


# ---------------------------------------------------------------------------
# Expression / structural classes (3)
# ---------------------------------------------------------------------------


@dataclass
class ContextStatement:
    """A single key:value line inside a `context:` block."""

    key: str
    value: str
    line: int = 0


@dataclass
class StructureNode:
    """A node in the `structure:` tree.

    Indentation-based hierarchy: a child has parent_indent < child_indent.
    """

    name: str
    indent: int
    parent: Optional["StructureNode"] = None
    children: List["StructureNode"] = field(default_factory=list)
    line: int = 0

    def path(self) -> str:
        """Dot-separated path from root, e.g. 'home.microphone_control'."""
        if self.parent is None or self.parent.name == "_root":
            return self.name
        return f"{self.parent.path()}.{self.name}"


@dataclass
class Expression:
    """A single `create NAME : Type` block in a .orn file.

    One .orn file may contain multiple Expression blocks (Gap 5).
    """

    name: str
    type: ExpressionType
    context: List[ContextStatement] = field(default_factory=list)
    structure: List[StructureNode] = field(default_factory=list)
    raw_sections: Dict[str, List[str]] = field(default_factory=dict)
    source_line: int = 0

    def structure_root(self) -> Optional[StructureNode]:
        """Return the first top-level structure node, or None."""
        for n in self.structure:
            if n.parent is None or n.parent.name == "_root":
                return n
        return None


# ---------------------------------------------------------------------------
# Dimension payload classes (8)
# ---------------------------------------------------------------------------


@dataclass
class CognitiveStatement:
    """A `key = value` line inside a `cognitive:` block."""

    subject: str
    predicate: str
    value: str
    line: int = 0


@dataclass
class VibeStatement:
    """A `subject.aspect = term` line inside a `vibe:` block.

    `aspect` may be 'color_character', 'form_character', 'tone',
    'aesthetic', 'activation_signal', or any free-form aspect name.
    """

    subject: str
    aspect: str
    term: str
    annotation: Optional[str] = None
    line: int = 0


@dataclass
class SpatialStatement:
    """`subject located_in/scoped_to target` line inside `spatial:`."""

    subject: str
    relation: str  # 'located_in' | 'scoped_to'
    target: str
    line: int = 0


@dataclass
class TemporalStatement:
    """A line inside `temporal:`.

    Either a transition (`A → B on trigger`) or a persistence
    (`X persists beyond Y`).
    """

    kind: str  # 'transition' | 'persistence' | 'sequence'
    source: str
    target: Optional[str] = None
    trigger: Optional[str] = None
    line: int = 0


@dataclass
class RelationalStatement:
    """`A feeds/triggers/produces B` line inside `relational:`."""

    source: str
    relation: str  # 'feeds' | 'triggers' | 'produces' | 'depends_on'
    target: str
    qualifier: Optional[str] = None
    line: int = 0


@dataclass
class ConditionalStatement:
    """`subject activates/retained/begins on CONDITION` line."""

    subject: str
    action: str  # 'activates' | 'begins' | 'retained' | 'deactivates'
    condition: str
    unconditional: bool = False
    line: int = 0


@dataclass
class LifecycleTransition:
    """A single hop in a `lifecycle: A → B → C → D` chain."""

    from_state: str
    to_state: str


@dataclass
class BehavioralStatement:
    """One line inside `behavior:`.

    kind in:
      - 'behaves_as'        (subject behaves_as ROLE)
      - 'responds_to'       (subject responds_to STIMULUS with RESPONSE)
      - 'transitions'       (subject transitions from A to B on EVENT)
      - 'lifecycle'         (subject lifecycle: A -> B -> C -> D)
    """

    subject: str
    kind: str
    role: Optional[str] = None
    stimulus: Optional[str] = None
    response: Optional[str] = None
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    on_event: Optional[str] = None
    lifecycle: List[LifecycleTransition] = field(default_factory=list)
    line: int = 0


# ---------------------------------------------------------------------------
# Calibration (2)
# ---------------------------------------------------------------------------


@dataclass
class CalibrationTarget:
    """One signal/threshold pair within a calibrate block."""

    maps_to: str
    threshold: str
    signal: Optional[str] = None
    note: Optional[str] = None


@dataclass
class CalibrationEntry:
    """`calibrate TERM for DIM:` block."""

    term: str
    dimension: str  # the dimension name as written (e.g. 'vibe')
    targets: List[CalibrationTarget] = field(default_factory=list)
    line: int = 0


# ---------------------------------------------------------------------------
# Equilibrium (3)
# ---------------------------------------------------------------------------


@dataclass
class EquilibriumCondition:
    """A single `WHEN cond AND cond` clause."""

    dimension: str
    predicate: str


@dataclass
class EquilibriumResolution:
    """The `resolution:` line — how to honor the contract."""

    text: str
    bridge_to: Optional[str] = None  # target language if explicit


@dataclass
class EquilibriumRule:
    """A complete `name: when ... preserve ... resolution:` block."""

    name: str
    conditions: List[EquilibriumCondition] = field(default_factory=list)
    preserve: List[str] = field(default_factory=list)
    resolution: Optional[EquilibriumResolution] = None
    rationale: Optional[str] = None
    line: int = 0

    def applies_to(self, node: "SIRNode") -> bool:
        """Does this rule fire on the given node?

        A rule fires if every condition's dimension is present on the node
        AND the condition's predicate matches the dimension's payload.

        Predicate matching is semantic: the predicate is split into a
        leading term (the actual token being checked, e.g. 'calm' in
        'vibe.calm is active') plus optional English commentary
        ('is active'). The rule fires if the leading term appears in
        the dimension's serialized payload.
        """
        for cond in self.conditions:
            # Be tolerant of unknown dimension names — rule does not fire.
            try:
                dim = Dimension(cond.dimension)
            except ValueError:
                return False
            dim_payload = node.dimensions.get(dim)
            if not dim_payload:
                return False
            blob = _serialize_payload(dim_payload).lower()
            # Extract the leading term from the predicate (e.g. 'calm'
            # from 'calm is active'). Anything after the first whitespace
            # is treated as English commentary.
            leading_term = cond.predicate.strip().split()[0].lower() if cond.predicate.strip() else ""
            if not leading_term:
                return False
            if leading_term not in blob:
                return False
        return True


# ---------------------------------------------------------------------------
# Realization (4)
# ---------------------------------------------------------------------------


@dataclass
class DegradationEntry:
    """One row of `tolerate/require LEVEL for DIM on ASPECT`."""

    level: ToleranceLevel
    dimension: str
    aspect: str
    mode: str = "tolerate"  # 'tolerate' | 'require'


@dataclass
class OutputFile:
    """A single artifact produced by a realization target."""

    path: str
    language: str


@dataclass
class RealizationTarget:
    """Parsed `target: NAME (LANG)` block from `realize:`."""

    name: str
    language: str
    capabilities: List[str] = field(default_factory=list)
    can_express: List[str] = field(default_factory=list)
    needs_bridge: List[str] = field(default_factory=list)
    cannot_express: List[str] = field(default_factory=list)
    degradation: List[DegradationEntry] = field(default_factory=list)
    preservation_score: float = 1.0


@dataclass
class RealizationArtifact:
    """Final artifact produced by the coordinator for one target.

    Schema matches 07_VALIDATION_v3.md exactly.
    """

    target_language: str
    capabilities: List[str] = field(default_factory=list)
    output_files: List[OutputFile] = field(default_factory=list)
    degradation_report: List[Dict[str, str]] = field(default_factory=list)
    preservation_score: float = 1.0
    target_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "target_name": self.target_name,
            "target_language": self.target_language,
            "capabilities": list(self.capabilities),
            "output_files": [
                {"path": f.path, "language": f.language} for f in self.output_files
            ],
            "degradation_report": list(self.degradation_report),
            "preservation_score": round(self.preservation_score, 4),
        }


# ---------------------------------------------------------------------------
# SIR core (2)
# ---------------------------------------------------------------------------


@dataclass
class SIRNode:
    """Atomic semantic unit. Carries ALL 9 dimensions simultaneously.

    Invariant (testable):
        Every SIRNode has a key for every Dimension — values may be empty
        lists but the keys MUST exist. This is what prevents any dimension
        from being silently dropped during realization.
    """

    path: str  # dot-separated, e.g. 'application.home.microphone_control'
    name: str
    kind: str = "entity"  # 'entity' | 'subsystem' | 'equilibrium' | 'root'
    parent: Optional["SIRNode"] = None
    children: List["SIRNode"] = field(default_factory=list)
    dimensions: Dict[Dimension, List[Any]] = field(default_factory=dict)
    degradation_tolerance: Dict[str, DegradationEntry] = field(default_factory=dict)
    calibration: List[CalibrationEntry] = field(default_factory=list)
    dirty: bool = False
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def __post_init__(self) -> None:
        # INVARIANT: every node carries all 9 dimensions.
        for dim in Dimension:
            self.dimensions.setdefault(dim, [])

    def set_dimension(self, dim: Dimension, payload: Any) -> None:
        self.dimensions[dim].append(payload)

    def get_dimension(self, dim: Dimension) -> List[Any]:
        return self.dimensions.get(dim, [])

    def has_dimension_content(self, dim: Dimension) -> bool:
        return bool(self.dimensions.get(dim))

    def all_dimensions_present(self) -> bool:
        """Invariant check: all 9 dimension keys exist."""
        return all(dim in self.dimensions for dim in Dimension)

    def signature(self) -> str:
        """Stable content signature for output-stability tests.

        Two nodes with identical signatures MUST produce identical
        realization artifacts. Line numbers are intentionally excluded
        — they are source-position metadata, not semantic content, so
        adding/removing comments or blank lines must not change the
        signature.
        """
        parts = [self.path, self.kind]
        for dim in Dimension:
            payload = self.dimensions.get(dim, [])
            parts.append(f"{dim.value}:{_serialize_payload(payload, exclude_fields=('line',))}")
        return "|".join(parts)


@dataclass
class SIRGraph:
    """The full multidimensional semantic object graph."""

    root: Optional[SIRNode] = None
    nodes: List[SIRNode] = field(default_factory=list)
    equilibrium_rules: List[EquilibriumRule] = field(default_factory=list)
    realization_targets: List[RealizationTarget] = field(default_factory=list)
    expressions: List[Expression] = field(default_factory=list)

    def find(self, path: str) -> Optional[SIRNode]:
        """Locate a node by exact dot-path."""
        for n in self.nodes:
            if n.path == path:
                return n
        return None

    def search(
        self,
        dimension: Optional[Dimension] = None,
        property_name: Optional[str] = None,
        value: Optional[str] = None,
    ) -> List[SIRNode]:
        """Search nodes by dimension / property / value (any subset).

        When `dimension` is provided, only nodes with non-empty payload
        for that dimension are returned. `property_name` and `value`
        further filter within that payload (substring match on the
        serialized blob).
        """
        out: List[SIRNode] = []
        for n in self.nodes:
            if dimension is not None:
                payload = n.dimensions.get(dimension, [])
                if not payload:
                    continue
                if value is None and property_name is None:
                    out.append(n)
                    continue
                blob = _serialize_payload(payload)
                if value is not None and value not in blob:
                    continue
                if property_name is not None and property_name not in blob:
                    continue
                out.append(n)
            else:
                if value is None and property_name is None:
                    out.append(n)
                    continue
                blob = _serialize_payload_all(n)
                if value is not None and value not in blob:
                    continue
                if property_name is not None and property_name not in blob:
                    continue
                out.append(n)
        return out

    def signature(self) -> str:
        """Whole-graph signature for SIR-builder stability tests."""
        return "\n".join(n.signature() for n in self.nodes)


# ---------------------------------------------------------------------------
# Editing (1)
# ---------------------------------------------------------------------------


@dataclass
class EditOperation:
    """A single semantic edit, recorded for undo/redo."""

    op: EditOp
    target_path: str
    dimension: Optional[Dimension] = None
    property_name: Optional[str] = None
    old_value: Any = None
    new_value: Any = None
    rationale: Optional[str] = None
    timestamp: str = ""
    edit_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _serialize_payload(payload: Any, exclude_fields: tuple = ()) -> str:
    """Stable string serialization of a dimension payload list.

    `exclude_fields` lets the caller strip source-metadata fields
    (e.g. 'line') from the signature so that comments and blank lines
    in the source don't change the semantic signature.
    """
    if payload is None:
        return ""
    if isinstance(payload, list):
        items = []
        for item in payload:
            if isinstance(item, dict):
                keys = sorted(k for k in item.keys() if k not in exclude_fields)
                items.append(",".join(f"{k}={item[k]}" for k in keys))
            elif hasattr(item, "__dataclass_fields__"):
                fields_to_use = [
                    f for f in item.__dataclass_fields__
                    if f not in exclude_fields
                    and getattr(item, f) not in (None, [], {})
                ]
                items.append(
                    ",".join(f"{f}={getattr(item, f)}" for f in fields_to_use)
                )
            else:
                items.append(str(item))
        return ";".join(sorted(items))
    return str(payload)


def _serialize_payload_all(node: SIRNode) -> str:
    return " ".join(
        _serialize_payload(node.dimensions.get(dim, [])) for dim in Dimension
    )


# ---------------------------------------------------------------------------
# Public type surface — count = 27
# ---------------------------------------------------------------------------
#
#  1.  Dimension
#  2.  ToleranceLevel
#  3.  Severity
#  4.  ExpressionType
#  5.  EditOp
#  6.  ContextStatement
#  7.  StructureNode
#  8.  Expression
#  9.  CognitiveStatement
# 10.  VibeStatement
# 11.  SpatialStatement
# 12.  TemporalStatement
# 13.  RelationalStatement
# 14.  ConditionalStatement
# 15.  LifecycleTransition
# 16.  BehavioralStatement
# 17.  CalibrationTarget
# 18.  CalibrationEntry
# 19.  EquilibriumCondition
# 20.  EquilibriumResolution
# 21.  EquilibriumRule
# 22.  DegradationEntry
# 23.  OutputFile
# 24.  RealizationTarget
# 25.  RealizationArtifact
# 26.  SIRNode
# 27.  SIRGraph
#
# (EditOperation is a 28th helper class — it is the editing history record
#  rather than a structural type, so it is not counted toward the 27 core
#  classes listed in 07_VALIDATION_v3.md. It is included here for
#  completeness; if your engine strictly requires 27, treat EditOperation
#  as the editing module's auxiliary type.)
# ---------------------------------------------------------------------------
