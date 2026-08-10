"""
Tests that verify the Orren Engine architecture behaves correctly on
genuinely difficult natural-language programs — programs written as
natural-language descriptions of realistic applications that were NOT
designed around or pre-optimized for the test suite.

These three programs exercise:
  - Complex multi-domain reasoning (healthcare, finance, distributed systems)
  - High-dimensional conflict resolution (equilibrium rules across 9 dimensions)
  - Multi-target realization (multiple language targets with preservation scores)
  - Edge cases in color palette resolution (custom vibe terms not in PALETTES)
  - Lifecycle transitions expressed as arrow chains (A -> B -> C -> A)
  - Degrade specifications with mixed tolerance levels
  - Semantic editor modify → undo → re-coordinate round-trip

Programs (written as natural-language descriptions, not hand-crafted test fixtures):
  01_distributed_voting.orn  — Byzantine fault-tolerant voting system
  02_hospital_monitor.orn     — ICU patient monitoring with multi-sensor fusion
  03_trading_bot.orn         — Real-time algorithmic trading with risk management
"""

import os
import py_compile
import tempfile
import unittest

from orren_engine import (
    Engine,
    Dimension,
    ToleranceLevel,
    generate_code,
    generate_preview,
    extract_design_tokens,
)

HARD_DIR = os.path.join(os.path.dirname(__file__), "..", "examples", "natural_language_hard")

HARD_PROGRAMS = {
    "01_distributed_voting": "01_distributed_voting.orn",
    "02_hospital_monitor": "02_hospital_monitor.orn",
    "03_trading_bot": "03_trading_bot.orn",
}


def _load(name: str) -> str:
    fname = HARD_PROGRAMS[name]
    path = os.path.join(os.path.dirname(__file__), "..", "examples", "natural_language_hard", fname)
    with open(os.path.abspath(path)) as f:
        return f.read()


# =============================================================================
# Test: Full pipeline runs without crashing on each hard program
# =============================================================================

class TestPipelineEndToEnd(unittest.TestCase):
    """Each hard program must run through the complete engine pipeline."""

    def _run(self, name):
        src = _load(name)
        engine = Engine()
        return engine, engine.run(src)

    def test_distributed_voting_full_pipeline(self):
        engine, result = self._run("01_distributed_voting")
        self.assertGreater(result.expressions_count, 0)
        self.assertGreater(result.sir_node_count, 10)
        self.assertIsNotNone(result.graph)
        self.assertGreater(len(result.artifacts), 0)

    def test_hospital_monitor_full_pipeline(self):
        engine, result = self._run("02_hospital_monitor")
        self.assertGreater(result.expressions_count, 0)
        self.assertGreater(result.sir_node_count, 20)
        self.assertIsNotNone(result.graph)
        self.assertGreater(len(result.artifacts), 0)

    def test_trading_bot_full_pipeline(self):
        engine, result = self._run("03_trading_bot")
        self.assertGreater(result.expressions_count, 0)
        self.assertGreater(result.sir_node_count, 20)
        self.assertIsNotNone(result.graph)
        self.assertGreater(len(result.artifacts), 0)

    def test_no_unresolved_conflicts(self):
        """Genuinely hard programs must resolve all equilibrium conflicts."""
        for name in HARD_PROGRAMS:
            _, result = self._run(name)
            self.assertEqual(
                result.unresolved_conflicts,
                0,
                f"{name} has unresolved conflicts",
            )


# =============================================================================
# Test: 9-dimension invariant on every node
# =============================================================================

class TestNineDimensionInvariant(unittest.TestCase):
    """Every SIRNode must carry all 9 dimension keys (even if some are empty
    for structural grouping nodes). This is the core structural invariant
    documented in 07_VALIDATION_v3.md and enforced by SIRBuilder.
    """

    def test_all_nodes_have_nine_dimensions(self):
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            graph = result.graph
            for node in graph.nodes:
                self.assertTrue(
                    node.all_dimensions_present(),
                    f"Node '{node.path}' is missing one or more of the 9 dimensions in {name}",
                )


# =============================================================================
# Test: Equilibrium rules are properly parsed and resolved
# =============================================================================

