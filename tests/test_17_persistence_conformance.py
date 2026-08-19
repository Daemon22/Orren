from __future__ import annotations

import json
from pathlib import Path

from orren_engine.conformance import run_conformance
from orren_engine.database import ProjectDatabase
from orren_engine.engine import Engine
from orren_engine.parser import CoParser
from orren_engine.sir_builder import SIRBuilder
from orren_engine.realization_coordinator import RealizationCoordinator
from orren_engine.codegen import generate


EXAMPLE = Path(__file__).parents[1] / "examples" / "02_news_researcher.orn"


def test_engine_persists_materialized_revision(tmp_path):
    db_path = tmp_path / "project.sqlite"
    source = EXAMPLE.read_text(encoding="utf-8")
    result = Engine(db_path=str(db_path), project_name="conformance").run(source)
    assert result.revision_id == 1
    db = ProjectDatabase(db_path, "conformance")
    assert db.latest_revision()["sir_hash"]
    counts = db.counts()
    assert counts["nodes"] == result.sir_node_count
    assert counts["targets"] == len(result.artifacts)
    assert counts["payloads"] > 0
    assert counts["events"] == 1
    db.close()


def test_coordinator_paths_match_generated_files():
    source = EXAMPLE.read_text(encoding="utf-8")
    graph = SIRBuilder().build(CoParser().parse(source))
    artifacts = RealizationCoordinator().coordinate(graph)
    for artifact in artifacts:
        generated = generate(graph, next(t for t in graph.realization_targets if t.name == artifact.target_name))
        assert {item.path for item in artifact.output_files} == set(generated)


def test_conformance_executes_generated_python_and_resolves_web_assets(tmp_path):
    source = EXAMPLE.read_text(encoding="utf-8")
    graph = SIRBuilder().build(CoParser().parse(source))
    artifacts = RealizationCoordinator().coordinate(graph)
    out = tmp_path / "out"
    out.mkdir()
    manifest = {"artifacts": [a.to_dict() for a in artifacts]}
    for artifact in artifacts:
        target = next(t for t in graph.realization_targets if t.name == artifact.target_name)
        for name, code in generate(graph, target).items():
            path = out / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(code, encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    report = run_conformance(out)
    assert report["failed"] == 0
    assert report["passed"] >= 1


SOVEREIGN_EXAMPLES = [
    "08_rust_processor.orn",
    "09_go_microservices.orn",
    "10_embedded_controller.orn",
    "11_typescript_collab.orn",
    "12_kotlin_mobile.orn",
    "13_latex_specification.orn",
    "14_webaudio_soundscape.orn",
    "15_sovereign_core.orn",
]


def test_sovereign_manifest_paths_match_native_codegen():
    for filename in SOVEREIGN_EXAMPLES:
        source = (EXAMPLE.parents[0] / filename).read_text(encoding="utf-8")
        graph = SIRBuilder().build(CoParser().parse(source))
        targets = {target.name: target for target in graph.realization_targets}
        for artifact in RealizationCoordinator().coordinate(graph):
            generated = generate(graph, targets[artifact.target_name])
            assert {item.path for item in artifact.output_files} == set(generated), (
                f"{filename}:{artifact.target_name} manifest paths do not match codegen"
            )
            assert {item.language for item in artifact.output_files} == {
                _language_for_generated_name(name) for name in generated
            }


def _language_for_generated_name(name: str) -> str:
    suffix = Path(name).suffix.lower()
    return {
        ".rs": "rust",
        ".go": "go",
        ".c": "c",
        ".ts": "typescript",
        ".swift": "swift",
        ".kt": "kotlin",
        ".tex": "latex",
        ".js": "javascript" if name.endswith("app.js") else "webaudio",
        ".py": "python",
        ".txt": "text",
    }.get(suffix, suffix.lstrip("."))
