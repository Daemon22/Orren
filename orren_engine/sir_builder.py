"""
Orren Engine — SIR Builder
==========================

Converts a list of parsed Expression objects into a SIRGraph:
a multidimensional semantic object graph where every node carries
ALL 9 dimensions simultaneously (per 07_VALIDATION_v3.md).

Architecture:
    9 dimension builders cooperate:
      1. expression   — context + structure → entity tree
      2. cognitive    — cognitive statements attached per-node
      3. vibe         — vibe statements attached per-node
      4. spatial      — located_in/scoped_to attached per-node
      5. temporal     — transitions/persistence attached per-node
      6. relational   — feeds/triggers/produces attached per-node
      7. conditional  — activation conditions attached per-node
      8. behavioral   — lifecycle/transitions attached per-node
      9. equilibrium  — rules collected at graph level, attached
                        per-node during resolution

Every dimension builder operates on the same SIRNode set; none of them
may create new nodes — only enrich existing ones. This is the structural
guarantee that no dimension can ever be silently dropped.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .data_model import (
    BehavioralStatement,
    CalibrationEntry,
    CognitiveStatement,
    ConditionalStatement,
    DegradationEntry,
    Dimension,
    EquilibriumRule,
    Expression,
    ExpressionType,
    RealizationTarget,
    RelationalStatement,
    SIRGraph,
    SIRNode,
    SpatialStatement,
    StructureNode,
    TemporalStatement,
    ToleranceLevel,
    VibeStatement,
)


class SIRBuilder:
    """Build a SIRGraph from a list of Expression objects."""

    def build(self, expressions: List[Expression]) -> SIRGraph:
        graph = SIRGraph(expressions=expressions)
        for expr in expressions:
            self._build_expression(expr, graph)
        return graph

    # -----------------------------------------------------------------
    # Per-expression construction
    # -----------------------------------------------------------------

    def _build_expression(self, expr: Expression, graph: SIRGraph) -> None:
        # 1. EXPRESSION dimension: build the entity tree from structure.
        # If no structure is provided, create a single root node named
        # after the expression.
        expr_node = self._make_entity_node(
            path=expr.name,
            name=expr.name,
            kind=(
                "equilibrium"
                if expr.type == ExpressionType.EQUILIBRIUM
                else "root"
            ),
        )
        # Attach context statements as the expression dimension payload.
        for ctx in expr.context:
            expr_node.set_dimension(
                Dimension.EXPRESSION,
                {"key": ctx.key, "value": ctx.value, "line": ctx.line},
            )
        expr_node.set_dimension(
            Dimension.EXPRESSION,
            {"__type__": expr.type.value, "__name__": expr.name},
        )

        graph.nodes.append(expr_node)
        if graph.root is None:
            graph.root = expr_node

        # Build entity tree from structure section.
        # IMPORTANT: build ALL top-level structure nodes, not just the
        # first. A structure section may declare multiple sibling roots
        # (e.g. `arm`, `control_unit`, `interface` in a device description).
        entity_nodes: Dict[str, SIRNode] = {expr.name: expr_node}
        for struct_node in expr.structure:
            if struct_node.parent is None or struct_node.parent.name == "_root":
                self._build_structure_tree(
                    struct_node, parent=expr_node, graph=graph, registry=entity_nodes
                )

        # 2-8. Attach each dimension's payload to the appropriate node(s).
        self._attach_cognitive(expr, graph, entity_nodes)
        self._attach_vibe(expr, graph, entity_nodes)
        self._attach_spatial(expr, graph, entity_nodes)
        self._attach_temporal(expr, graph, entity_nodes)
        self._attach_relational(expr, graph, entity_nodes)
        self._attach_conditional(expr, graph, entity_nodes)
        self._attach_behavioral(expr, graph, entity_nodes)

        # Calibration — attached to the nearest subject node (or root).
        self._attach_calibration(expr, graph, entity_nodes)

        # Degradation tolerance — flattened into a dict on each affected node.
        self._attach_degradation(expr, graph, entity_nodes)

        # 9. Equilibrium rules — collected at graph level.
        for rule_dict in expr.raw_sections.get("equilibrium", []):
            rule = self._dict_to_rule(rule_dict)
            if rule is not None:
                graph.equilibrium_rules.append(rule)

        # Realization targets — collected at graph level.
        for tgt_dict in expr.raw_sections.get("realize", []):
            tgt = self._dict_to_target(tgt_dict)
            if tgt is not None:
                graph.realization_targets.append(tgt)

    # -----------------------------------------------------------------
    # Structure tree → entity nodes
    # -----------------------------------------------------------------

    def _build_structure_tree(
        self,
        struct_node: StructureNode,
        parent: SIRNode,
        graph: SIRGraph,
        registry: Dict[str, SIRNode],
    ) -> None:
        path = f"{parent.path}.{struct_node.name}"
        node = self._make_entity_node(
            path=path, name=struct_node.name, kind="entity", parent=parent
        )
        parent.children.append(node)
        graph.nodes.append(node)
        registry[path] = node
        # Also register by short name for convenience lookups.
        registry.setdefault(struct_node.name, node)
        for child in struct_node.children:
            self._build_structure_tree(child, node, graph, registry)

    def _make_entity_node(
        self,
        path: str,
        name: str,
        kind: str = "entity",
        parent: Optional[SIRNode] = None,
    ) -> SIRNode:
        node = SIRNode(path=path, name=name, kind=kind, parent=parent)
        return node

    # -----------------------------------------------------------------
    # Dimension attachment (8 builders)
    # -----------------------------------------------------------------

    def _resolve_subject(
        self, subject: str, registry: Dict[str, SIRNode], root: SIRNode
    ) -> SIRNode:
        """Resolve a subject reference to a SIRNode.

        Subjects may be dotted paths ('home.microphone_control') or short
        names ('microphone_control'). If unresolvable, attach to root.
        """
        if subject in registry:
            return registry[subject]
        # Try suffix match: any path ending in .subject
        for path, node in registry.items():
            if path.endswith("." + subject) or path == subject:
                return node
        return root

    def _attach_cognitive(
        self, expr: Expression, graph: SIRGraph, registry: Dict[str, SIRNode]
    ) -> None:
        root = registry[expr.name]
        for payload in expr.raw_sections.get("cognitive", []):
            subj = payload.get("subject", "")
            node = self._resolve_subject(subj, registry, root)
            node.set_dimension(Dimension.COGNITIVE, payload)

    def _attach_vibe(
        self, expr: Expression, graph: SIRGraph, registry: Dict[str, SIRNode]
    ) -> None:
        root = registry[expr.name]
        for payload in expr.raw_sections.get("vibe", []):
            subj = payload.get("subject", "")
            node = self._resolve_subject(subj, registry, root)
            node.set_dimension(Dimension.VIBE, payload)

    def _attach_spatial(
        self, expr: Expression, graph: SIRGraph, registry: Dict[str, SIRNode]
    ) -> None:
        root = registry[expr.name]
        for payload in expr.raw_sections.get("spatial", []):
            subj = payload.get("subject", "")
            node = self._resolve_subject(subj, registry, root)
            node.set_dimension(Dimension.SPATIAL, payload)

    def _attach_temporal(
        self, expr: Expression, graph: SIRGraph, registry: Dict[str, SIRNode]
    ) -> None:
        root = registry[expr.name]
        for payload in expr.raw_sections.get("temporal", []):
            subj = payload.get("source", "")
            node = self._resolve_subject(subj, registry, root)
            node.set_dimension(Dimension.TEMPORAL, payload)

    def _attach_relational(
        self, expr: Expression, graph: SIRGraph, registry: Dict[str, SIRNode]
    ) -> None:
        root = registry[expr.name]
        for payload in expr.raw_sections.get("relational", []):
            subj = payload.get("source", "")
            node = self._resolve_subject(subj, registry, root)
            node.set_dimension(Dimension.RELATIONAL, payload)

    def _attach_conditional(
        self, expr: Expression, graph: SIRGraph, registry: Dict[str, SIRNode]
    ) -> None:
        root = registry[expr.name]
        for payload in expr.raw_sections.get("conditional", []):
            subj = payload.get("subject", "")
            node = self._resolve_subject(subj, registry, root)
            node.set_dimension(Dimension.CONDITIONAL, payload)

    def _attach_behavioral(
        self, expr: Expression, graph: SIRGraph, registry: Dict[str, SIRNode]
    ) -> None:
        root = registry[expr.name]
        for payload in expr.raw_sections.get("behavior", []):
            subj = payload.get("subject", "")
            node = self._resolve_subject(subj, registry, root)
            node.set_dimension(Dimension.BEHAVIORAL, payload)

    # -----------------------------------------------------------------
    # Calibration and degradation
    # -----------------------------------------------------------------

    def _attach_calibration(
        self, expr: Expression, graph: SIRGraph, registry: Dict[str, SIRNode]
    ) -> None:
        root = registry[expr.name]
        for cal_dict in expr.raw_sections.get("calibrate", []):
            entry = CalibrationEntry(
                term=cal_dict.get("term", ""),
                dimension=cal_dict.get("dimension", ""),
            )
            for tgt in cal_dict.get("targets", []):
                from .data_model import CalibrationTarget

                entry.targets.append(
                    CalibrationTarget(
                        maps_to=tgt.get("maps_to", ""),
                        threshold=tgt.get("threshold", ""),
                        signal=tgt.get("signal"),
                        note=tgt.get("note"),
                    )
                )
            # Calibration targets a vibe term; attach to root or to any
            # node whose vibe payload mentions the term.
            attached = False
            for node in graph.nodes:
                for v in node.get_dimension(Dimension.VIBE):
                    if isinstance(v, dict) and v.get("term") == entry.term:
                        node.calibration.append(entry)
                        attached = True
            if not attached:
                root.calibration.append(entry)

    def _attach_degradation(
        self, expr: Expression, graph: SIRGraph, registry: Dict[str, SIRNode]
    ) -> None:
        for d_dict in expr.raw_sections.get("degrade", []):
            entry = DegradationEntry(
                level=ToleranceLevel(d_dict.get("level", "optional")),
                dimension=d_dict.get("dimension", ""),
                aspect=d_dict.get("aspect", ""),
                mode=d_dict.get("mode", "tolerate"),
            )
            # Attach to every node that has content in the named dimension.
            dim_name = entry.dimension
            try:
                dim = Dimension(dim_name)
            except ValueError:
                continue
            for node in graph.nodes:
                if node.has_dimension_content(dim):
                    node.degradation_tolerance[f"{dim_name}.{entry.aspect}"] = entry

    # -----------------------------------------------------------------
    # Helpers: dict → typed object
    # -----------------------------------------------------------------

    def _dict_to_rule(self, d: Dict) -> Optional[EquilibriumRule]:
        from .data_model import (
            EquilibriumCondition,
            EquilibriumResolution,
        )

        rule = EquilibriumRule(name=d.get("name", ""))
        for c in d.get("conditions", []):
            rule.conditions.append(
                EquilibriumCondition(
                    dimension=c.get("dimension", ""),
                    predicate=c.get("predicate", ""),
                )
            )
        rule.preserve = list(d.get("preserve", []))
        if d.get("resolution"):
            rule.resolution = EquilibriumResolution(text=d["resolution"])
        rule.rationale = d.get("rationale")
        return rule

    def _dict_to_target(self, d: Dict) -> Optional[RealizationTarget]:
        from .data_model import DegradationEntry, RealizationTarget, ToleranceLevel

        tgt = RealizationTarget(
            name=d.get("name", ""),
            language=d.get("language", ""),
            capabilities=list(d.get("capabilities", [])),
            can_express=list(d.get("can_express", [])),
            needs_bridge=list(d.get("needs_bridge", [])),
            cannot_express=list(d.get("cannot_express", [])),
            preservation_score=float(d.get("preservation_score", 1.0)),
        )
        for dd in d.get("degradation", []):
            try:
                tgt.degradation.append(
                    DegradationEntry(
                        level=ToleranceLevel(dd.get("level", "optional")),
                        dimension=dd.get("dimension", ""),
                        aspect=dd.get("aspect", ""),
                        mode=dd.get("mode", "tolerate"),
                    )
                )
            except ValueError:
                pass
        return tgt


__all__ = ["SIRBuilder"]