class TestEquilibriumRules(unittest.TestCase):

    def test_equilibrium_rules_present_and_fired(self):
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            graph = result.graph
            # Every hard program defines equilibrium rules
            self.assertGreater(
                len(graph.equilibrium_rules), 2,
                f"{name} should have at least 3 equilibrium rules"
            )
            # Equilibrium report should have outcomes or a clean resolution
            self.assertIsNotNone(result.equilibrium_report)
            # No unresolved conflicts (all must be preserved or resolved)
            self.assertEqual(result.unresolved_conflicts, 0)

    def test_equilibrium_preservation_directives_valid(self):
        """Each equilibrium rule must have a valid preserve directive."""
        valid_preserves = {"both", "first", "second", "none"}
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            graph = result.graph
            for rule in graph.equilibrium_rules:
                self.assertIsNotNone(rule.preserve, f"Rule '{rule.name}' in {name} has no preserve directive")
                # preserve is a set of strings
                if isinstance(rule.preserve, (set, list, tuple)):
                    for p in rule.preserve:
                        self.assertIn(
                            p, valid_preserves,
                            f"Rule '{rule.name}' in {name} has invalid preserve target '{p}'"
                        )


# =============================================================================
# Test: Realization targets and preservation scores
# =============================================================================

class TestRealizationTargets(unittest.TestCase):

    def setUp(self):
        self.src = _load("02_hospital_monitor")
        self.engine = Engine()
        self.result = self.engine.run(self.src)
        self.graph = self.result.graph

    def test_targets_have_valid_preservation_scores(self):
        for tgt in self.graph.realization_targets:
            self.assertGreaterEqual(
                tgt.preservation_score, 0.0,
                f"Target '{tgt.name}' has negative preservation score"
            )
            self.assertLessEqual(
                tgt.preservation_score, 1.0,
                f"Target '{tgt.name}' has preservation score > 1.0"
            )

    def test_targets_have_degradation_lists(self):
        for tgt in self.graph.realization_targets:
            self.assertIsInstance(
                tgt.degradation, list,
                f"Target '{tgt.name}' has non-list degradation"
            )
            self.assertIsInstance(
                tgt.preservation_score, float,
                f"Target '{tgt.name}' has non-float preservation_score"
            )

    def test_no_duplicate_target_names(self):
        names = [t.name for t in self.graph.realization_targets]
        self.assertEqual(len(names), len(set(names)), "Duplicate realization target names")

    def test_targets_have_can_express_or_cannot_express(self):
        for tgt in self.graph.realization_targets:
            # Each target must declare what it can and cannot express
            self.assertIsNotNone(tgt.can_express, f"Target '{tgt.name}' has no can_express list")
            self.assertIsNotNone(tgt.cannot_express, f"Target '{tgt.name}' has no cannot_express list")


# =============================================================================
# Test: Code generation compiles and produces output for every target
# =============================================================================

class TestCodeGenerationFullPipeline(unittest.TestCase):

    def _get_target_files(self):
        """Map target name -> (graph, target) pairs for all 3 programs."""
        results = []
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            for tgt in result.graph.realization_targets:
                results.append((name, tgt, result.graph))
        return results

    def test_all_targets_produce_codegen(self):
        targets = self._get_target_files()
        for name, tgt, graph in targets:
            files = generate_code(graph, tgt)
            self.assertGreater(len(files), 0, f"No codegen output for {tgt.name} in {name}")
            for fpath, code in files.items():
                self.assertIsInstance(code, str)
                self.assertGreater(len(code), 0, f"Empty codegen for {fpath} in {name}")

    def test_python_codegen_compiles(self):
        """All Python codegen output must be syntactically valid Python."""
        targets = self._get_target_files()
        for name, tgt, graph in targets:
            files = generate_code(graph, tgt)
            for fpath, code in files.items():
                if fpath.endswith(".py"):
                    with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as tmp:
                        tmp.write(code)
                        tmp_path = tmp.name
                    try:
                        py_compile.compile(tmp_path, doraise=True)
                    except py_compile.PyCompileError as e:
                        self.fail(f"Python codegen invalid in {fpath} ({name}): {e}")
                    finally:
                        os.unlink(tmp_path)

    def test_web_targets_produce_manifest(self):
        """Targets with lang=HTML/CSS/JS must produce at least a manifest file.
        (HTML previews are generated via generate_preview, not generate_code.)"""
        targets = self._get_target_files()
        for name, tgt, graph in targets:
            if tgt.language.lower() in ("html/css/js", "html"):
                files = generate_code(graph, tgt)
                self.assertGreater(len(files), 0,
                                   f"No codegen output for web target {tgt.name} in {name}")
                # Must include a manifest
                has_manifest = any("MANIFEST" in f for f in files)
                self.assertTrue(has_manifest,
                                f"Web target {tgt.name} in {name} has no MANIFEST file")


