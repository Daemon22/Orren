"""Semantic Editor Protocol — contract tests.

Validates the editing protocol described in 07_VALIDATION_v3.md Gap 6:
    editor.modify(
        "application.home.microphone_control.icon",
        Dimension.VIBE,
        "color_character",
        "calmer",
        rationale="..."
    )

Covers:
  - Path resolution (exact, suffix, by short name, ambiguous, not found)
  - modify / relocate / redefine / add / remove
  - undo / redo (incl. stack discipline)
  - search by dimension / property / value
  - dirty tracking
  - rationale + timestamp recording

Run: pytest tests/test_02_semantic_editor.py -v
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from orren_engine import (
    CoParser,
    Dimension,
    EditOp,
    SIRBuilder,
    SemanticEditor,
)
from orren_engine.data_model import SIRNode


# ---------------------------------------------------------------------------
# Fixture: a small graph for editor tests
# ---------------------------------------------------------------------------

SOURCE = """create mic_app : Application

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


@pytest.fixture
def editor():
    parser = CoParser()
    exprs = parser.parse(SOURCE)
    builder = SIRBuilder()
    graph = builder.build(exprs)
    return SemanticEditor(graph)


# ---------------------------------------------------------------------------
# Path resolution contract
# ---------------------------------------------------------------------------


class TestPathResolution:
    def test_exact_path(self, editor):
        node = editor.resolve("mic_app.home.microphone_control")
        assert node is not None
        assert node.name == "microphone_control"

    def test_suffix_path_unique(self, editor):
        node = editor.resolve("microphone_control")
        assert node is not None
        assert node.path == "mic_app.home.microphone_control"

    def test_short_name_unique(self, editor):
        node = editor.resolve("home")
        assert node is not None
        assert node.path == "mic_app.home"

    def test_not_found_returns_none(self, editor):
        assert editor.resolve("nonexistent.thing") is None

    def test_root_path(self, editor):
        node = editor.resolve("mic_app")
        assert node is not None
        assert node.kind == "root"

    def test_resolve_raises_on_require(self, editor):
        with pytest.raises(KeyError):
            editor._require("no.such.path")


# ---------------------------------------------------------------------------
# Modify operation contract
# ---------------------------------------------------------------------------


class TestModify:
    def test_modify_changes_value(self, editor):
        editor.modify(
            "microphone_control",
            Dimension.VIBE,
            "color_character",
            "calmer emerald",
            rationale="User wants calmer",
        )
        node = editor.resolve("microphone_control")
        # The modify writes the property on the matching payload entry.
        found = False
        for entry in node.get_dimension(Dimension.VIBE):
            if isinstance(entry, dict) and entry.get("aspect") == "color_character":
                assert entry["term"] == "calmer emerald"
                found = True
        assert found

    def test_modify_marks_dirty(self, editor):
        editor.modify(
            "microphone_control",
            Dimension.VIBE,
            "tone",
            "warmer",
        )
        node = editor.resolve("microphone_control")
        assert node.dirty is True

    def test_modify_records_old_value(self, editor):
        op = editor.modify(
            "microphone_control",
            Dimension.VIBE,
            "color_character",
            "calmer emerald",
        )
        assert op.old_value == "emerald"
        assert op.new_value == "calmer emerald"

    def test_modify_records_rationale(self, editor):
        op = editor.modify(
            "microphone_control",
            Dimension.VIBE,
            "tone",
            "warmer",
            rationale="User wants warmer",
        )
        assert op.rationale == "User wants warmer"

    def test_modify_records_timestamp(self, editor):
        op = editor.modify(
            "microphone_control", Dimension.VIBE, "tone", "warmer"
        )
        assert op.timestamp != ""
        assert "T" in op.timestamp  # ISO 8601

    def test_modify_clears_redo_stack(self, editor):
        editor.modify("microphone_control", Dimension.VIBE, "tone", "warmer")
        editor.undo()
        assert editor.can_redo()
        editor.modify("microphone_control", Dimension.VIBE, "tone", "cooler")
        assert not editor.can_redo()


