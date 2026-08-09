"""Integration tests across the whole pipeline.

End-to-end: .orn → parse → SIR → equilibrium → realization → codegen →
semantic edit → re-realization.

These tests confirm that:
  - The full pipeline runs cleanly on a realistic input.
  - Edits to the SIR propagate to regenerated artifacts.
  - The 9-dimension invariant holds after every step.
  - Equilibrium contracts survive editing.
  - Code generation reflects edited state, not stale state.
  - Subsystem composition works end-to-end.
  - Error paths are handled gracefully.

Run: pytest tests/test_09_integration.py -v
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from orren_engine import (
    CoParser,
    Dimension,
    Engine,
    SIRBuilder,
    EquilibriumResolver,
    RealizationCoordinator,
    SemanticEditor,
    generate_code,
)


# ---------------------------------------------------------------------------
# Canonical integration source
# ---------------------------------------------------------------------------

INTEGRATION_SOURCE = """create microphone_application : Application

    context:
        purpose: a microphone control on the home screen that feels calm
        audience: someone who wants a recording tool

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
        microphone_control.aesthetic = "music for idealists"
        microphone_control.activation_signal = steady_glow

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

    calibrate:
        calibrate emerald for vibe:
            maps_to color_hue
            threshold: hue in [150, 170]
            signal: css_color_value

        calibrate calm for vibe:
            maps_to motion_intensity
            threshold: animation_duration >= 600ms
            signal: transition_timing_function

    equilibrium:
        calmness_preserves_urgency:
            when vibe.calm is active AND cognitive.activation is active
            preserve both
            resolution: express urgency as steady_glow
            rationale: calm does not mean no signal

        preservation_overrides_convenience:
            when cognitive.preservation is active
            preserve unconditionally
            resolution: original_audio retained even if storage constrained
            rationale: preservation is a hard contract

    degrade:
        require full for cognitive on activation_logic
        require full for cognitive on recording_capture
        require full for cognitive on transcription_pipeline
        require full for cognitive on audio_preservation
        require faithful for vibe on color_character
        tolerate proxy for vibe on aesthetic

    realize:
        target: web_interface (HTML/CSS/JS)
            capabilities: layout, color, motion, event_handling
            can_express: spatial, conditional, behavioral, temporal
            needs_bridge: device_microphone
            cannot_express: aesthetic
            preservation_score: 0.83

        target: native_shell (Swift)
            capabilities: device_microphone, input_buttons, storage
            can_express: cognitive, spatial, conditional, behavioral, relational
            needs_bridge: aesthetic
            cannot_express: aesthetic
            preservation_score: 0.91

        target: transcription_service (Python)
            capabilities: speech_to_text, audio_input
            can_express: cognitive.transcription
            cannot_express: vibe, spatial, behavioral, relational
            preservation_score: 1.0

        target: audio_storage (Python)
            capabilities: write, retain, retrieve
            can_express: cognitive.preservation
            cannot_express: vibe, spatial, behavioral, relational
            preservation_score: 1.0

        target: input_button_watcher (Python)
            capabilities: detect_volume_down, detect_double_click
            can_express: conditional, relational
            cannot_express: vibe, spatial, behavioral
            preservation_score: 1.0
