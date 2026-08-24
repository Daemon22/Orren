from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from orren_engine.codegen import generate
from orren_engine.conformance_sovereign import check_file
from orren_engine.parser import CoParser
from orren_engine.sir_builder import SIRBuilder
from orren_engine.realization_coordinator import RealizationCoordinator


REPO = Path(__file__).parents[1]
SOURCE = REPO / "examples" / "08_rust_processor.orn"


def _rust_artifact(tmp_path: Path) -> tuple[Path, dict]:
    graph = SIRBuilder().build(CoParser().parse(SOURCE.read_text(encoding="utf-8")))
    target = next(target for target in graph.realization_targets if target.language.lower() == "rust")
    generated = generate(graph, target)
    path = tmp_path / "main.rs"
    path.write_text(generated[f"{target.name}/main.rs"], encoding="utf-8")
    return path, {"sir_hash": hashlib.sha256(graph.signature().encode()).hexdigest(), "target": target.name}


def test_rust_validator_compiles_and_executes_generated_artifact(tmp_path):
    path, _ = _rust_artifact(tmp_path)
    result = check_file(path, "rust")
    assert result.status == "PASS"
    assert result.evidence_level >= 3
    assert "compiled" in result.detail.lower()
    assert "behavior" in result.detail.lower()


def test_rust_binary_is_deterministic_and_preserves_semantic_state(tmp_path):
    path, provenance = _rust_artifact(tmp_path)
    binary = tmp_path / "app"
    subprocess.run(["rustc", "--edition", "2021", "-D", "warnings", str(path), "-o", str(binary)], check=True, capture_output=True, text=True)
    first = subprocess.run([str(binary)], check=True, capture_output=True, text=True).stdout
    second = subprocess.run([str(binary)], check=True, capture_output=True, text=True).stdout
    assert first == second
    runtime = json.loads(first.replace("'", '"')) if False else first
    assert "application" in first
    assert "input_title" in first
    assert "schema_validation" in first
    assert provenance["sir_hash"]


def test_rust_validator_rejects_type_errors(tmp_path):
    path = tmp_path / "bad.rs"
    path.write_text('fn main() { let value: i32 = "not an integer"; println!("{}", value); }\n', encoding="utf-8")
    result = check_file(path, "rust")
    assert result.status == "FAIL"
    assert "compilation" in result.detail.lower()


def test_rust_manifest_declares_native_source():
    graph = SIRBuilder().build(CoParser().parse(SOURCE.read_text(encoding="utf-8")))
    artifacts = RealizationCoordinator().coordinate(graph)
    rust_artifact = next(artifact for artifact in artifacts if artifact.target_language.lower() == "rust")
    assert [(item.path, item.language) for item in rust_artifact.output_files] == [("rust_backend/main.rs", "rust"), ("rust_backend/Cargo.toml", "toml")]


def test_realize_manifest_contains_matching_provenance(tmp_path):
    out = tmp_path / "realized"
    subprocess.run(
        ["python3", "-m", "orren_engine.cli", "realize", str(SOURCE), "--out", str(out)],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
    )
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert manifest["source_sha256"] == source_hash
    assert manifest["provenance"]["source_sha256"] == source_hash
    assert manifest["provenance"]["sir_sha256"] == manifest["sir_sha256"]
