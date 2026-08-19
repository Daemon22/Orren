"""Adversarial fail-closed conformance tests.

Verifies that the conformance harness can detect and reject bad input — and
that it never silently reports PASS for something that is not genuinely valid.

Each AC-* test case corresponds to a finding in the acceptance criteria:

    AC-5.1  Python syntax error  → FAIL
    AC-5.2  JavaScript syntax error → FAIL
    AC-5.3  HTML malformed markup → FAIL or DEGRADED (never PASS)
    AC-5.4  CSS empty stylesheet → FAIL
    AC-5.5  Proxy degradation    → FAIL or DEGRADED (never PASS)

The fail-closed principle is non-negotiable: if required meaning cannot be
expressed, the system must FAIL, not proxy-and-pass.

Run: pytest tests/test_22_adversarial_conformance.py -v
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Ensure the repo root is importable.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from orren_engine.conformance_sovereign import (  # noqa: E402
    Status,
    check_file,
    run_conformance,
    write_report,
)
from orren_engine.cli import (  # noqa: E402
    _detect_proxy,
    _has_executable_realisation,
    _language_for_file,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ADVERSARIAL_ORN = """\
create microphone_app : Application

    context:
        purpose: a microphone control that captures audio through the device
                 microphone and feels calm, organic, emerald and musical

    structure:
        home
            microphone_control

    cognitive:
        microphone_control.activation  = on_user_intent
        microphone_control.recording     = capture_audio_stream(device_microphone)
        microphone_control.transcription = transcribe(audio_recording)
        microphone_control.preservation  = retain(original_audio)

    vibe:
        microphone_control.color_character = emerald
        microphone_control.tone            = calm
        microphone_control.aesthetic       = "music for idealists"

    conditional:
        microphone_control activates on double_click
        original_audio retained always (unconditional preservation)

    behavior:
        microphone_control transitions from idle to active on activation_intent
        microphone_control transitions from recording to processing on user_stop_signal

    realize:
        target: rust_backend (Rust)
            capabilities: state_machine, event_handling, hardware_io
            preservation_score: 0.9
