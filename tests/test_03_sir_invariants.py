"""Semantic object graph — invariant tests.

Validates the structural invariants of the SIR graph as specified in
07_VALIDATION_v3.md:

    "Every SIR node carries ALL 9 dimensions (8 semantic + equilibrium)
     simultaneously — no dimension can be lost."

Covers:
  - Every SIRNode has all 9 dimension keys present (even if empty).
  - Parent/child composition: child.parent.path is a prefix of child.path.
  - No orphan nodes (every non-root node has a parent).
  - Path uniqueness: no two nodes share the same path.
  - Node IDs are unique.
  - Structure tree faithfully reflects the .orn structure section.
  - Dimensions attached to the correct subject node.
  - Equilibrium rules and realization targets collected at graph level.
  - Degradation tolerance attached to the right nodes.
  - Subsystem composition (Gap 5): multiple `create` blocks → one graph
    with parent/child relationships.

Run: pytest tests/test_03_sir_invariants.py -v
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from orren_engine import (
    CoParser,
    Dimension,
    ExpressionType,
    SIRBuilder,
)
from orren_engine.data_model import SIRGraph, SIRNode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SOURCE_SIMPLE = """create app : Application

    context:
        purpose: a microphone control

    structure:
        home
            microphone_control

    cognitive:
        microphone_control.activation = on_user_intent
        microphone_control.recording = capture_audio

    vibe:
        microphone_control.color_character = emerald
        microphone_control.tone = calm
"""


SOURCE_FULL = """create mic_app : Application

    context:
        purpose: a microphone control on the home screen

    structure:
        home
            microphone_control
                icon

    cognitive:
        microphone_control.activation = on_user_intent
        microphone_control.recording = capture_audio
        microphone_control.transcription = transcribe_audio
        microphone_control.preservation = retain_original

    vibe:
        microphone_control.color_character = emerald
        microphone_control.form_character = organic
        microphone_control.tone = calm

    spatial:
        microphone_control located_in home
        microphone_control scoped_to home.primary_surface

    temporal:
        activation → recording on user_intent
        recording → stops on user_stop
        original_audio persists beyond transcription

    relational:
        microphone_control feeds device_microphone
        device_microphone feeds recorder
        recorder feeds transcriber

    conditional:
        microphone_control activates on double_click
        microphone_control activates on volume_down × 2
        original_audio retained always (unconditional preservation)

    behavior:
        microphone_control behaves_as organic_toggle
        microphone_control transitions from idle to active on activation_intent
        microphone_control transitions from active to recording on device_microphone_ack
        microphone_control lifecycle: idle -> active -> recording -> processing -> idle

    degrade:
        require full for cognitive on activation_logic
        tolerate faithful for vibe on color_character

    realize:
        target: web_interface (HTML/CSS/JS)
            capabilities: layout, color, event_handling
            preservation_score: 0.83
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

create system_equilibrium : Equilibrium

    equilibrium:
        water_vs_crops:
            when cognitive.irrigation is active AND cognitive.crop is active
            preserve both
            resolution: schedule irrigation around crop windows
