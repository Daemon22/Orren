"""SIR builder output stability tests.

Validates that the SIR builder produces deterministic, stable output:
  - Same input → same node ordering, same paths, same payloads, every run.
  - Node ordering follows insertion order (deterministic).
  - Paths are stable: same .orn → same paths.
  - Dimension payloads preserve insertion order from the source.
  - Subsystem composition: multiple `create` blocks → multiple roots,
    each preserving its own subtree.
  - Large/complex inputs don't destabilize output.

Run: pytest tests/test_05_sir_stability.py -v
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from orren_engine import CoParser, Dimension, SIRBuilder
from orren_engine.data_model import SIRGraph


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

SOURCE_A = """create app : Application

    context:
        purpose: a microphone control

    structure:
        home
            microphone_control
                icon

    cognitive:
        microphone_control.activation = on_user_intent
        microphone_control.recording = capture_audio

    vibe:
        microphone_control.color_character = emerald
        microphone_control.tone = calm
"""

SOURCE_B = """create app : Application

    context:
        purpose: a microphone control

    structure:
        home
            microphone_control
                icon

    cognitive:
        microphone_control.activation = on_user_intent
        microphone_control.recording = capture_audio

    vibe:
        microphone_control.color_character = emerald
        microphone_control.tone = calm
"""

# SOURCE_C is identical to A but with comments and blank lines that
# should not affect the SIR output.
SOURCE_C = """# This is a comment
create app : Application

    context:
        purpose: a microphone control

    structure:
        home
            microphone_control
                icon

    cognitive:
        # activation logic
        microphone_control.activation = on_user_intent
        microphone_control.recording = capture_audio

    vibe:
        microphone_control.color_character = emerald
        microphone_control.tone = calm
"""

SOURCE_SUBSYSTEMS = """create farm_system : Application

    context:
        purpose: a farm management system

    structure:
        dashboard
            crop_panel
            irrigation_panel

create crop_planner : Subsystem

    context:
        purpose: plan crops

    cognitive:
        crop_planner.scheduling = seasonal

create irrigation_controller : Subsystem

    cognitive:
        irrigation_controller.flow = regulated

    equilibrium:
        water_priority:
            when cognitive.flow is active AND cognitive.scheduling is active
            preserve both
            resolution: schedule around crop windows

create system_equilibrium : Equilibrium

    equilibrium:
        system_balance:
            when cognitive.flow is active AND cognitive.scheduling is active
            preserve both
            resolution: system-level coordination
