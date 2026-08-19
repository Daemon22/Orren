from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from orren_engine.backends import BACKENDS, backend_for_language, backend_for_target
from orren_engine.parser import CoParser
from orren_engine.realization_ir import IR_VERSION, lower_graph
from orren_engine.sir_builder import SIRBuilder


REPO = Path(__file__).parents[1]
EXAMPLE = REPO / "examples" / "08_rust_processor.orn"


def _graph():
    return SIRBuilder().build(CoParser().parse(EXAMPLE.read_text(encoding="utf-8")))


def test_realization_ir_is_deterministic_and_valid():
    source = EXAMPLE.read_text(encoding="utf-8")
    first = lower_graph(_graph(), source)
    second = lower_graph(_graph(), source)
    assert first.version == IR_VERSION
    assert first.canonical_json() == second.canonical_json()
    assert first.content_hash() == second.content_hash()
    assert first.source_hash == hashlib.sha256(source.encode()).hexdigest()
    first.validate()


def test_realization_ir_preserves_all_dimensions_per_node():
    ir = lower_graph(_graph(), EXAMPLE.read_text(encoding="utf-8"))
    expected = {"expression", "cognitive", "vibe", "spatial", "temporal", "relational", "conditional", "behavioral", "equilibrium"}
    assert ir.nodes
    assert all(set(node.dimensions) == expected for node in ir.nodes)


def test_backend_registry_matches_native_contracts():
    assert backend_for_language("Rust").key == "rust"
    assert backend_for_language("WebAudio API").key == "webaudio"
    assert backend_for_language("TypeScript").key == "typescript"
    assert backend_for_target("rust", {"memory_safety"}).key == "rust"
    assert BACKENDS["rust"].native_files == (("main.rs", "rust"),)
    assert BACKENDS["kotlin"].platforms == ("linux", "windows", "android")


def test_realize_manifest_contains_ir_and_matching_hash(tmp_path):
    out = tmp_path / "out"
    subprocess.run(["python3", "-m", "orren_engine.cli", "realize", str(EXAMPLE), "--out", str(out)], cwd=REPO, check=True, capture_output=True, text=True)
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    ir = manifest["realization_ir"]
    canonical = json.dumps(ir, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    assert manifest["realization_ir_sha256"] == hashlib.sha256(canonical.encode()).hexdigest()
    assert manifest["provenance"]["realization_ir_sha256"] == manifest["realization_ir_sha256"]
    assert {item["target_language"] for item in manifest["artifacts"]} >= {"Rust", "Go", "C", "Python"}