"""


@pytest.fixture
def graph_simple():
    parser = CoParser()
    exprs = parser.parse(SOURCE_SIMPLE)
    return SIRBuilder().build(exprs)


@pytest.fixture
def graph_full():
    parser = CoParser()
    exprs = parser.parse(SOURCE_FULL)
    return SIRBuilder().build(exprs)


@pytest.fixture
def graph_subsystems():
    parser = CoParser()
    exprs = parser.parse(SOURCE_SUBSYSTEMS)
    return SIRBuilder().build(exprs)


# ---------------------------------------------------------------------------
# Dimension completeness invariant
# ---------------------------------------------------------------------------


class TestDimensionCompleteness:
    def test_every_node_has_all_9_dimensions(self, graph_simple):
        for node in graph_simple.nodes:
            assert node.all_dimensions_present(), (
                f"node {node.path} missing dimensions: "
                f"{set(Dimension) - set(node.dimensions.keys())}"
            )

    def test_every_node_has_all_9_dimensions_full(self, graph_full):
        for node in graph_full.nodes:
            assert node.all_dimensions_present()

    def test_every_node_has_all_9_dimensions_subsystems(self, graph_subsystems):
        for node in graph_subsystems.nodes:
            assert node.all_dimensions_present()

    def test_dimension_count(self):
        from orren_engine.data_model import Dimension

        assert len(list(Dimension)) == 9
        assert len(Dimension.semantic()) == 8

    def test_empty_node_carries_all_dimensions(self):
        """A freshly constructed SIRNode MUST have all 9 dimension keys
        present, even before any payload is attached."""
        node = SIRNode(path="x", name="x")
        for dim in Dimension:
            assert dim in node.dimensions
            assert node.dimensions[dim] == []

    def test_no_dimension_can_be_lost(self, graph_full):
        """If we delete a dimension key from a node, the invariant
        check returns False. This is the negative test that confirms
        the invariant check actually works."""
        node = graph_full.nodes[0]
        del node.dimensions[Dimension.VIBE]
        assert not node.all_dimensions_present()


# ---------------------------------------------------------------------------
# Parent/child composition invariants
# ---------------------------------------------------------------------------


class TestParentChild:
    def test_child_parent_path_is_prefix(self, graph_full):
        for node in graph_full.nodes:
            if node.parent is not None:
                assert node.path.startswith(node.parent.path + ".") or node.parent.path == "_root"

    def test_no_orphan_non_root_nodes(self, graph_simple):
        for node in graph_simple.nodes:
            if node.kind == "root":
                assert node.parent is None
            elif node.parent is None:
                # Allow root-level expressions like subsystems.
                assert node.kind in ("root",)

    def test_parent_children_back_reference(self, graph_full):
        for node in graph_full.nodes:
            if node.parent is not None:
                assert node in node.parent.children

    def test_children_have_same_or_greater_indent(self, graph_full):
        """Children must be deeper than parents in the path."""
        for node in graph_full.nodes:
            if node.parent is not None and node.parent.path != "_root":
                parent_depth = node.parent.path.count(".")
                child_depth = node.path.count(".")
                assert child_depth > parent_depth

    def test_subsystem_composition(self, graph_subsystems):
        """Multiple `create` blocks produce multiple root nodes; each
        is reachable in the graph."""
        names = {n.name for n in graph_subsystems.nodes}
        assert "farm_system" in names
        assert "crop_planner" in names
        assert "system_equilibrium" in names


# ---------------------------------------------------------------------------
# Path uniqueness invariant
# ---------------------------------------------------------------------------


class TestPathUniqueness:
    def test_paths_unique(self, graph_full):
        paths = [n.path for n in graph_full.nodes]
        assert len(paths) == len(set(paths)), "duplicate paths in graph"

    def test_node_ids_unique(self, graph_full):
        ids = [n.node_id for n in graph_full.nodes]
        assert len(ids) == len(set(ids))

    def test_no_path_collision_across_expressions(self, graph_subsystems):
        paths = [n.path for n in graph_subsystems.nodes]
        assert len(paths) == len(set(paths))


# ---------------------------------------------------------------------------
# Dimension attachment correctness
# ---------------------------------------------------------------------------


class TestDimensionAttachment:
    def test_cognitive_attached_to_correct_subject(self, graph_full):
        node = graph_full.find("mic_app.home.microphone_control")
        assert node is not None
        cog = node.get_dimension(Dimension.COGNITIVE)
        assert len(cog) == 4
        preds = {e["predicate"] for e in cog}
        assert "activation" in preds
        assert "recording" in preds
        assert "transcription" in preds
        assert "preservation" in preds

    def test_vibe_attached_to_correct_subject(self, graph_full):
        node = graph_full.find("mic_app.home.microphone_control")
        vibes = node.get_dimension(Dimension.VIBE)
        aspects = {e["aspect"] for e in vibes}
        assert "color_character" in aspects
        assert "form_character" in aspects
        assert "tone" in aspects

    def test_unrelated_node_has_empty_payload(self, graph_full):
        """A node that wasn't a subject of any vibe statement should
        have an empty vibe payload (but the key must still exist)."""
        home = graph_full.find("mic_app.home")
        assert home is not None
        assert home.get_dimension(Dimension.VIBE) == []
        # Key still present:
        assert Dimension.VIBE in home.dimensions

    def test_degradation_tolerance_attached(self, graph_full):
        node = graph_full.find("mic_app.home.microphone_control")
        # Two degrade rules apply to vibe on this node.
        assert any("vibe.color_character" in k for k in node.degradation_tolerance)
        assert any("cognitive.activation_logic" in k for k in node.degradation_tolerance)


# ---------------------------------------------------------------------------
# Structure tree fidelity
# ---------------------------------------------------------------------------


class TestStructureFidelity:
    def test_structure_tree_built(self, graph_full):
        root = graph_full.find("mic_app")
        assert root is not None
        # Root has one child: home
        assert len(root.children) == 1
        assert root.children[0].name == "home"
        # Home has one child: microphone_control
        home = root.children[0]
        assert len(home.children) == 1
        assert home.children[0].name == "microphone_control"
        # microphone_control has one child: icon
        mc = home.children[0]
        assert len(mc.children) == 1
        assert mc.children[0].name == "icon"

    def test_node_count_matches_structure(self, graph_full):
        # mic_app + home + microphone_control + icon = 4
        assert len(graph_full.nodes) == 4

    def test_no_structure_no_extra_nodes(self, graph_simple):
        """If structure: is provided with 2 nodes (home + microphone_control),
        plus the root, we should have 3 nodes total."""
        # graph_simple has mic_app + home + microphone_control = 3
        assert len(graph_simple.nodes) == 3


# ---------------------------------------------------------------------------
# Equilibrium and realization collection invariants
# ---------------------------------------------------------------------------


class TestGraphLevelCollections:
    def test_equilibrium_rules_collected(self):
        src = """create app : Application
    equilibrium:
        rule_one:
            when vibe.calm is active AND cognitive.activation is active
            preserve both
            resolution: x
        rule_two:
            when vibe.aesthetic is active AND cognitive.recording is active
            preserve both
            resolution: y