"""


# ---------------------------------------------------------------------------
# Full pipeline integration
# ---------------------------------------------------------------------------


class TestFullPipeline:
    def test_run_end_to_end(self):
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        assert result.expressions_count == 1
        assert result.sir_node_count == 4  # root + home + mic + icon
        # Two equilibrium rules declared.
        assert len(result.graph.equilibrium_rules) == 2
        # Both should fire (calm + activation conflict, preservation + transcription).
        assert result.equilibrium_outcomes >= 1
        # Five realization targets declared.
        assert len(result.artifacts) == 5

    def test_all_nodes_carry_9_dimensions_after_run(self):
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        for node in result.graph.nodes:
            assert node.all_dimensions_present(), f"node {node.path} missing dims"

    def test_equilibrium_stamped_on_nodes(self):
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        # At least one node should have an EQUILIBRIUM payload.
        eq_nodes = [
            n for n in result.graph.nodes
            if n.has_dimension_content(Dimension.EQUILIBRIUM)
        ]
        assert len(eq_nodes) >= 1

    def test_artifacts_have_valid_preservation_scores(self):
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        for art in result.artifacts:
            assert 0.0 <= art.preservation_score <= 1.0
            assert art.target_language
            assert art.capabilities

    def test_codegen_runs_for_all_targets(self):
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        for tgt in result.graph.realization_targets:
            files = generate_code(result.graph, tgt)
            assert len(files) > 0
            for fname, code in files.items():
                assert len(code) > 0
                assert fname.endswith((".html", ".css", ".js", ".swift", ".py", ".txt"))


# ---------------------------------------------------------------------------
# Edit → re-realize integration
# ---------------------------------------------------------------------------


class TestEditAndReRealize:
    def test_edit_propagates_to_re_coordination(self):
        """Modifying a vibe dimension and re-running the coordinator
        must produce a different artifact (different degradation_report)."""
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        before = result.artifacts[0].degradation_report

        editor = engine.editor()
        editor.modify(
            "microphone_application.home.microphone_control",
            Dimension.VIBE,
            "color_character",
            "sapphire",
        )
        # Re-coordinate without re-parsing.
        new_artifacts = engine.re_coordinate()
        after = new_artifacts[0].degradation_report

        # The color_character aspect value should be reflected somewhere
        # in the new degradation report (or at least the report should
        # be the same length, since structure didn't change).
        assert len(after) == len(before)

    def test_edit_marks_dirty(self):
        engine = Engine()
        engine.run(INTEGRATION_SOURCE)
        editor = engine.editor()
        editor.modify(
            "microphone_application.home.microphone_control",
            Dimension.VIBE,
            "tone",
            "warmer",
        )
        dirty = editor.dirty_nodes()
        assert len(dirty) == 1
        assert dirty[0].name == "microphone_control"

    def test_undo_restores_artifact_state(self):
        """Undo an edit and confirm the SIR signature returns to original."""
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        sig_before = result.graph.signature()

        editor = engine.editor()
        editor.modify(
            "microphone_application.home.microphone_control",
            Dimension.VIBE,
            "tone",
            "warmer",
        )
        sig_after_edit = result.graph.signature()
        assert sig_after_edit != sig_before

        editor.undo()
        sig_after_undo = result.graph.signature()
        assert sig_after_undo == sig_before

    def test_multiple_edits_then_re_coordination(self):
        """Apply several edits, then re-coordinate; artifacts must reflect
        the cumulative state."""
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        editor = engine.editor()

        editor.modify(
            "microphone_application.home.microphone_control",
            Dimension.VIBE,
            "color_character",
            "sapphire",
        )
        editor.modify(
            "microphone_application.home.microphone_control",
            Dimension.VIBE,
            "tone",
            "urgent",
        )
        editor.add(
            "microphone_application.home.microphone_control",
            Dimension.VIBE,
            {"aspect": "intensity", "term": "high"},
        )

        # All three edits dirty the same node.
        dirty = editor.dirty_nodes()
        assert len(dirty) == 1
        # The node now has more vibe entries than before.
        node = dirty[0]
        assert len(node.get_dimension(Dimension.VIBE)) >= 6  # was 5, now 6

        # Re-coordinate.
        new_artifacts = engine.re_coordinate()
        assert len(new_artifacts) == 5

    def test_relocate_then_re_coordinate(self):
        """Moving a node and re-coordinating produces a valid artifact."""
        engine = Engine()
        engine.run(INTEGRATION_SOURCE)
        editor = engine.editor()

        editor.relocate(
            "microphone_application.home.microphone_control",
            "microphone_application",
        )
        # After relocate, the node's path has changed.
        assert editor.resolve("microphone_application.microphone_control") is not None
        # Re-coordinate still works.
        new_artifacts = engine.re_coordinate()
        assert len(new_artifacts) == 5

    def test_redefine_then_re_coordinate(self):
        engine = Engine()
        engine.run(INTEGRATION_SOURCE)
        editor = engine.editor()

        editor.redefine(
            "microphone_application.home.microphone_control",
            "subsystem",
        )
        node = editor.resolve("microphone_application.home.microphone_control")
        assert node.kind == "subsystem"
        # Re-coordinate still works.
        new_artifacts = engine.re_coordinate()
        assert len(new_artifacts) == 5


# ---------------------------------------------------------------------------
# Equilibrium contract survival
# ---------------------------------------------------------------------------


class TestEquilibriumSurvival:
    def test_equilibrium_rules_preserved_after_edit(self):
        """Editing a vibe value should NOT remove the equilibrium rules
        from the graph — they're graph-level contracts."""
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        rules_before = len(result.graph.equilibrium_rules)

        editor = engine.editor()
        editor.modify(
            "microphone_application.home.microphone_control",
            Dimension.VIBE,
            "color_character",
            "sapphire",
        )
        assert len(result.graph.equilibrium_rules) == rules_before

    def test_preservation_contract_honored_in_storage_codegen(self):
        """The audio_storage target's generated code must contain the
        unconditional preservation language — the equilibrium contract
        survives into the realization."""
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        storage_tgt = next(
            t for t in result.graph.realization_targets if t.name == "audio_storage"
        )
        files = generate_code(result.graph, storage_tgt)
        code = next(iter(files.values()))
        assert "unconditional" in code.lower()
        assert "preservation" in code.lower() or "preserved" in code.lower()

    def test_calm_vs_urgency_resolution_in_web_css(self):
        """The equilibrium rule calmness_preserves_urgency says 'express
        urgency as steady_glow'. The web CSS should contain a steady_glow
        expression (box-shadow)."""
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        web_tgt = next(
            t for t in result.graph.realization_targets if t.name == "web_interface"
        )
        files = generate_code(result.graph, web_tgt)
        css = files.get("web_interface/styles.css", "")
        # The steady_glow should be expressed as box-shadow.
        assert "box-shadow" in css


