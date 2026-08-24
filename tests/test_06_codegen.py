"""Code generator correctness tests against a small standard library.

Validates that for each of the 5 standard targets, the generator emits:
  - Syntactically reasonable code (parseable Python / HTML / CSS / JS / Swift)
  - Code that reflects the semantic content (entities, vibes, conditions)
  - Explicit PROXY / BRIDGE markers where the target cannot fully express
    a dimension
  - Stable output (same input → same code, byte-for-byte)

The "small standard library" is the canonical microphone example from
the architecture document, with all 5 realization targets declared.

Run: pytest tests/test_06_codegen.py -v
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from orren_engine import (
    CoParser,
    Dimension,
    RealizationCoordinator,
    SIRBuilder,
    generate_code,
)


# ---------------------------------------------------------------------------
# Canonical source — the "small standard library"
# ---------------------------------------------------------------------------

CANONICAL_SOURCE = """create microphone_application : Application

    context:
        purpose: a microphone control on the home screen

    structure:
        home
            microphone_control

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

    conditional:
        microphone_control activates on double_click
        microphone_control activates on volume_down × 2
        original_audio retained always (unconditional preservation)

    behavior:
        microphone_control transitions from idle to active on activation_intent
        microphone_control lifecycle: idle -> active -> recording -> processing -> idle

    degrade:
        require full for cognitive on activation_logic
        tolerate faithful for vibe on color_character
        tolerate proxy for vibe on aesthetic

    realize:
        target: web_interface (HTML/CSS/JS)
            capabilities: layout, color, motion, event_handling
            can_express: spatial, conditional, behavioral
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


@pytest.fixture(scope="module")
def graph_and_targets():
    parser = CoParser()
    exprs = parser.parse(CANONICAL_SOURCE)
    graph = SIRBuilder().build(exprs)
    return graph, graph.realization_targets


# ---------------------------------------------------------------------------
# Web target
# ---------------------------------------------------------------------------


class TestWebCodegen:
    def test_produces_three_files(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "web_interface")
        files = generate_code(graph, tgt)
        assert "web_interface/index.html" in files
        assert "web_interface/styles.css" in files
        assert "web_interface/app.js" in files

    def test_html_has_doctype(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "web_interface")
        html = generate_code(graph, tgt)["web_interface/index.html"]
        assert html.startswith("<!DOCTYPE html>")

    def test_html_includes_entity_div(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "web_interface")
        html = generate_code(graph, tgt)["web_interface/index.html"]
        assert "microphone_control" in html
        assert '<div id="' in html

    def test_css_has_emerald_color(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "web_interface")
        css = generate_code(graph, tgt)["web_interface/styles.css"]
        # emerald should map to a green hex.
        assert "#2ecc71" in css.lower() or "emerald" in css.lower()

    def test_css_marks_aesthetic_as_proxy(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "web_interface")
        css = generate_code(graph, tgt)["web_interface/styles.css"]
        # The aesthetic vibe ('music for idealists') is declared as
        # cannot_express, so the generator must mark it PROXY.
        assert "PROXY" in css

    def test_js_has_double_click_handler(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "web_interface")
        js = generate_code(graph, tgt)["web_interface/app.js"]
        assert "dblclick" in js
        assert "addEventListener" in js

    def test_js_marks_volume_down_as_bridge(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "web_interface")
        js = generate_code(graph, tgt)["web_interface/app.js"]
        # volume_down is not directly available on web; must be marked BRIDGE.
        assert "BRIDGE" in js

    def test_js_includes_lifecycle(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "web_interface")
        js = generate_code(graph, tgt)["web_interface/app.js"]
        assert "lifecycle" in js.lower()
        assert "idle" in js


# ---------------------------------------------------------------------------
# Native shell target (Swift)
# ---------------------------------------------------------------------------


class TestNativeShellCodegen:
    def test_produces_swift_file(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "native_shell")
        files = generate_code(graph, tgt)
        assert "native_shell/Main.swift" in files

    def test_swift_imports_uikit(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "native_shell")
        swift = generate_code(graph, tgt)["native_shell/Main.swift"]
        assert "import UIKit" in swift

    def test_swift_imports_avfoundation_for_microphone(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "native_shell")
        swift = generate_code(graph, tgt)["native_shell/Main.swift"]
        # cognitive.activation is present → AVFoundation must be imported.
        assert "import AVFoundation" in swift

    def test_swift_has_microphone_activation(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "native_shell")
        swift = generate_code(graph, tgt)["native_shell/Main.swift"]
        assert "activateMicrophone" in swift
        assert "audioEngine" in swift

    def test_swift_class_name_derived_from_app_name(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "native_shell")
        swift = generate_code(graph, tgt)["native_shell/Main.swift"]
        # Application name is 'microphone_application' → class MicrophoneApplication.
        assert "class MicrophoneApplication" in swift

    def test_swift_includes_entity_views(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "native_shell")
        swift = generate_code(graph, tgt)["native_shell/Main.swift"]
        assert "microphone_control" in swift
        assert "UIView" in swift


# ---------------------------------------------------------------------------
# Transcription service target (Python)
# ---------------------------------------------------------------------------