"""
        graph = SIRBuilder().build(CoParser().parse(src))
        assert len(graph.equilibrium_rules) == 2
        names = {r.name for r in graph.equilibrium_rules}
        assert names == {"rule_one", "rule_two"}

    def test_realization_targets_collected(self, graph_full):
        assert len(graph_full.realization_targets) == 1
        assert graph_full.realization_targets[0].name == "web_interface"

    def test_no_equilibrium_no_rules(self, graph_simple):
        assert graph_simple.equilibrium_rules == []

    def test_no_realize_no_targets(self, graph_simple):
        assert graph_simple.realization_targets == []


# ---------------------------------------------------------------------------
# Graph-level signature
# ---------------------------------------------------------------------------


class TestGraphSignature:
    def test_signature_is_string(self, graph_simple):
        sig = graph_simple.signature()
        assert isinstance(sig, str)
        assert "app" in sig  # graph_simple uses `create app : Application`

    def test_signature_includes_all_nodes(self, graph_full):
        sig = graph_full.signature()
        for node in graph_full.nodes:
            assert node.path in sig

    def test_signature_includes_all_dimensions(self, graph_full):
        """Every node signature includes all 9 dimension entries."""
        sig = graph_full.signature()
        # Each node's signature has 9 dimension entries separated by '|'
        # after path and kind. Total '|'-separated parts per node = 2 + 9 = 11.
        lines = sig.split("\n")
        for line in lines:
            parts = line.split("|")
            assert len(parts) >= 11, f"node signature missing dimensions: {line}"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_source_produces_empty_graph(self):
        graph = SIRBuilder().build([])
        assert graph.nodes == []
        assert graph.root is None

    def test_node_with_no_dimensions_still_valid(self):
        node = SIRNode(path="x", name="x")
        # Invariant: all 9 dimensions present, even if empty.
        assert node.all_dimensions_present()
        assert not node.has_dimension_content(Dimension.COGNITIVE)

    def test_set_dimension_appends(self):
        node = SIRNode(path="x", name="x")
        node.set_dimension(Dimension.VIBE, {"aspect": "tone", "term": "calm"})
        node.set_dimension(Dimension.VIBE, {"aspect": "color", "term": "emerald"})
        assert len(node.get_dimension(Dimension.VIBE)) == 2

    def test_has_dimension_content(self):
        node = SIRNode(path="x", name="x")
        assert not node.has_dimension_content(Dimension.VIBE)
        node.set_dimension(Dimension.VIBE, {"aspect": "tone", "term": "calm"})
        assert node.has_dimension_content(Dimension.VIBE)