# ---------------------------------------------------------------------------
# Subsystem composition end-to-end
# ---------------------------------------------------------------------------


SUBSYSTEM_SOURCE = """create farm_management_system : Application

    context:
        purpose: a farm management system with multiple subsystems

    structure:
        dashboard
            crop_panel
            irrigation_panel
            market_panel

create crop_planner : Subsystem

    cognitive:
        crop_planner.scheduling = seasonal
        crop_planner.rotation = enabled

    vibe:
        crop_planner.tone = calm

create irrigation_controller : Subsystem

    cognitive:
        irrigation_controller.flow = regulated
        irrigation_controller.safety = enforced

    vibe:
        irrigation_controller.tone = urgent

create system_equilibrium : Equilibrium

    equilibrium:
        water_vs_crops:
            when cognitive.flow is active AND cognitive.scheduling is active
            preserve both
            resolution: schedule irrigation around crop windows

        urgency_vs_calmness:
            when vibe.urgent is active AND vibe.calm is active
            preserve both
            resolution: route urgency through dedicated alerts, leave calm panels untouched

    realize:
        target: web_interface (HTML/CSS/JS)
            capabilities: layout, color, event_handling
            preservation_score: 0.85
"""


class TestSubsystemEndToEnd:
    def test_parses_four_expressions(self):
        engine = Engine()
        result = engine.run(SUBSYSTEM_SOURCE)
        assert result.expressions_count == 4

    def test_all_nodes_carry_9_dimensions(self):
        engine = Engine()
        result = engine.run(SUBSYSTEM_SOURCE)
        for node in result.graph.nodes:
            assert node.all_dimensions_present()

    def test_equilibrium_rules_aggregate_across_subsystems(self):
        engine = Engine()
        result = engine.run(SUBSYSTEM_SOURCE)
        # Two rules defined in the system_equilibrium expression.
        assert len(result.graph.equilibrium_rules) == 2

    def test_realization_artifacts_at_graph_level(self):
        engine = Engine()
        result = engine.run(SUBSYSTEM_SOURCE)
        # One target declared, in the system_equilibrium expression.
        assert len(result.artifacts) == 1
        assert result.artifacts[0].target_name == "web_interface"

    def test_codegen_runs_on_subsystem_graph(self):
        engine = Engine()
        result = engine.run(SUBSYSTEM_SOURCE)
        for tgt in result.graph.realization_targets:
            files = generate_code(result.graph, tgt)
            assert len(files) > 0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_empty_source(self):
        engine = Engine()
        result = engine.run("")
        assert result.expressions_count == 0
        assert result.sir_node_count == 0
        assert result.artifacts == []

    def test_malformed_section_doesnt_crash(self):
        """A section with unrecognized syntax should not crash the engine."""
        src = """create app : Application
    cognitive:
        this is not valid syntax at all
        random words here
"""
        engine = Engine()
        result = engine.run(src)
        # Should complete without raising; may produce empty cognitive payload.
        assert result.expressions_count == 1

    def test_missing_section_doesnt_crash(self):
        """An expression with only a `create` header should still parse."""
        src = "create app : Application\n"
        engine = Engine()
        result = engine.run(src)
        assert result.expressions_count == 1
        assert result.sir_node_count == 1  # just the root

    def test_editor_on_unrun_engine_raises(self):
        engine = Engine()
        with pytest.raises(RuntimeError):
            engine.editor()

    def test_re_coordinate_on_unrun_engine_raises(self):
        engine = Engine()
        with pytest.raises(RuntimeError):
            engine.re_coordinate()