# ---------------------------------------------------------------------------
# Relocate operation contract
# ---------------------------------------------------------------------------


class TestRelocate:
    def test_relocate_moves_node(self, editor):
        # Move microphone_control from home to mic_app root.
        editor.relocate("microphone_control", "mic_app")
        # Old path no longer resolves.
        assert editor.resolve("mic_app.home.microphone_control") is None
        # New path resolves.
        node = editor.resolve("mic_app.microphone_control")
        assert node is not None

    def test_relocate_updates_parent_children(self, editor):
        editor.relocate("microphone_control", "mic_app")
        home = editor.resolve("home")
        assert home.children == []
        root = editor.resolve("mic_app")
        assert any(c.name == "microphone_control" for c in root.children)

    def test_relocate_marks_dirty(self, editor):
        editor.relocate("microphone_control", "mic_app")
        node = editor.resolve("mic_app.microphone_control")
        assert node.dirty


# ---------------------------------------------------------------------------
# Redefine operation contract
# ---------------------------------------------------------------------------


class TestRedefine:
    def test_redefine_changes_kind(self, editor):
        editor.redefine("microphone_control", "subsystem")
        node = editor.resolve("microphone_control")
        assert node.kind == "subsystem"

    def test_redefine_records_old_kind(self, editor):
        op = editor.redefine("microphone_control", "subsystem")
        assert op.old_value == "entity"
        assert op.new_value == "subsystem"


# ---------------------------------------------------------------------------
# Add / Remove operation contract
# ---------------------------------------------------------------------------


class TestAddRemove:
    def test_add_appends_payload(self, editor):
        before = len(editor.resolve("microphone_control").get_dimension(Dimension.VIBE))
        editor.add(
            "microphone_control",
            Dimension.VIBE,
            {"aspect": "intensity", "term": "low"},
        )
        after = len(editor.resolve("microphone_control").get_dimension(Dimension.VIBE))
        assert after == before + 1

    def test_remove_deletes_payload(self, editor):
        before = len(editor.resolve("microphone_control").get_dimension(Dimension.VIBE))
        editor.remove("microphone_control", Dimension.VIBE, "color_character")
        after = len(editor.resolve("microphone_control").get_dimension(Dimension.VIBE))
        assert after == before - 1


# ---------------------------------------------------------------------------
# Undo / Redo contract
# ---------------------------------------------------------------------------


class TestUndoRedo:
    def test_undo_restores_value(self, editor):
        editor.modify("microphone_control", Dimension.VIBE, "color_character", "red")
        editor.undo()
        # Find the color_character entry and check it's back to emerald.
        node = editor.resolve("microphone_control")
        for entry in node.get_dimension(Dimension.VIBE):
            if isinstance(entry, dict) and entry.get("aspect") == "color_character":
                assert entry["term"] == "emerald"

    def test_redo_reapplies_value(self, editor):
        editor.modify("microphone_control", Dimension.VIBE, "color_character", "red")
        editor.undo()
        editor.redo()
        node = editor.resolve("microphone_control")
        for entry in node.get_dimension(Dimension.VIBE):
            if isinstance(entry, dict) and entry.get("aspect") == "color_character":
                assert entry["term"] == "red"

    def test_undo_empty_history_returns_none(self, editor):
        assert editor.undo() is None

    def test_redo_empty_stack_returns_none(self, editor):
        assert editor.redo() is None

    def test_multiple_undo_redo(self, editor):
        editor.modify("microphone_control", Dimension.VIBE, "color_character", "red")
        editor.modify("microphone_control", Dimension.VIBE, "color_character", "blue")
        editor.modify("microphone_control", Dimension.VIBE, "color_character", "green")
        # Undo all three
        editor.undo()
        editor.undo()
        editor.undo()
        node = editor.resolve("microphone_control")
        for entry in node.get_dimension(Dimension.VIBE):
            if isinstance(entry, dict) and entry.get("aspect") == "color_character":
                assert entry["term"] == "emerald"
        # Redo all three
        editor.redo()
        editor.redo()
        editor.redo()
        for entry in node.get_dimension(Dimension.VIBE):
            if isinstance(entry, dict) and entry.get("aspect") == "color_character":
                assert entry["term"] == "green"

    def test_undo_relocate_restores_position(self, editor):
        editor.relocate("microphone_control", "mic_app")
        assert editor.resolve("mic_app.microphone_control") is not None
        editor.undo()
        # Should be back at mic_app.home.microphone_control
        assert editor.resolve("mic_app.home.microphone_control") is not None

    def test_undo_addremoves_payload(self, editor):
        before = len(editor.resolve("microphone_control").get_dimension(Dimension.VIBE))
        editor.add(
            "microphone_control",
            Dimension.VIBE,
            {"aspect": "intensity", "term": "low"},
        )
        assert len(editor.resolve("microphone_control").get_dimension(Dimension.VIBE)) == before + 1
        editor.undo()
        assert len(editor.resolve("microphone_control").get_dimension(Dimension.VIBE)) == before