class TestTranscriptionServiceCodegen:
    def test_produces_python_file(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "transcription_service")
        files = generate_code(graph, tgt)
        assert "transcription_service/transcription.py" in files

    def test_python_is_parseable(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "transcription_service")
        code = generate_code(graph, tgt)["transcription_service/transcription.py"]
        # Must parse as valid Python.
        compile(code, "<transcription.py>", "exec")

    def test_has_transcribe_function(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "transcription_service")
        code = generate_code(graph, tgt)["transcription_service/transcription.py"]
        assert "def transcribe(" in code
        assert "def transcribe_with_metadata(" in code

    def test_marks_proxy_for_actual_backend(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "transcription_service")
        code = generate_code(graph, tgt)["transcription_service/transcription.py"]
        # The actual STT backend isn't bundled → must be marked PROXY.
        assert "PROXY" in code

    def test_preservation_referenced(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "transcription_service")
        code = generate_code(graph, tgt)["transcription_service/transcription.py"]
        # The transcription service should note that original_audio is
        # preserved upstream (not its responsibility).
        assert "preservation" in code.lower() or "preserved" in code.lower()


# ---------------------------------------------------------------------------
# Audio storage target (Python)
# ---------------------------------------------------------------------------


class TestAudioStorageCodegen:
    def test_produces_python_file(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "audio_storage")
        files = generate_code(graph, tgt)
        assert "audio_storage/storage.py" in files

    def test_python_is_parseable(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "audio_storage")
        code = generate_code(graph, tgt)["audio_storage/storage.py"]
        compile(code, "<storage.py>", "exec")

    def test_has_retain_function(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "audio_storage")
        code = generate_code(graph, tgt)["audio_storage/storage.py"]
        assert "def retain(" in code
        assert "def retrieve(" in code

    def test_marks_unconditional_preservation(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "audio_storage")
        code = generate_code(graph, tgt)["audio_storage/storage.py"]
        # The preservation contract is unconditional — must be in the code.
        assert "unconditional" in code.lower()

    def test_writes_manifest_sidecar(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "audio_storage")
        code = generate_code(graph, tgt)["audio_storage/storage.py"]
        assert "manifest" in code.lower()


# ---------------------------------------------------------------------------
# Input button watcher target (Python)
# ---------------------------------------------------------------------------


class TestInputButtonWatcherCodegen:
    def test_produces_python_file(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "input_button_watcher")
        files = generate_code(graph, tgt)
        assert "input_button_watcher/input_watcher.py" in files

    def test_python_is_parseable(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "input_button_watcher")
        code = generate_code(graph, tgt)["input_button_watcher/input_watcher.py"]
        compile(code, "<input_watcher.py>", "exec")

    def test_has_double_click_detection(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "input_button_watcher")
        code = generate_code(graph, tgt)["input_button_watcher/input_watcher.py"]
        assert "double_click" in code
        assert "DOUBLE_CLICK_WINDOW" in code

    def test_has_volume_down_detection(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "input_button_watcher")
        code = generate_code(graph, tgt)["input_button_watcher/input_watcher.py"]
        assert "volume_down" in code
        assert "VOLUME_DOWN_SEQUENCE" in code

    def test_fires_activation_callback(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "input_button_watcher")
        code = generate_code(graph, tgt)["input_button_watcher/input_watcher.py"]
        assert "_fire_activation" in code
        assert "on_activation" in code


# ---------------------------------------------------------------------------
# Output stability
# ---------------------------------------------------------------------------


class TestCodegenStability:
    def test_same_input_same_output(self, graph_and_targets):
        graph, targets = graph_and_targets
        for tgt in targets:
            files1 = generate_code(graph, tgt)
            files2 = generate_code(graph, tgt)
            for fname in files1:
                assert files1[fname] == files2[fname], f"unstable output for {fname}"

    def test_output_stable_across_rebuilds(self, graph_and_targets):
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "web_interface")
        first_run = generate_code(graph, tgt)
        # Re-build the graph from scratch and regenerate.
        graph2 = SIRBuilder().build(CoParser().parse(CANONICAL_SOURCE))
        second_run = generate_code(graph2, tgt)
        for fname in first_run:
            assert first_run[fname] == second_run[fname]


# ---------------------------------------------------------------------------
# Degradation visibility
# ---------------------------------------------------------------------------


class TestDegradationVisibility:
    def test_proxy_markers_present_when_declared(self, graph_and_targets):
        """When degrade: tolerate proxy is declared, the generated code
        must contain a PROXY marker for that aspect."""
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "web_interface")
        css = generate_code(graph, tgt)["web_interface/styles.css"]
        # vibe on aesthetic is tolerated as proxy.
        assert "PROXY" in css

    def test_bridge_markers_present_when_needs_bridge(self, graph_and_targets):
        """When realize: needs_bridge is declared, the generated code
        must contain a BRIDGE marker."""
        graph, targets = graph_and_targets
        tgt = next(t for t in targets if t.name == "web_interface")
        js = generate_code(graph, tgt)["web_interface/app.js"]
        # device_microphone needs a bridge on web.
        assert "BRIDGE" in js


# ---------------------------------------------------------------------------
# Coordinator integration
# ---------------------------------------------------------------------------


class TestCoordinatorIntegration:
    def test_coordinator_artifacts_have_output_files(self, graph_and_targets):
        graph, targets = graph_and_targets
        artifacts = RealizationCoordinator().coordinate(graph)
        # 5 targets → 5 artifacts.
        assert len(artifacts) == 5
        for art in artifacts:
            assert len(art.output_files) > 0
            assert art.preservation_score > 0.0

    def test_artifact_and_codegen_agree_on_target(self, graph_and_targets):
        graph, targets = graph_and_targets
        artifacts = RealizationCoordinator().coordinate(graph)
        for art, tgt in zip(artifacts, targets):
            assert art.target_name == tgt.name
            assert art.target_language == tgt.language
            # Codegen should produce files for every artifact.
            files = generate_code(graph, tgt)
            assert len(files) > 0