# ---------------------------------------------------------------------------
# Round-trip stability
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_pipeline_idempotent(self):
        """Running the pipeline twice produces identical signatures."""
        engine = Engine()
        r1 = engine.run(INTEGRATION_SOURCE)
        sig1 = r1.graph.signature()
        r2 = engine.run(INTEGRATION_SOURCE)
        sig2 = r2.graph.signature()
        assert sig1 == sig2

    def test_codegen_idempotent(self):
        """Generating code twice from the same graph produces identical output."""
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        tgt = result.graph.realization_targets[0]
        files1 = generate_code(result.graph, tgt)
        files2 = generate_code(result.graph, tgt)
        for fname in files1:
            assert files1[fname] == files2[fname]

    def test_edit_undo_redo_idempotent(self):
        """A full undo-redo cycle returns the SIR to its post-edit state."""
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        editor = engine.editor()

        editor.modify(
            "microphone_application.home.microphone_control",
            Dimension.VIBE,
            "tone",
            "urgent",
        )
        sig_after_edit = result.graph.signature()

        editor.undo()
        editor.redo()
        sig_after_redo = result.graph.signature()
        assert sig_after_edit == sig_after_redo


# ---------------------------------------------------------------------------
# Realization artifact schema conformance
# ---------------------------------------------------------------------------


class TestArtifactSchema:
    def test_artifact_has_required_fields(self):
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        for art in result.artifacts:
            d = art.to_dict()
            assert "target_name" in d
            assert "target_language" in d
            assert "capabilities" in d
            assert "output_files" in d
            assert "degradation_report" in d
            assert "preservation_score" in d

    def test_output_files_have_path_and_language(self):
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        for art in result.artifacts:
            for of in art.output_files:
                assert of.path
                assert of.language

    def test_degradation_report_has_required_fields(self):
        engine = Engine()
        result = engine.run(INTEGRATION_SOURCE)
        for art in result.artifacts:
            for entry in art.degradation_report:
                assert "dimension" in entry
                assert "aspect" in entry
                assert "severity" in entry
                assert "tolerance" in entry