"""


# ---------------------------------------------------------------------------
# Determinism: same input → same output
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_signature_identical_across_runs(self):
        sigs = []
        for _ in range(5):
            graph = SIRBuilder().build(CoParser().parse(SOURCE_A))
            sigs.append(graph.signature())
        assert len(set(sigs)) == 1

    def test_node_count_identical(self):
        g1 = SIRBuilder().build(CoParser().parse(SOURCE_A))
        g2 = SIRBuilder().build(CoParser().parse(SOURCE_A))
        assert len(g1.nodes) == len(g2.nodes)

    def test_node_paths_identical(self):
        g1 = SIRBuilder().build(CoParser().parse(SOURCE_A))
        g2 = SIRBuilder().build(CoParser().parse(SOURCE_A))
        assert [n.path for n in g1.nodes] == [n.path for n in g2.nodes]

    def test_node_ordering_stable(self):
        """Nodes appear in insertion order: root first, then BFS."""
        graph = SIRBuilder().build(CoParser().parse(SOURCE_A))
        paths = [n.path for n in graph.nodes]
        # Root must be first.
        assert paths[0] == "app"
        # Children come after parents.
        home_idx = paths.index("app.home")
        mc_idx = paths.index("app.home.microphone_control")
        icon_idx = paths.index("app.home.microphone_control.icon")
        assert home_idx < mc_idx < icon_idx

    def test_payload_order_preserved(self):
        """Within a node, dimension payloads preserve source order."""
        graph = SIRBuilder().build(CoParser().parse(SOURCE_A))
        node = graph.find("app.home.microphone_control")
        cog = node.get_dimension(Dimension.COGNITIVE)
        assert cog[0]["predicate"] == "activation"
        assert cog[1]["predicate"] == "recording"
        # Vibe order: color_character, tone (source order)
        vib = node.get_dimension(Dimension.VIBE)
        assert vib[0]["aspect"] == "color_character"
        assert vib[1]["aspect"] == "tone"

    def test_comments_and_blanks_dont_affect_output(self):
        """SOURCE_C is SOURCE_A with comments and blank lines; the SIR
        output should be identical."""
        g_a = SIRBuilder().build(CoParser().parse(SOURCE_A))
        g_c = SIRBuilder().build(CoParser().parse(SOURCE_C))
        assert g_a.signature() == g_c.signature()


# ---------------------------------------------------------------------------
# Path stability
# ---------------------------------------------------------------------------


class TestPathStability:
    def test_paths_are_dotted(self):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_A))
        for node in graph.nodes:
            assert "." in node.path or node.path == "app"

    def test_path_includes_expression_name(self):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_A))
        for node in graph.nodes:
            # Root node has path = expression name with no dot;
            # children start with "expression_name.".
            assert node.path == "app" or node.path.startswith("app.")

    def test_subsystem_paths_includes_their_own_root(self):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_SUBSYSTEMS))
        paths = {n.path for n in graph.nodes}
        # Each subsystem is its own root.
        assert "farm_system" in paths
        assert "crop_planner" in paths
        assert "irrigation_controller" in paths
        assert "system_equilibrium" in paths
        # farm_system has a subtree.
        assert "farm_system.dashboard" in paths
        assert "farm_system.dashboard.crop_panel" in paths
        assert "farm_system.dashboard.irrigation_panel" in paths


# ---------------------------------------------------------------------------
# Subsystem composition (Gap 5)
# ---------------------------------------------------------------------------


class TestSubsystemComposition:
    def test_multiple_expressions_produce_multiple_roots(self):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_SUBSYSTEMS))
        roots = [n for n in graph.nodes if n.parent is None]
        assert len(roots) == 4

    def test_subsystem_structure_preserved(self):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_SUBSYSTEMS))
        # farm_system has its own subtree.
        farm = graph.find("farm_system")
        assert farm is not None
        assert len(farm.children) == 1  # dashboard
        assert farm.children[0].name == "dashboard"
        # dashboard has two children
        assert len(farm.children[0].children) == 2

    def test_subsystem_cognitive_attached_locally(self):
        """crop_planner's cognitive statement must attach to
        crop_planner, not to farm_system."""
        graph = SIRBuilder().build(CoParser().parse(SOURCE_SUBSYSTEMS))
        cp = graph.find("crop_planner")
        assert cp is not None
        cog = cp.get_dimension(Dimension.COGNITIVE)
        assert len(cog) == 1
        assert cog[0]["subject"] == "crop_planner"

    def test_equilibrium_rules_aggregated_at_graph_level(self):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_SUBSYSTEMS))
        # Two rules across two subsystems.
        assert len(graph.equilibrium_rules) == 2
        names = {r.name for r in graph.equilibrium_rules}
        assert names == {"water_priority", "system_balance"}


# ---------------------------------------------------------------------------
# Larger input stability
# ---------------------------------------------------------------------------


LARGE_SOURCE = """create big_app : Application

    context:
        purpose: a large test
        audience: developers
        scale: large

    structure:
        root
            child_a
                grandchild_a1
                grandchild_a2
            child_b
                grandchild_b1
                    great_grandchild_b1a
            child_c

    cognitive:
        child_a.processing = enabled
        child_b.storage = persistent
        grandchild_a1.scheduling = timed
        great_grandchild_b1a.optimization = aggressive

    vibe:
        child_a.tone = calm
        child_b.tone = urgent
        grandchild_a1.color_character = blue

    spatial:
        child_a located_in root
        child_b located_in root

    temporal:
        child_a → grandchild_a1 on schedule
        grandchild_b1 → great_grandchild_b1a on demand

    relational:
        child_a feeds grandchild_a1
        child_b feeds grandchild_b1
        grandchild_b1 feeds great_grandchild_b1a

    conditional:
        child_a activates on start_signal
        child_b activates on storage_request

    behavior:
        child_a transitions from idle to active on start_signal
        child_a lifecycle: idle -> active -> processing -> idle
"""


class TestLargeInputStability:
    def test_signature_stable_across_runs(self):
        sigs = []
        for _ in range(5):
            graph = SIRBuilder().build(CoParser().parse(LARGE_SOURCE))
            sigs.append(graph.signature())
        assert len(set(sigs)) == 1

    def test_all_nodes_built(self):
        graph = SIRBuilder().build(CoParser().parse(LARGE_SOURCE))
        # big_app + root + child_a + grandchild_a1 + grandchild_a2
        # + child_b + grandchild_b1 + great_grandchild_b1a + child_c
        # = 9 nodes
        assert len(graph.nodes) == 9

    def test_deeply_nested_paths_correct(self):
        graph = SIRBuilder().build(CoParser().parse(LARGE_SOURCE))
        paths = {n.path for n in graph.nodes}
        assert "big_app.root.child_a.grandchild_a1" in paths
        assert "big_app.root.child_b.grandchild_b1.great_grandchild_b1a" in paths
        assert "big_app.root.child_c" in paths

    def test_dimensions_attached_at_correct_depth(self):
        graph = SIRBuilder().build(CoParser().parse(LARGE_SOURCE))
        gg = graph.find("big_app.root.child_b.grandchild_b1.great_grandchild_b1a")
        assert gg is not None
        cog = gg.get_dimension(Dimension.COGNITIVE)
        assert len(cog) == 1
        assert cog[0]["predicate"] == "optimization"


# ---------------------------------------------------------------------------
# Round-trip stability
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_rebuild_preserves_state(self):
        """Build a graph, capture signature, build again from same
        source — signature must match."""
        g1 = SIRBuilder().build(CoParser().parse(LARGE_SOURCE))
        sig1 = g1.signature()
        # Mutate g1 (e.g. add a node)
        from orren_engine.data_model import SIRNode

        g1.nodes.append(SIRNode(path="extra", name="extra"))
        # g1's signature now differs.
        sig2 = g1.signature()
        assert sig1 != sig2
        # But a fresh build from the same source produces the same sig.
        g3 = SIRBuilder().build(CoParser().parse(LARGE_SOURCE))
        assert g3.signature() == sig1