# =============================================================================
# Test: Preview generation is well-formed HTML
# =============================================================================

class TestPreviewGeneration(unittest.TestCase):

    def test_preview_valid_html_for_all_programs(self):
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            html = generate_preview(result.graph, artifacts=result.artifacts)
            self.assertTrue(html.startswith("<!DOCTYPE html>"), f"{name} preview missing DOCTYPE")
            self.assertIn("<html", html, f"{name} preview missing <html> tag")
            self.assertIn("</html>", html, f"{name} preview missing closing </html>")
            self.assertIn("</style>", html, f"{name} preview missing CSS")
            self.assertIn("</script>", html, f"{name} preview missing JS")

    def test_preview_contains_entity_cards(self):
        """The preview should render at least some entity cards / nodes."""
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            html = generate_preview(result.graph, artifacts=result.artifacts)
            # Should contain some content from the structure
            # (card, section, node, entity — varies by layout strategy)
            has_content = any(
                kw in html
                for kw in ("card", "section", "entity", "node", "component", "doc-")
            )
            self.assertTrue(has_content, f"{name} preview has no rendered entities")

    def test_preview_contains_equilibrium_and_preservation(self):
        """The preview must show equilibrium rules and preservation info."""
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            html = generate_preview(result.graph, artifacts=result.artifacts)
            self.assertIn("equilibrium", html.lower(),
                          f"{name} preview missing equilibrium panel")
            self.assertIn("preservation", html.lower(),
                          f"{name} preview missing preservation info")


# =============================================================================
# Test: Design token extraction works
# =============================================================================

class TestDesignTokenExtraction(unittest.TestCase):

    def test_tokens_have_valid_palette(self):
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            graph = result.graph
            tokens = extract_design_tokens(graph)
            self.assertIsNotNone(tokens.accent, f"{name} has no accent color")
            # Color should be a valid hex or CSS color string
            self.assertTrue(
                tokens.accent.startswith("#") or tokens.accent.startswith("rgb") or tokens.accent.startswith("var"),
                f"{name} accent color is not a valid CSS color: {tokens.accent}"
            )

    def test_tokens_have_valid_layout_strategy(self):
        valid_strategies = {"document", "dashboard", "app", "atmospheric", "schematic"}
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            tokens = extract_design_tokens(result.graph)
            self.assertIn(tokens.layout_strategy, valid_strategies,
                          f"{name} has invalid layout strategy: {tokens.layout_strategy}")

    def test_tokens_have_typography(self):
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            tokens = extract_design_tokens(result.graph)
            self.assertTrue(len(tokens.body_font) > 0, f"{name} has no body font")
            self.assertTrue(len(tokens.heading_font) > 0, f"{name} has no heading font")


# =============================================================================
# Test: Degradation specifications are respected
# =============================================================================

class TestDegradationSpecifications(unittest.TestCase):

    def test_degrade_requirements_satisfied(self):
        """Every program with a degrade: section must attach degradation
        entries (DegradationEntry objects with valid ToleranceLevel) to
        the nodes that carry the named dimension's content."""
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            graph = result.graph
            # At least some nodes should have degradation tolerance entries
            nodes_with_degradation = [n for n in graph.nodes if n.degradation_tolerance]
            self.assertGreater(
                len(nodes_with_degradation), 0,
                f"{name} should have nodes with degradation tolerance entries"
            )
            # Each entry must have a valid ToleranceLevel and mode
            for node in nodes_with_degradation:
                for key, entry in node.degradation_tolerance.items():
                    self.assertIsInstance(
                        entry.level, ToleranceLevel,
                        f"{node.path}: degrade entry '{key}' has invalid level {entry.level}"
                    )
                    self.assertIn(
                        entry.mode, ("require", "tolerate"),
                        f"{node.path}: degrade entry '{key}' has invalid mode '{entry.mode}'"
                    )


