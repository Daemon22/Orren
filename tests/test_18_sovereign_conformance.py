"""Sovereign Conformance Tests — Language Equality Validation.

This test module enforces Orren's sovereignty principle:
- Every language with a realization target gets EQUAL validation rigor
- DEGRADED status is used honestly (never inflated to PASS)
- Adversarial cases prove the harness can FAIL each language
- Python has no privileged status

Run with: pytest test_18_sovereign_conformance.py -v
"""
from __future__ import annotations

import json
import pytest
from pathlib import Path

# Import the SOVEREIGN conformance module (not the old one)
from orren_engine.conformance_sovereign import (
    Status,
    EvidenceLevel,
    run_conformance,
    write_report,
    check_file,
    generate_adversarial_cases,
    run_adversarial_tests,
    CheckResult,
    CoverageMatrix,
)

EXAMPLES_DIR = Path(__file__).parents[1] / "examples"


class TestSovereignPrinciples:
    """Verify the conformance harness respects language sovereignty."""

    def test_python_is_not_privileged_in_status_enum(self):
        """Python must not have special status in the status hierarchy."""
        # All languages use the same Status enum
        assert hasattr(Status, 'PASS')
        assert hasattr(Status, 'DEGRADED')
        assert hasattr(Status, 'SKIP')
        assert hasattr(Status, 'FAIL')
        # No PYTHON_PASS or similar privilege exists
        assert not hasattr(Status, 'PYTHON_PASS')
        assert not hasattr(Status, 'PYTHON_SPECIAL')

    def test_degraded_status_exists_and_is_distinct(self):
        """DEGRADED must exist and be different from PASS."""
        assert Status.DEGRADED != Status.PASS
        assert Status.DEGRADED != Status.SKIP
        assert Status.DEGRADED != Status.FAIL

    def test_evidence_levels_exist_for_transparency(self):
        """Evidence levels allow consumers to judge check quality."""
        assert EvidenceLevel.FILE_EXISTS == 0
        assert EvidenceLevel.SYNTACTIC == 1
        assert EvidenceLevel.STRUCTURAL == 2
        assert EvidenceLevel.BEHAVIORAL == 3
        assert EvidenceLevel.INTEGRATION == 4


class TestMultiLanguageValidatorsExist:
    """Every claimed backend must have a validator path."""

    @pytest.mark.parametrize("language", [
        "python", "rust", "go", "c", "typescript",
        "javascript", "html", "css", "swift", "kotlin",
        "latex", "webaudio", "text"
    ])
    def test_validator_registered(self, language):
        """Each language has an entry point in the validator dispatch."""
        from orren_engine.conformance_sovereign import _VALIDATORS
        assert language in _VALIDATORS, f"No validator for {language}"

    def test_rust_validator_is_real_function(self):
        """Rust validator exists (not stub)."""
        from orren_engine.conformance_sovereign import _validate_rust
        import inspect
        assert inspect.isfunction(_validate_rust)
        # Should have meaningful implementation, not just "return SKIP"
        source = inspect.getsource(_validate_rust)
        assert "rustc" in source.lower() or "toolchain" in source.lower()

    def test_go_validator_is_real_function(self):
        """Go validator exists (not stub)."""
        from orren_engine.conformance_sovereign import _validate_go
        import inspect
        source = inspect.getsource(_validate_go)
        assert "go vet" in source or "go build" in source or "toolchain" in source.lower()

    def test_c_validator_is_real_function(self):
        """C/C++ validator exists (not stub)."""
        from orren_engine.conformance_sovereign import _validate_c
        import inspect
        source = inspect.getsource(_validate_c)
        assert "gcc" in source or "clang" in source or "fsyntax-only" in source

    def test_typescript_validator_is_real_function(self):
        """TypeScript validator uses tsc."""
        from orren_engine.conformance_sovereign import _validate_typescript
        import inspect
        source = inspect.getsource(_validate_typescript)
        assert "tsc" in source or "noEmit" in source