# ---------------------------------------------------------------------------
# Search contract
# ---------------------------------------------------------------------------


class TestSearch:
    def test_search_by_dimension(self, editor):
        results = editor.search(dimension=Dimension.VIBE)
        # Only microphone_control has vibe payload.
        assert len(results) == 1
        assert results[0].name == "microphone_control"

    def test_search_by_value(self, editor):
        results = editor.search(value="emerald")
        assert any(n.name == "microphone_control" for n in results)

    def test_search_by_dimension_and_value(self, editor):
        results = editor.search(dimension=Dimension.VIBE, value="calm")
        assert len(results) == 1
        assert results[0].name == "microphone_control"

    def test_search_no_match(self, editor):
        results = editor.search(value="nonexistent_term")
        assert results == []


# ---------------------------------------------------------------------------
# Dirty tracking contract
# ---------------------------------------------------------------------------


class TestDirtyTracking:
    def test_no_dirty_initially(self, editor):
        assert editor.dirty_nodes() == []

    def test_dirty_after_modify(self, editor):
        editor.modify("microphone_control", Dimension.VIBE, "tone", "warm")
        dirty = editor.dirty_nodes()
        assert len(dirty) == 1
        assert dirty[0].name == "microphone_control"

    def test_mark_clean(self, editor):
        editor.modify("microphone_control", Dimension.VIBE, "tone", "warm")
        editor.mark_clean()
        assert editor.dirty_nodes() == []

    def test_undo_does_not_clear_dirty(self, editor):
        # Undo reverses the value but the node is still 'dirty' in the
        # sense that it has been touched. (Implementations may differ;
        # this contract requires only that the dirty flag remains set
        # so re-realization can be triggered.)
        editor.modify("microphone_control", Dimension.VIBE, "tone", "warm")
        editor.undo()
        assert editor.resolve("microphone_control").dirty


# ---------------------------------------------------------------------------
# History discipline contract
# ---------------------------------------------------------------------------


class TestHistoryDiscipline:
    def test_history_grows_with_each_op(self, editor):
        assert len(editor.history) == 0
        editor.modify("microphone_control", Dimension.VIBE, "tone", "warm")
        assert len(editor.history) == 1
        editor.add("microphone_control", Dimension.VIBE, {"aspect": "x", "term": "y"})
        assert len(editor.history) == 2

    def test_redo_stack_grows_with_undo(self, editor):
        editor.modify("microphone_control", Dimension.VIBE, "tone", "warm")
        assert len(editor.redo_stack) == 0
        editor.undo()
        assert len(editor.redo_stack) == 1

    def test_op_has_unique_id(self, editor):
        op1 = editor.modify("microphone_control", Dimension.VIBE, "tone", "warm")
        op2 = editor.modify("microphone_control", Dimension.VIBE, "tone", "cool")
        assert op1.edit_id != op2.edit_id

    def test_op_records_op_type(self, editor):
        op = editor.modify("microphone_control", Dimension.VIBE, "tone", "warm")
        assert op.op == EditOp.MODIFY