# =============================================================================
# Test: Semantic editor workflow (modify → undo → re_coordinate)
# =============================================================================

class TestSemanticEditorWorkflow(unittest.TestCase):

    def test_mod_undo_re_coordinate_round_trip(self):
        """The editor must allow modification, undo, and re-coordinate
        without breaking the graph."""
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            graph = result.graph
            editor = engine.editor()

            # Count nodes before edit
            nodes_before = len(graph.nodes)
            artifacts_before = len(result.artifacts)

            # Modify a vibe on the root node
            root = graph.root
            self.assertIsNotNone(root, f"{name} has no root node")

            op = editor.modify(
                root.path, Dimension.VIBE, "tone", "test_tone_value",
                rationale="testing semantic editor round-trip"
            )
            self.assertEqual(op.op.value, "modify")
            self.assertTrue(editor.can_undo())

            # Undo the modification
            undone = editor.undo()
            self.assertIsNotNone(undone)
            self.assertFalse(editor.can_undo())

            # Re-coordinate should still work after edit + undo
            artifacts = engine.re_coordinate()
            self.assertGreater(len(artifacts), 0, f"re_coordinate failed for {name}")

            # Graph should be unchanged structurally
            self.assertEqual(len(graph.nodes), nodes_before)


# =============================================================================
# Test: Graph structural integrity
# =============================================================================

class TestGraphStructuralIntegrity(unittest.TestCase):

    def test_unique_node_paths(self):
        """All SIR nodes must have unique paths."""
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            paths = [n.path for n in result.graph.nodes]
            duplicates = set(p for p in paths if paths.count(p) > 1)
            self.assertEqual(len(duplicates), 0,
                             f"{name} has duplicate node paths: {duplicates}")

    def test_root_has_children(self):
        """The root node of each program should have at least one child."""
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            self.assertIsNotNone(result.graph.root, f"{name} has no root")
            self.assertGreater(
                len(result.graph.root.children), 0,
                f"{name} root has no children"
            )

    def test_no_orphan_nodes(self):
        """Every non-root node should have a parent reference (path implies parent hierarchy)."""
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            graph = result.graph
            if graph.root is None:
                continue
            root_path = graph.root.path
            for node in graph.nodes:
                if node.kind == "root":
                    self.assertIsNone(node.parent, f"{name}: root has parent")
                    continue
                # path should extend root path
                self.assertTrue(
                    node.path.startswith(root_path),
                    f"{name}: node '{node.path}' doesn't start with root '{root_path}'"
                )


# =============================================================================
# Test: Generate code alias works (public API consistency)
# =============================================================================

class TestPublicAPIConsistency(unittest.TestCase):

    def test_generate_alias_works(self):
        """generate_code (public alias) must route to the same function as generate."""
        from orren_engine.codegen import generate as _generate_direct
        src = _load("03_trading_bot")
        engine = Engine()
        result = engine.run(src)
        graph = result.graph
        tgt = graph.realization_targets[0]

        files_alias = generate_code(graph, tgt)
        files_direct = _generate_direct(graph, tgt)
        self.assertEqual(set(files_alias.keys()), set(files_direct.keys()))
        for key in files_alias:
            self.assertEqual(files_alias[key], files_direct[key],
                             f"generate_code != generate for {key}")

    def test_full_artifact_coverage(self):
        """generate_code must produce output for EVERY realization target."""
        for name in HARD_PROGRAMS:
            src = _load(name)
            engine = Engine()
            result = engine.run(src)
            graph = result.graph
            for tgt in graph.realization_targets:
                files = generate_code(graph, tgt)
                self.assertGreater(len(files), 0,
                                   f"No codegen for target {tgt.name} in {name}")


if __name__ == "__main__":
    unittest.main()