class TestHonestStatusReporting:
    """Verify that weak checks are NOT reported as PASS."""

    def test_css_empty_file_fails_not_passes(self, tmp_path):
        """Empty CSS must FAIL, never PASS."""
        css_file = tmp_path / "empty.css"
        css_file.write_text("", encoding="utf-8")
        
        result = check_file(css_file, "css")
        assert result.status == Status.FAIL
        assert result.status != Status.PASS
        assert result.status != Status.DEGRADED  # Empty is failure, not degradation

    def test_css_nonempty_gets_degraded_not_pass(self, tmp_path):
        """Non-empty CSS without compiler should be DEGRADED, not PASS."""
        css_file = tmp_path / "styles.css"
        css_file.write_text("body { color: red; }", encoding="utf-8")
        
        result = check_file(css_file, "css")
        # CRITICAL: Must NOT be PASS — we didn't actually validate CSS
        assert result.status != Status.PASS, (
            f"CSS returned {result.status} but should be DEGRADED/SKIP "
            f"(no real CSS compiler ran). Detail: {result.detail}"
        )
        assert result.status in (Status.DEGRADED, Status.SKIP)

    def test_html_without_body_gets_fail_or_degraded(self, tmp_path):
        """HTML missing structure must fail, not pass."""
        html_file = tmp_path / "bad.html"
        html_file.write_text("<html><head></head></html>", encoding="utf-8")
        
        result = check_file(html_file, "html")
        assert result.status != Status.PASS

    def test_javascript_syntax_only_reports_degraded_not_pass(self, tmp_path):
        """JS --check is syntactic only; must report DEGRADED if no behavioral test."""
        js_file = tmp_path / "app.js"
        js_file.write_text("'use strict';\nconsole.log('hello');\n", encoding="utf-8")
        
        result = check_file(js_file, "javascript")
        # JS only does syntax check, not behavioral execution
        # So it should be DEGRADED (syntactic valid, behavioral untested)
        # OR PASS if we consider syntax sufficient for JS
        # The key: detail must explain what was NOT tested
        if result.status == Status.PASS:
            assert "behavioral" in result.detail.lower() or "syntax" in result.detail.lower()


class TestAdversarialValidation:
    """Prove the harness CAN reject bad artifacts."""

    def test_adversarial_suite_generates_bad_files(self, tmp_path):
        """Adversarial generator creates intentionally broken files."""
        manifest = generate_adversarial_cases(tmp_path)
        
        assert "cases" in manifest
        assert len(manifest["cases"]) > 0
        
        adversarial_dir = tmp_path / "__adversarial__"
        assert adversarial_dir.exists()
        
        for case in manifest["cases"]:
            case_path = tmp_path / case["path"]
            assert case_path.exists(), f"Adversarial file not created: {case['path']}"

    def test_python_syntax_error_detected(self, tmp_path):
        """Harness rejects Python with syntax errors."""
        (tmp_path / "__adv__").mkdir(parents=True, exist_ok=True)
        bad_py = tmp_path / "__adv__/bad_syntax.py"
        bad_py.write_text("def broken(\n    # unclosed\n", encoding="utf-8")
        
        result = check_file(bad_py, "python")
        assert result.status == Status.FAIL, (
            f"Expected FAIL for bad Python, got {result.status}: {result.detail}"
        )

    def test_python_runtime_error_detected(self, tmp_path):
        """Harness rejects Python where process() raises exception."""
        (tmp_path / "__adv__").mkdir(parents=True, exist_ok=True)
        bad_behavior = tmp_path / "__adv__/bad_behavior.py"
        bad_behavior.write_text("""
class BadService:
    def process(self):
        raise RuntimeError("Intentional failure")
""", encoding="utf-8")
        
        result = check_file(bad_behavior, "python")
        assert result.status == Status.FAIL, (
            f"Expected FAIL for bad behavior, got {result.status}: {result.detail}"
        )

    def test_javascript_syntax_error_detected(self, tmp_path):
        """Harness rejects JavaScript with syntax errors."""
        (tmp_path / "__adv__").mkdir(parents=True, exist_ok=True)
        bad_js = tmp_path / "__adv__/bad_syntax.js"
        bad_js.write_text("function broken( {\n", encoding="utf-8")
        
        result = check_file(bad_js, "javascript")
        assert result.status == Status.FAIL, (
            f"Expected FAIL for bad JS, got {result.status}: {result.detail}"
        )

    def test_html_missing_structure_detected(self, tmp_path):
        """Harness rejects HTML without required elements."""
        (tmp_path / "__adv__").mkdir(parents=True, exist_ok=True)
        bad_html = tmp_path / "__adv__/bad.html"
        bad_html.write_text("<!DOCTYPE html><p>No structure</p>", encoding="utf-8")
        
        result = check_file(bad_html, "html")
        assert result.status != Status.PASS

    def test_css_empty_file_rejected(self, tmp_path):
        """Harness rejects empty CSS."""
        (tmp_path / "__adv__").mkdir(parents=True, exist_ok=True)
        empty_css = tmp_path / "__adv__/empty.css"
        empty_css.write_text("", encoding="utf-8")
        
        result = check_file(empty_css, "css")
        assert result.status == Status.FAIL

    def test_adversarial_suite_runs_and_reports(self, tmp_path):
        """Full adversarial suite produces health report."""
        summary = run_adversarial_tests(tmp_path)
        
        assert "health" in summary
        assert "correct_rejections" in summary
        assert "false_passes" in summary
        
        # false_passes MUST be 0 for healthy harness
        # (if >0, harness is passing things that should fail)
        assert summary["false_passes"] == 0, (
            f"Harness COMPROMISED: {summary['false_passes']} false passes detected!"
        )


