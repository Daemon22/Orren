"""CLI + reproducible build tests.

Validates:
  - CLI commands work end-to-end against a sample .orn file.
  - `orren hash` produces the same hash for the same input every run.
  - `orren realize` produces byte-identical artifacts across runs.
  - `orren --version` prints the version.
  - The packaged module imports cleanly.
  - pyproject.toml is well-formed and declares the orren entry point.

Run: pytest tests/test_08_cli.py -v
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest


SAMPLE_SOURCE = """create mic_app : Application

    context:
        purpose: a microphone control

    structure:
        home
            microphone_control

    cognitive:
        microphone_control.activation = on_user_intent
        microphone_control.recording = capture_audio
        microphone_control.preservation = retain_original

    vibe:
        microphone_control.color_character = emerald
        microphone_control.tone = calm
        microphone_control.aesthetic = "music for idealists"

    conditional:
        microphone_control activates on double_click
        original_audio retained always (unconditional preservation)

    behavior:
        microphone_control lifecycle: idle -> active -> recording -> processing -> idle

    degrade:
        require full for cognitive on activation_logic
        tolerate proxy for vibe on aesthetic

    realize:
        target: web_interface (HTML/CSS/JS)
            capabilities: layout, color, event_handling
            preservation_score: 0.83
"""


@pytest.fixture
def sample_file(tmp_path):
    p = tmp_path / "sample.orn"
    p.write_text(SAMPLE_SOURCE, encoding="utf-8")
    return str(p)


def _run_cli(*args):
    """Run the orren CLI as a subprocess; return (returncode, stdout, stderr)."""
    cmd = [sys.executable, "-m", "orren_engine.cli", *args]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=30)
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------


class TestVersion:
    def test_version_flag(self):
        rc, out, _ = _run_cli("--version")
        assert rc == 0
        assert "orren" in out
        # Should match the package version.
        from orren_engine import __version__
        assert __version__ in out

    def test_no_command_prints_help(self):
        rc, out, _ = _run_cli()
        # No command → help is printed, rc=1.
        assert rc == 1
        assert "usage:" in out.lower() or "command" in out.lower()


# ---------------------------------------------------------------------------
# parse
# ---------------------------------------------------------------------------


class TestParseCommand:
    def test_parse_exits_zero(self, sample_file):
        rc, out, _ = _run_cli("parse", sample_file)
        assert rc == 0
        assert "mic_app" in out

    def test_parse_shows_context(self, sample_file):
        rc, out, _ = _run_cli("parse", sample_file)
        assert "purpose" in out

    def test_parse_shows_section_counts(self, sample_file):
        rc, out, _ = _run_cli("parse", sample_file)
        # Sections like cognitive, vibe should appear.
        assert "cognitive" in out
        assert "vibe" in out


# ---------------------------------------------------------------------------
# sir
# ---------------------------------------------------------------------------


class TestSirCommand:
    def test_sir_shows_node_count(self, sample_file):
        rc, out, _ = _run_cli("sir", sample_file)
        assert rc == 0
        assert "SIR graph:" in out
        assert "3 nodes" in out

    def test_sir_shows_node_paths(self, sample_file):
        rc, out, _ = _run_cli("sir", sample_file)
        assert "mic_app.home.microphone_control" in out


# ---------------------------------------------------------------------------
# resolve
# ---------------------------------------------------------------------------


class TestResolveCommand:
    def test_resolve_shows_outcomes(self, sample_file):
        rc, out, _ = _run_cli("resolve", sample_file)
        assert rc == 0
        assert "Outcomes:" in out
        assert "Unresolved conflicts:" in out


# ---------------------------------------------------------------------------
# realize
# ---------------------------------------------------------------------------


class TestRealizeCommand:
    def test_realize_writes_files(self, sample_file, tmp_path):
        out_dir = tmp_path / "out"
        rc, _, _ = _run_cli("realize", sample_file, "--out", str(out_dir))
        assert rc == 0
        # Should have created web_interface/ with index.html, styles.css, app.js.
        web_dir = out_dir / "web_interface"
        assert web_dir.exists()
        assert (web_dir / "index.html").exists()
        assert (web_dir / "styles.css").exists()
        assert (web_dir / "app.js").exists()
        # And a manifest.json.
        assert (out_dir / "manifest.json").exists()

    def test_realize_manifest_is_valid_json(self, sample_file, tmp_path):
        out_dir = tmp_path / "out"
        _run_cli("realize", sample_file, "--out", str(out_dir))
        manifest_path = out_dir / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)
        assert manifest["version"] == "0.3.3"
        assert manifest["expressions"] >= 1
        assert manifest["sir_nodes"] >= 1
        assert len(manifest["artifacts"]) >= 1

    def test_realize_files_contain_code(self, sample_file, tmp_path):
        out_dir = tmp_path / "out"
        _run_cli("realize", sample_file, "--out", str(out_dir))
        html = (out_dir / "web_interface" / "index.html").read_text()
        assert "<!DOCTYPE html>" in html
        css = (out_dir / "web_interface" / "styles.css").read_text()
        assert "background-color" in css


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


class TestValidateCommand:
    def test_validate_passes_on_valid_source(self, sample_file):
        rc, out, _ = _run_cli("validate", sample_file)
        assert rc == 0
        assert "PASS" in out

    def test_validate_reports_checks(self, sample_file):
        rc, out, _ = _run_cli("validate", sample_file)
        assert "all_nodes_have_9_dimensions" in out
        assert "realization_artifacts_present" in out


# ---------------------------------------------------------------------------
# hash — reproducibility
# ---------------------------------------------------------------------------


class TestHashReproducibility:
    def test_same_input_same_hash(self, sample_file):
        rc1, out1, _ = _run_cli("hash", sample_file)
        rc2, out2, _ = _run_cli("hash", sample_file)
        assert rc1 == 0 and rc2 == 0
        # Both runs should produce the same hash.
        assert out1.strip() == out2.strip()
        # The hash is a 64-char hex string.
        assert len(out1.strip()) == 64

    def test_different_input_different_hash(self, sample_file, tmp_path):
        # Modify the source slightly.
        modified = SAMPLE_SOURCE.replace("emerald", "sapphire")
        p = tmp_path / "modified.orn"
        p.write_text(modified, encoding="utf-8")
        rc1, out1, _ = _run_cli("hash", sample_file)
        rc2, out2, _ = _run_cli("hash", str(p))
        assert out1.strip() != out2.strip()


# ---------------------------------------------------------------------------
# Byte-for-byte artifact reproducibility
# ---------------------------------------------------------------------------


class TestArtifactReproducibility:
    def test_realize_output_byte_identical_across_runs(self, sample_file, tmp_path):
        out1 = tmp_path / "out1"
        out2 = tmp_path / "out2"
        _run_cli("realize", sample_file, "--out", str(out1))
        _run_cli("realize", sample_file, "--out", str(out2))
        # Walk every file in out1 and compare with out2.
        for root, _, files in os.walk(out1):
            for fname in files:
                p1 = os.path.join(root, fname)
                rel = os.path.relpath(p1, out1)
                p2 = os.path.join(out2, rel)
                assert os.path.exists(p2), f"missing in run 2: {rel}"
                with open(p1, "rb") as f1, open(p2, "rb") as f2:
                    assert f1.read() == f2.read(), f"bytes differ: {rel}"

    def test_manifest_byte_identical_across_runs(self, sample_file, tmp_path):
        out1 = tmp_path / "out1"
        out2 = tmp_path / "out2"
        _run_cli("realize", sample_file, "--out", str(out1))
        _run_cli("realize", sample_file, "--out", str(out2))
        m1 = (out1 / "manifest.json").read_text()
        m2 = (out2 / "manifest.json").read_text()
        # The source_file path differs because tmp_path differs, so we
        # compare everything except that field.
        j1 = json.loads(m1)
        j2 = json.loads(m2)
        j1.pop("source_file", None)
        j2.pop("source_file", None)
        assert j1 == j2


# ---------------------------------------------------------------------------
# Package metadata
# ---------------------------------------------------------------------------


class TestPackageMetadata:
    def test_pyproject_exists(self):
        p = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
        )
        assert os.path.exists(p)

    def test_pyproject_declares_entry_point(self):
        p = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
        )
        with open(p) as f:
            content = f.read()
        assert "[project.scripts]" in content
        assert 'orren = "orren_engine.cli:main"' in content

    def test_pyproject_declares_version(self):
        p = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
        )
        with open(p) as f:
            content = f.read()
        assert 'version = "0.3.3"' in content

    def test_package_imports_cleanly(self):
        import orren_engine
        assert orren_engine.__version__ == "0.3.3"
        # All public API names should be importable.
        for name in ("CoParser", "SIRBuilder", "EquilibriumResolver",
                     "RealizationCoordinator", "SemanticEditor", "Engine"):
            assert hasattr(orren_engine, name)
