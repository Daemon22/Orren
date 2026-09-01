"""Purified Orren language parser.

This module implements the concrete syntax derived from the Zero-Assumption
Orren Purification document.  It deliberately exposes only the seven language
constructs identified by that document:

Core:       entity, relation, constraint, scope
Enrichment: intent, behavior, temporal

The parser lowers the new syntax into the existing ``Expression`` model so
that the current SIR builder can consume it during the migration.  It does
not add Vibe, Cognitive, Equilibrium, Mediation, or multi-target realization
syntax to the language core; those concerns belong to extensions or pipeline
stages.

Canonical forms:

    entity sensor: device = "soil moisture sensor" {
        intent "measure soil moisture"
        behavior "emit measurement"
        temporal "active while the controller is running"
    }

    relation sensor -> controller: dependency
    constraint sensor.value > 0

    scope irrigation {
        entity controller: process = "irrigation controller"
    }

The parser is intentionally small and deterministic.  It validates the
language shape while preserving the semantic text verbatim for later stages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .data_model import Expression, ExpressionType, StructureNode


ENTITY_RE = re.compile(
    r'^\s*entity\s+(?P<name>[A-Za-z_][A-Za-z0-9_.]*)\s*:\s*'
    r'(?P<type>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*(?P<meaning>.+?)\s*'
    r'(?:\{\s*)?$'
)
ENTITY_BARE_RE = re.compile(
    r'^\s*entity\s+(?P<name>[A-Za-z_][A-Za-z0-9_.]*)\s*:\s*'
    r'(?P<type>[A-Za-z_][A-Za-z0-9_]*)\s*$'
)
RELATION_RE = re.compile(
    r'^\s*relation\s+(?P<src>[A-Za-z_][A-Za-z0-9_.]*)\s*'
    r'->\s*(?P<tgt>[A-Za-z_][A-Za-z0-9_.]*)\s*:\s*'
    r'(?P<type>[A-Za-z_][A-Za-z0-9_.-]+)(?:\s+when\s+(?P<condition>.+))?\s*$'
)
CONSTRAINT_RE = re.compile(r'^\s*constraint\s+(?P<expr>.+?)\s*$')
SCOPE_RE = re.compile(r'^\s*scope\s+(?P<name>[A-Za-z_][A-Za-z0-9_.]*)\s*\{\s*$')
ANNOTATION_RE = re.compile(
    r'^\s*(?P<kind>intent|behavior|temporal)\s+(?P<value>.+?)\s*$'
)
CLOSE_RE = re.compile(r'^\s*}\s*$')

TYPE_MAP = {
    "application": ExpressionType.APPLICATION,
    "subsystem": ExpressionType.SUBSYSTEM,
    "equilibrium": ExpressionType.EQUILIBRIUM,
    "interface": ExpressionType.INTERFACE,
    "document": ExpressionType.DOCUMENT,
    "device": ExpressionType.DEVICE,
    "service": ExpressionType.SERVICE,
    "process": ExpressionType.SUBSYSTEM,
    "constant": ExpressionType.DOCUMENT,
    "event": ExpressionType.SERVICE,
}


@dataclass
class PurifiedEntity:
    name: str
    type: str
    meaning: str
    intent: Optional[str] = None
    behavior: Optional[str] = None
    temporal: Optional[str] = None
    line: int = 0
    scope: Optional[str] = None


@dataclass
class PurifiedRelation:
    source: str
    target: str
    relation_type: str
    condition: Optional[str] = None
    line: int = 0


@dataclass
class PurifiedConstraint:
    expression: str
    line: int = 0


@dataclass
class PurifiedProgram:
    entities: List[PurifiedEntity] = field(default_factory=list)
    relations: List[PurifiedRelation] = field(default_factory=list)
    constraints: List[PurifiedConstraint] = field(default_factory=list)
    scopes: List[str] = field(default_factory=list)


class PurifiedSyntaxError(ValueError):
    """Raised when canonical purified syntax is malformed."""

    def __init__(self, message: str, line: int = 0) -> None:
        self.line = line
        super().__init__(f"line {line}: {message}" if line else message)


class PurifiedParser:
    """Parse the seven-construct purified Orren language.

    ``parse_program`` returns a language-native ``PurifiedProgram``.
    ``parse`` lowers the same source into the existing Expression model for
    compatibility with the current SIR pipeline.
    """

    def parse_program(self, source: str) -> PurifiedProgram:
        lines = source.splitlines()
        program = PurifiedProgram()
        entity_stack: List[PurifiedEntity] = []
        scope_stack: List[str] = []

        i = 0
        while i < len(lines):
            lineno = i + 1
            raw = lines[i]
            text = raw.strip()
            i += 1

            if not text or text.startswith("#") or text.startswith("--"):
                continue

            if CLOSE_RE.match(text):
                if entity_stack:
                    entity_stack.pop()
                elif scope_stack:
                    scope_stack.pop()
                else:
                    raise PurifiedSyntaxError("unexpected '}'", lineno)
                continue

            sm = SCOPE_RE.match(text)
            if sm:
                scope_stack.append(sm.group("name"))
                program.scopes.append(".".join(scope_stack))
                continue

            em = ENTITY_RE.match(text)
            if not em:
                em = ENTITY_BARE_RE.match(text)
            if em:
                meaning = em.groupdict().get("meaning")
                if meaning is None:
                    raise PurifiedSyntaxError(
                        "entity requires a meaning expression: "
                        "entity NAME: TYPE = MEANING",
                        lineno,
                    )
                entity = PurifiedEntity(
                    name=em.group("name"),
                    type=em.group("type"),
                    meaning=_unquote(meaning.strip()),
                    line=lineno,
                    scope=".".join(scope_stack) or None,
                )
                program.entities.append(entity)
                if text.endswith("{"):
                    entity_stack.append(entity)
                continue

            rm = RELATION_RE.match(text)
            if rm:
                program.relations.append(
                    PurifiedRelation(
                        source=rm.group("src"),
                        target=rm.group("tgt"),
                        relation_type=rm.group("type"),
                        condition=(rm.group("condition") or None),
                        line=lineno,
                    )
                )
                continue

            cm = CONSTRAINT_RE.match(text)
            if cm:
                program.constraints.append(
                    PurifiedConstraint(expression=cm.group("expr"), line=lineno)
                )
                continue

            am = ANNOTATION_RE.match(text)
            if am:
                if not entity_stack:
                    raise PurifiedSyntaxError(
                        f"{am.group('kind')} must annotate an entity", lineno
                    )
                kind = am.group("kind")
                value = _unquote(am.group("value").strip())
                setattr(entity_stack[-1], kind, value)
                continue

            raise PurifiedSyntaxError(
                f"unknown construct '{text.split()[0]}'", lineno
            )

        if entity_stack:
            raise PurifiedSyntaxError("unclosed entity block")
        if scope_stack:
            raise PurifiedSyntaxError("unclosed scope block")
        return program

    def parse(self, source: str) -> List[Expression]:
        """Lower canonical purified syntax into legacy-compatible expressions."""
        program = self.parse_program(source)
        if not program.entities and not program.relations and not program.constraints:
            raise PurifiedSyntaxError("program contains no semantic constructs")

        roots: Dict[str, StructureNode] = {}
        children_by_scope: Dict[str, List[PurifiedEntity]] = {}
        for entity in program.entities:
            children_by_scope.setdefault(entity.scope or "", []).append(entity)

        # One canonical Expression per top-level entity, matching the
        # repository's existing multi-expression capability.
        expressions: List[Expression] = []
        top_level = [e for e in program.entities if not e.scope]
        if not top_level and program.entities:
            top_level = [program.entities[0]]

        for root_entity in top_level:
            etype = TYPE_MAP.get(root_entity.type.lower(), ExpressionType.UNSPECIFIED)
            expr = Expression(
                name=root_entity.name,
                type=etype,
                source_line=root_entity.line,
            )
            root = StructureNode(
                name=root_entity.name,
                indent=4,
                line=root_entity.line,
            )
            expr.structure.append(root)
            roots[root_entity.name] = root
            self._append_entity_enrichment(expr, root_entity)

            # Include other top-level entities as siblings beneath the
            # expression root.  The legacy builder represents the program
            # as one graph, while Structure remains the topology mechanism.
            for entity in program.entities:
                if entity is root_entity:
                    continue
                if entity.scope:
                    continue
                node = StructureNode(name=entity.name, indent=4, line=entity.line)
                root.children.append(node)
                self._append_entity_enrichment(expr, entity, node)

            relations = [r for r in program.relations]
            expr.raw_sections["relational"] = [
                {
                    "source": r.source,
                    "relation": r.relation_type,
                    "target": r.target,
                    "qualifier": r.condition,
                    "line": r.line,
                }
                for r in relations
            ]
            expr.raw_sections["conditional"] = [
                {
                    "subject": "__graph__",
                    "action": "satisfy",
                    "condition": c.expression,
                    "unconditional": False,
                    "line": c.line,
                }
                for c in program.constraints
            ]
            break

        return expressions

    @staticmethod
    def _append_entity_enrichment(
        expr: Expression,
        entity: PurifiedEntity,
        node: Optional[StructureNode] = None,
    ) -> None:
        target = node or (expr.structure[-1] if expr.structure else None)
        expr.raw_sections.setdefault("meaning", []).append(
            {
                "subject": entity.name,
                "meaning": entity.meaning,
                "type": entity.type,
                "line": entity.line,
            }
        )
        if entity.intent is not None:
            expr.raw_sections.setdefault("intent", []).append(
                {"subject": entity.name, "intent": entity.intent, "line": entity.line}
            )
        if entity.behavior is not None:
            expr.raw_sections.setdefault("behavior", []).append(
                {
                    "subject": entity.name,
                    "kind": "behavior",
                    "role": entity.behavior,
                    "line": entity.line,
                }
            )
        if entity.temporal is not None:
            expr.raw_sections.setdefault("temporal", []).append(
                {
                    "source": entity.name,
                    "kind": "scope",
                    "target": entity.temporal,
                    "line": entity.line,
                }
            )


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


__all__ = [
    "PurifiedParser",
    "PurifiedProgram",
    "PurifiedEntity",
    "PurifiedRelation",
    "PurifiedConstraint",
    "PurifiedSyntaxError",
]