"""


def _write_file(tmp_path: Path, name: str, content: str) -> Path:
    """Write *content* to *tmp_path / name* and return the Path."""
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# AC-5.1 — Python syntax error
# ---------------------------------------------------------------------------

class TestAC51PythonSyntaxError:
    """A Python file with a deliberate syntax error must FAIL."""

    def test_python_syntax_error_via_check_file(self, tmp_path):
        """check_file must return FAIL for syntactically broken Python."""
        bad_py = _write_file(tmp_path, "bad.py", "def broken(:\n    pass\n")
        result = check_file(bad_py, "python")
        assert result.status == Status.FAIL, (
            f"Expected FAIL for bad Python, got {result.status}: {result.detail}"
        )

    def test_old_conformance_module_also_rejects_bad_python(self, tmp_path):
        """The legacy conformance.check_file must also reject bad Python."""
        from orren_engine.conformance import check_file as old_check_file
        bad_py = _write_file(tmp_path, "bad.py", "def broken(:\n    pass\n")
        status, _detail = old_check_file(bad_py, "python")
        assert status == Status.FAIL


# ---------------------------------------------------------------------------
# AC-5.2 — JavaScript syntax error
# ---------------------------------------------------------------------------

class TestAC52JavaScriptSyntaxError:
    """A JavaScript file with invalid syntax must FAIL."""

    def test_javascript_syntax_error_via_check_file(self, tmp_path):
        """check_file must return FAIL for syntactically broken JavaScript."""
        bad_js = _write_file(tmp_path, "bad.js", "function broken( {\n")
        result = check_file(bad_js, "javascript")
        assert result.status == Status.FAIL, (
            f"Expected FAIL for bad JS, got {result.status}: {result.detail}"
        )

    def test_js_syntax_error_with_node_check(self, tmp_path):
        """If node is available, 'node --check' must reject bad JS."""
        import shutil
        if not shutil.which("node"):
            pytest.skip("node not available in this environment")
        bad_js = _write_file(tmp_path, "bad.js", "var x = ;\n")
        proc = subprocess.run(
            [shutil.which("node"), "--check", str(bad_js)],
            capture_output=True, text=True, timeout=10)
        assert proc.returncode != 0, "node --check should fail on syntax error"


# ---------------------------------------------------------------------------
# AC-5.3 — HTML malformed markup
# ---------------------------------------------------------------------------

class TestAC53HTMLMalformed:
    """Malformed HTML must never be reported as PASS."""

    def test_html_missing_body_structure(self, tmp_path):
        """HTML without html/body structure must not PASS."""
        bad_html = _write_file(tmp_path, "bad.html", "<p>No structure</p>")
        result = check_file(bad_html, "html")
        assert result.status != Status.PASS, (
            f"HTML without structure reported PASS: {result.detail}"
        )

    def test_html_malformed_unclosed_tags(self, tmp_path):
        """HTML with deeply unclosed tags must not PASS."""
        bad_html = _write_file(
            tmp_path, "nested.html",
            "<html><body><div><span><p>unclosed tags everywhere</div></body></html>")
        result = check_file(bad_html, "html")
        assert result.status != Status.PASS, (
            f"Malformed HTML reported PASS: {result.detail}"
        )

    def test_html_no_body_not_pass(self, tmp_path):
        """HTML missing body tag must not PASS."""
        bad_html = _write_file(tmp_path, "nob.html", "<html><head></head></html>")
        result = check_file(bad_html, "html")
        assert result.status != Status.PASS


# ---------------------------------------------------------------------------
# AC-5.4 — CSS empty stylesheet
# ---------------------------------------------------------------------------

class TestAC54CSSEmpty:
    """An empty CSS file must FAIL."""

    def test_empty_css_fails(self, tmp_path):
        """check_file must return FAIL for an empty CSS file."""
        empty_css = _write_file(tmp_path, "empty.css", "")
        result = check_file(empty_css, "css")
        assert result.status == Status.FAIL, (
            f"Expected FAIL for empty CSS, got {result.status}: {result.detail}"
        )

    def test_whitespace_only_css_fails(self, tmp_path):
        """CSS that is only whitespace must also FAIL."""
        ws_css = _write_file(tmp_path, "ws.css", "   \n\n  \t\n")
        result = check_file(ws_css, "css")
        assert result.status == Status.FAIL

    def test_nonempty_css_is_degraded_not_pass(self, tmp_path):
        """Non-empty CSS without a real compiler must be DEGRADED, not PASS."""
        css = _write_file(tmp_path, "style.css", "body { color: red; }")
        result = check_file(css, "css")
        assert result.status != Status.PASS, (
            f"CSS with no compiler should not PASS: {result.detail}"
        )


# ---------------------------------------------------------------------------
# AC-5.5 — Proxy degradation fail-closed
# ---------------------------------------------------------------------------

class TestAC55ProxyDegradation:
    """A backend that emits only a PROXY/DEGRADED comment must never PASS."""

    def test_detect_proxy_returns_true_for_proxy_comment(self):
        """_detect_proxy must flag a PROXY-only file."""
        proxy_text = "// PROXY: microphone capture requires native bridge"
        assert _detect_proxy(proxy_text) is True

    def test_detect_proxy_returns_true_for_degraded_comment(self):
        """_detect_proxy must flag a DEGRADED-only file."""
        proxy_text = "// DEGRADED: no runtime available; stub only"
        assert _detect_proxy(proxy_text) is True

    def test_detect_proxy_returns_false_for_real_code(self):
        """_detect_proxy must NOT flag a file with a real entry point."""
        real_rust = "fn main() {\n    println!(\"hello\");\n}\n"
        assert _detect_proxy(real_rust) is False

    def test_detect_proxy_returns_false_for_real_python(self):
        """_detect_proxy must NOT flag real Python code."""
        real_py = "def process(self):\n    return {'status': 'ok'}\n"
        assert _detect_proxy(real_py) is False

    def test_has_executable_realisation_detects_rust_main(self):
        """A Rust file with fn main is not proxy-only."""
        assert _has_executable_realisation("fn main() {}\n") is True

    def test_has_executable_realisation_detects_python_def(self):
        """A Python file with def is not proxy-only."""
        assert _has_executable_realisation("def process(): pass\n") is True

    def test_has_executable_realisation_rejects_proxy_only(self):
        """A proxy-only comment file has no executable realisation."""
        assert _has_executable_realisation("// PROXY: stub\n") is False

    def test_proxy_rust_file_does_not_pass(self, tmp_path):
        """check_file on a proxy-only Rust file must not return PASS."""
        proxy_rs = _write_file(
            tmp_path, "stub.rs",
            "// PROXY: microphone capture requires native bridge\n")
        result = check_file(proxy_rs, "rust")
        assert result.status != Status.PASS, (
            f"Proxy-only Rust reported PASS: {result.detail}"
        )

    def test_proxy_only_target_never_passes(self, tmp_path):
        """Full preservation-proof flow: a proxied target must not be PASS.

        This simulates a backend that emits only a PROXY comment for a
        microphone-capture capability it cannot express, then verifies that
        the fail-closed logic in _emit_preservation_proof downgrades it.
        """
        from orren_engine.cli import _emit_preservation_proof
        from unittest.mock import MagicMock, Mock

        # Build a minimal fake result graph with a single Rust target.
        fake_target = Mock()
        fake_target.name = "microphone_backend"
        fake_target.language = "Rust"

        fake_graph = Mock()
        fake_graph.realization_targets = [fake_target]
        fake_graph.nodes = []
        fake_graph.equilibrium_rules = []
        fake_graph.signature = Mock(return_value="fake-signature-for-test")

        fake_result = Mock()
        fake_result.graph = fake_graph
        fake_result.expressions_count = 1
        fake_result.sir_node_count = 1
        fake_result.equilibrium_outcomes = 0
        fake_result.unresolved_conflicts = 0
        fake_result.artifacts = []

        fake_ir = Mock()
        fake_ir.content_hash.return_value = "abc123"

        # Write a proxy-only artifact to the output dir.
        out_dir = tmp_path / "realization"
        out_dir.mkdir()
        proxy_file = out_dir / "microphone_backend" / "main.rs"
        proxy_file.parent.mkdir(parents=True, exist_ok=True)
        proxy_file.write_text(
            "// PROXY: full microphone capture requires native bridge; "
            "no Rust implementation emitted\n", encoding="utf-8")

        written_artifacts = [("microphone_backend", "main.rs", str(proxy_file))]

        _emit_preservation_proof(
            str(out_dir), "deadbeef", fake_result, fake_ir, written_artifacts)

        proof_path = out_dir / "preservation_proof.json"
        assert proof_path.exists(), "preservation_proof.json must be written"
        proof = json.loads(proof_path.read_text(encoding="utf-8"))

        assert proof["fail_closed"] is True
        target_report = proof["targets"][0]
        assert target_report["status"] != "PASS", (
            f"Proxy target reported PASS — FAIL CLOSED VIOLATION. "
            f"Status: {target_report['status']}"
        )
        assert target_report["proxy_only"] is True, "Proxy should be detected"

    def test_sovereign_conformance_with_bad_artifacts_fails_closed(self, tmp_path):
        """Run the full sovereign conformance harness against a dir with
        deliberately broken artifacts and assert no false PASS."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()

        # Bad Python
        py_dir = out_dir / "bad_python"
        py_dir.mkdir()
        (py_dir / "service.py").write_text("def broken(:\n    pass\n", encoding="utf-8")

        # Bad JS
        js_dir = out_dir / "bad_js"
        js_dir.mkdir()
        (js_dir / "app.js").write_text("function broken( {\n", encoding="utf-8")

        manifest = {
            "artifacts": [
                {"target_name": "bad_python",
                 "output_files": [{"path": "service.py", "language": "python"}]},
                {"target_name": "bad_js",
                 "output_files": [{"path": "app.js", "language": "javascript"}]},
            ]
        }
        (out_dir / "manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8")

        report = run_conformance(out_dir, run_adversarial=False)
        assert report["failed"] > 0, (
            f"Expected failed > 0 for adversarial bad artifacts, "
            f"got failed={report['failed']}"
        )


# ---------------------------------------------------------------------------
# Language-for-file mapping (used by preservation proof)
# ---------------------------------------------------------------------------

class TestLanguageForFile:
    """Verify the file-extension → language mapping is correct."""

    @pytest.mark.parametrize("ext,expected", [
        ("foo.py", "python"),
        ("foo.rs", "rust"),
        ("foo.go", "go"),
        ("foo.c", "c"),
        ("foo.h", "c"),
        ("foo.cpp", "cpp"),
        ("foo.ts", "typescript"),
        ("foo.js", "javascript"),
        ("foo.html", "html"),
        ("foo.css", "css"),
        ("foo.swift", "swift"),
        ("foo.kt", "kotlin"),
        ("foo.tex", "latex"),
        ("foo.txt", "text"),
        ("foo.unknown", "text"),
    ])
    def test_extension_mapping(self, ext, expected):
        assert _language_for_file(ext) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