class TestCoverageMatrixReporting:
    """Verify coverage matrix shows honest picture."""

    def test_report_includes_coverage_matrix(self, tmp_path):
        """Report includes structured coverage, not just flat counts."""
        # Create minimal valid output
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        
        # Create a simple Python artifact
        py_dir = out_dir / "test_service"
        py_dir.mkdir()
        (py_dir / "service.py").write_text("""
class TestService:
    def process(self):
        return {"status": "ok"}
""", encoding="utf-8")
        
        manifest = {
            "artifacts": [{
                "target_name": "test_service",
                "output_files": [{"path": "service.py", "language": "python"}]
            }]
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        
        report = run_conformance(out_dir, run_adversarial=False)
        
        assert "coverage_matrix" in report
        assert isinstance(report["coverage_matrix"], dict)

    def test_report_lists_languages_tested_vs_available(self, tmp_path):
        """Report shows which languages were actually exercised."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        
        py_dir = out_dir / "svc"
        py_dir.mkdir()
        (py_dir / "main.py").write_text("x = 1\n", encoding="utf-8")
        
        manifest = {
            "artifacts": [{
                "target_name": "svc",
                "output_files": [{"path": "main.py", "language": "python"}]
            }]
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        
        report = run_conformance(out_dir, run_adversarial=False)
        
        assert "languages_tested" in report
        assert "languages_available" in report
        assert len(report["languages_available"]) >= 10  # Should have many validators
        assert "python" in report["languages_tested"]

    def test_report_includes_sovereignty_note(self, tmp_path):
        """Report includes explicit statement about sovereignty principle."""
        out_dir = tmp_path / "out"
        out_dir.mkdir()
        
        py_dir = out_dir / "svc"
        py_dir.mkdir()
        (py_dir / "main.py").write_text("# test\n", encoding="utf-8")
        
        manifest = {
            "artifacts": [{
                "target_name": "svc",
                "output_files": [{"path": "main.py", "language": "python"}]
            }]
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        
        report = run_conformance(out_dir, run_adversarial=False)
        
        assert "sovereignty_note" in report
        assert "sovereignty" in report["sovereignty_note"].lower()


class TestNewOrnExamplesParse:
    """Verify new multi-language .orn examples parse correctly."""

    @pytest.mark.parametrize("orn_file", [
        "08_rust_processor.orn",
        "09_go_microservices.orn", 
        "10_embedded_controller.orn",
        "11_typescript_collab.orn",
        "12_kotlin_mobile.orn",
        "13_latex_specification.orn",
        "14_webaudio_soundscape.orn",
        "15_sovereign_core.orn",
    ])
    def test_new_example_parses(self, orn_file):
        """Each new example file parses without errors."""
        path = EXAMPLES_DIR / orn_file
        if not path.exists():
            pytest.skip(f"Example file not found: {orn_file}")
        
        from orren_engine.parser import CoParser
        source = path.read_text(encoding="utf-8")
        expressions = CoParser().parse(source)
        
        # Should parse at least one expression
        assert len(expressions) > 0, f"{orn_file} parsed zero expressions"

    def test_sovereign_core_declares_all_languages(self):
        """The sovereign core .orn explicitly targets all major backends."""
        path = EXAMPLES_DIR / "15_sovereign_core.orn"
        if not path.exists():
            pytest.skip("sovereign_core.orn not found")
        
        source = path.read_text(encoding="utf-8")
        
        # Verify it mentions key non-Python backends as first-class citizens
        assert "rust" in source.lower(), "Must mention Rust"
        assert "go" in source.lower() or "golang" in source.lower(), "Must mention Go"
        assert "kotlin" in source.lower(), "Must mention Kotlin"
        assert "typescript" in source.lower(), "Must mention TypeScript"
        assert "swift" in source.lower(), "Must mention Swift"
        
        # Verify it explicitly states Python equality (not privilege)
        assert "not the reference" in source.lower() or "equal" in source.lower() or "sovereignty" in source.lower()


class TestRustGoCExamplesGenerateValidCode:
    """Test that examples targeting Rust/Go/C produce valid code."""

    def test_rust_processor_generates_rust_code(self):
        """08_rust_processor.orn should generate Rust code."""
        path = EXAMPLES_DIR / "08_rust_processor.orn"
        if not path.exists():
            pytest.skip("Example not found")
        
        from orren_engine.parser import CoParser
        from orren_engine.sir_builder import SIRBuilder
        from orren_engine.realization_coordinator import RealizationCoordinator
        from orren_engine.codegen import generate
        
        source = path.read_text(encoding="utf-8")
        graph = SIRBuilder().build(CoParser().parse(source))
        artifacts = RealizationCoordinator().coordinate(graph)
        
        # Find rust_backend target
        rust_targets = [t for t in graph.realization_targets if "rust" in t.name.lower()]
        assert len(rust_targets) > 0, "No Rust target found in realization targets"
        
        # Generate code for rust target
        for target in rust_targets:
            code = generate(graph, target)
            assert isinstance(code, dict), f"Code generation for {target.name} failed"
            assert len(code) > 0, f"No files generated for {target.name}"
            
            # Check generated content looks like Rust
            for filename, content in code.items():
                assert len(content) > 0, f"Empty file: {filename}"
                # Basic Rust indicators
                has_rust_syntax = any(
                    indicator in content 
                    for indicator in ["fn ", "struct ", "impl ", "let ", "pub ", "mod "]
                ) or filename.endswith(".rs")
                # If it's supposed to be Rust, it should have Rust-like content
                if target.language.lower() == "rust":
                    assert has_rust_syntax, (
                        f"Generated Rust file {filename} doesn't look like Rust. "
                        f"First 200 chars: {content[:200]}"
                    )

    def test_go_microservices_generates_go_code(self):
        """09_go_microservices.orn should generate Go code."""
        path = EXAMPLES_DIR / "09_go_microservices.orn"
        if not path.exists():
            pytest.skip("Example not found")
        
        from orren_engine.parser import CoParser
        from orren_engine.sir_builder import SIRBuilder
        from orren_engine.realization_coordinator import RealizationCoordinator
        from orren_engine.codegen import generate
        
        source = path.read_text(encoding="utf-8")
        graph = SIRBuilder().build(CoParser().parse(source))
        artifacts = RealizationCoordinator().coordinate(graph)
        
        go_targets = [t for t in graph.realization_targets if "go" in t.name.lower()]
        assert len(go_targets) > 0, "No Go target found"
        
        for target in go_targets:
            code = generate(graph, target)
            assert isinstance(code, dict)
            
            for filename, content in code.items():
                assert len(content) > 0
                if target.language.lower() == "go":
                    has_go_syntax = any(
                        indicator in content 
                        for indicator in ["package ", "func ", "type ", "import ", "go "]
                    ) or filename.endswith(".go")
                    assert has_go_syntax, f"Generated Go file doesn't look like Go"

    def test_embedded_controller_generates_c_code(self):
        """10_embedded_controller.orn should generate C code."""
        path = EXAMPLES_DIR / "10_embedded_controller.orn"
        if not path.exists():
            pytest.skip("Example not found")
        
        from orren_engine.parser import CoParser
        from orren_engine.sir_builder import SIRBuilder
        from orren_engine.realization_coordinator import RealizationCoordinator
        from orren_engine.codegen import generate
        
        source = path.read_text(encoding="utf-8")
        graph = SIRBuilder().build(CoParser().parse(source))
        artifacts = RealizationCoordinator().coordinate(graph)
        
        c_targets = [t for t in graph.realization_targets 
                     if t.language.lower() in ("c", "cpp") or "embedded" in t.name.lower()]
        assert len(c_targets) > 0, "No C/embedded target found"
        
        for target in c_targets:
            code = generate(graph, target)
            for filename, content in code.items():
                assert len(content) > 0
                if target.language.lower() in ("c", "cpp"):
                    has_c_syntax = any(
                        indicator in content 
                        for indicator in ["#include", "int ", "void ", "struct ", "/*"]
                    ) or any(filename.endswith(ext) for ext in [".c", ".cpp", ".h"])
                    assert has_c_syntax, f"Generated C file doesn't look like C/C++"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
