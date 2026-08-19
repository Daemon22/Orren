"""Phase 2 expansion tests (Movement A): honest gates + FastAPI service.

Covers:
    - seven-gate matrix honesty (no unevidenced PASS; tool-missing SKIPs)
    - manifest preservation fields on artifacts
    - FastAPI HTTP service generation gated on ``http_service`` capability,
      with REAL endpoint behavior via the ASGI transport (httpx).
"""

from __future__ import annotations

import os
import tempfile

import pytest

from orren_engine import CoParser, SIRBuilder, generate_code
from orren_engine.backends.manifest import manifest_for_language
from orren_engine.gate_matrix import GATES, gate_matrix, render_gate_matrix

EXAMPLE_DIR = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "..", "examples"
)


# ---------------------------------------------------------------------------
# Gate matrix honesty
# ---------------------------------------------------------------------------


def test_matrix_covers_all_registered_backends():
    from orren_engine.backends.manifest import ALL_MANIFESTS

    matrix = gate_matrix()
    for m in ALL_MANIFESTS:
        assert m.backend_id in matrix


def test_matrix_has_all_seven_gates():
    for row in gate_matrix().values():
        assert set(row) == set(GATES)


def test_no_unevidenced_pass_for_missing_tools():
    # tsc/swiftc/kotlinc/pdflatex are known-absent in this environment;
    # their syntactic gate must be an explicit tool-missing SKIP.
    matrix = gate_matrix()
    for backend, tool in (
        ("typescript", "tsc"),
        ("swift", "swiftc"),
        ("kotlin", "kotlinc"),
        ("latex", "pdflatex"),
    ):
        import shutil

        if shutil.which(tool) is None:
            status = matrix[backend]["syntactic"]
            assert status == f"SKIP:tool_missing:{tool}", status


def test_render_is_aligned_text():
    text = render_gate_matrix()
    assert "backend" in text
    assert "PASS" in text or "SKIP" in text


# ---------------------------------------------------------------------------
# Manifest preservation honesty fields
# ---------------------------------------------------------------------------


def test_python_manifest_declares_operations_and_limits():
    m = manifest_for_language("python")
    assert m.supported_operations, "must list what it CAN do"
    assert m.unsupported_cases, "must declare what it CANNOT do"
    assert 0.0 <= m.preservation_score <= 1.0


def test_web_manifest_honest_about_static_layers():
    html = manifest_for_language("html")
    assert "behavioral_execution" in html.unsupported_cases
    css = manifest_for_language("css")
    assert "animation_logic" in css.unsupported_cases


# ---------------------------------------------------------------------------
# FastAPI HTTP service (real behavioral verification over ASGI)
# ---------------------------------------------------------------------------


HTTP_ORN = """
create http_probe_app : Application

    context:
        purpose: verify that cognitive predicates surface as HTTP state

    structure:
        core
            sensor

    cognitive:
        sensor.reading = sample_temperature(core_probe)

    realize:
        target: probe_api (Python)
            capabilities: http_service, data_persistence
            can_express: cognitive.reading
            preservation_score: 0.95
"""


@pytest.fixture(scope="module")
def http_service_code():
    source = HTTP_ORN.strip()
    graph = SIRBuilder().build(CoParser().parse(source))
    target = next(t for t in graph.realization_targets if t.name == "probe_api")
    return graph, target, generate_code(graph, target)


def test_http_service_generated_only_with_capability(http_service_code):
    _, _, files = http_service_code
    assert "probe_api/service.py" in files
    assert "from fastapi import FastAPI" in files["probe_api/service.py"]


def test_http_service_endpoints_behave_over_asgi(http_service_code):
    pytest.importorskip("httpx")
    fastapi = pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    _, _, files = http_service_code
    code = files["probe_api/service.py"]

    namespace: dict = {}
    exec(compile(code, "service.py", "exec"), namespace)  # noqa: S102
    app = namespace["app"]
    client = TestClient(app)

    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["predicates"] >= 1

    key_subject, key_pred = "sensor", "reading"
    r = client.get(f"/state/{key_subject}/{key_pred}")
    assert r.status_code == 200
    body = r.json()
    assert body["records"][0]["value"] == "sample_temperature(core_probe)"

    r = client.post(
        f"/state/{key_subject}/{key_pred}", json={"value": "42.5"}
    )
    assert r.status_code == 200
    assert r.json()["recorded"] == "42.5"

    r = client.get(f"/state/{key_subject}/{key_pred}")
    values = [rec["value"] for rec in r.json()["records"]]
    assert values[-1] == "42.5"

    r = client.get("/state/nowhere/nothing")
    assert r.status_code == 200
    assert r.json()["error"] == "unknown predicate"
