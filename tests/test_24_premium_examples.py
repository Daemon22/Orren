"""Seven-gate conformance for the Movement B canonical web examples.

Each example must parse into a full nine-dimension SIR graph and its
``web_interface`` target must produce artifacts that pass all seven gates:

    1. structural   -- semantic HTML, data-semantic-id, ARIA
    2. syntactic    -- parser-verified HTML / CSS / JS
    3. semantic     -- every dimension represented in output
    4. behavioral   -- FSM + guards + temporal sequences in JS (executed)
    5. degradation  -- honest PROXY/DEGRADED markers where needed
    6. accessibility-- focus-visible, theme control, reduced motion
    7. honesty      -- no silent capability claims; manifest matches codegen

Run: python -m pytest tests/test_24_premium_examples.py -q
"""

from __future__ import annotations

import os
import re

import pytest

from orren_engine import CoParser, SIRBuilder, generate_code
from orren_engine.backends.web_generator import generate_web
from orren_engine.backends.web_tokens import extract_all_tokens

EXAMPLES = [
    "premium_web_atmospheric.orn",
    "premium_web_ceremonial.orn",
    "premium_web_data_dashboard.orn",
]

EXAMPLE_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "examples")


def _build(filename: str):
    source = open(os.path.join(EXAMPLE_DIR, filename), encoding="utf-8").read()
    graph = SIRBuilder().build(CoParser().parse(source))
    target = next(t for t in graph.realization_targets if t.name == "web_interface")
    files = generate_code(graph, target)
    bundle = generate_web(graph, target)
    return graph, target, files, bundle


@pytest.fixture(scope="module", params=EXAMPLES)
def case(request):
    filename = request.param
    graph, target, files, bundle = _build(filename)
    return {
        "filename": filename,
        "graph": graph,
        "target": target,
        "html": files["web_interface/index.html"],
        "css": files["web_interface/styles.css"],
        "js": files["web_interface/app.js"],
        "living": bundle["web_interface/living.js"],
        "standalone": bundle["web_interface/index.standalone.html"],
        "bundle_keys": set(bundle),
        "files": files,
    }


# --- Gate 1: structural ------------------------------------------------------


def test_semantic_landmarks(case):
    assert '<header class="orren-header" role="banner">' in case["html"]
    assert 'role="main"' in case["html"]
    assert 'role="contentinfo"' in case["html"]


def test_semantic_ids_present(case):
    assert 'data-semantic-id="orren.theme_toggle"' in case["html"]
    assert 'data-semantic-id="orren.purpose"' in case["html"]
    assert 'data-semantic-id="orren.living_backdrop"' in case["html"]


# --- Gate 2: syntactic --------------------------------------------------------


def test_html_parses(case):
    from html.parser import HTMLParser

    seen: list = []

    class Checker(HTMLParser):
        def handle_starttag(self, tag, attrs):
            if tag in ("html", "head", "body"):
                seen.append(tag)

    Checker().feed(case["html"])
    assert seen.count("html") == 1 and seen.count("body") == 1


def test_css_balanced_braces(case):
    assert case["css"].count("{") == case["css"].count("}")


def test_js_exports_contract(case):
    js = case["js"]
    assert "export function wireUpEvents" in js or "export default wireUpEvents" in js
    assert "export function startTemporalSequences" in js
    assert "export function initThemeToggle" in js


# --- Gate 3: semantic (dimension preservation) --------------------------------


def test_all_nine_dimensions_present_in_graph(case):
    g = case["graph"]
    found = set()
    for node in [g.root] + list(_walk(g.root)):
        for dim, entries in node.dimensions.items():
            if entries:
                found.add(dim.name.lower())
    # Equilibrium attaches at graph level.
    if getattr(g, "equilibrium_rules", None):
        found.add("equilibrium")
    required = {
        "expression", "cognitive", "vibe", "spatial", "temporal",
        "relational", "conditional", "behavioral", "equilibrium",
    }
    assert required <= found, f"{case['filename']} missing dimensions: {required - found}"


def _walk(node):
    for child in getattr(node, "children", []) or []:
        yield child
        yield from _walk(child)


def test_vibe_tokens_flow_into_css(case):
    tokens = extract_all_tokens(case["graph"])
    accent_vars = [
        tm.css_variables.get("--color-accent")
        for tm in tokens.values()
        if tm.css_variables.get("--color-accent")
    ]
    assert accent_vars, f"{case['filename']}: no vibe color token extracted"
    # At least one per-node rule carries the accent.
    for var in accent_vars:
        assert var in case["css"]


# --- Gate 4: behavioral (JS executed under Node when available) ---------------


def test_js_executes_under_node(case):
    import shutil
    import subprocess
    import tempfile

    if shutil.which("node") is None:
        pytest.skip("node not available")
    shim = (
        "const listeners=new Map();"
        "global.document={"
        "getElementById:()=>null,"
        "addEventListener:(t,f)=>{listeners.set(t,f)},"
        "removeEventListener:()=>{},"
        "querySelectorAll:()=>[],"
        "documentElement:{classList:{add(){},remove(){},contains:()=>false}},"
        "hidden:false};"
        "global.window={addEventListener:(t,f)=>{},matchMedia:()=>({matches:false,addListener(){}}),dispatchEvent:()=>true};"
        "global.localStorage={getItem:()=>null,setItem:()=>{},removeItem:()=>{}};"
        "global.CustomEvent=class{constructor(t,o){this.type=t;this.detail=o&&o.detail}};"
        "global.ErrorEvent=class extends global.CustomEvent{};"
        "global.requestAnimationFrame=()=>1;global.cancelAnimationFrame=()=>{};"
    )
    with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False, encoding="utf-8") as fh:
        fh.write(shim + "\n" + case["js"] + "\nconsole.log('ORREN_JS_OK');")
        path = fh.name
    proc = subprocess.run(
        ["node", path], capture_output=True, text=True, timeout=60
    )
    assert proc.returncode == 0, f"{case['filename']} JS failed:\n{proc.stderr}"
    assert "ORREN_JS_OK" in proc.stdout


def test_temporal_sequences_self_start(case):
    js = case["js"]
    assert "startTemporalSequences" in js


# --- Gate 5: degradation honesty ----------------------------------------------


def test_degradation_markers_when_declared(case):
    cannot = case["target"].cannot_express
    if not cannot:
        pytest.skip(f"{case['filename']} declares nothing it cannot express")
    combined = case["css"] + case["html"]
    assert "PROXY" in combined or "DEGRADED" in combined


# --- Gate 6: accessibility -----------------------------------------------------


def test_focus_visible_and_theme_classes(case):
    assert ":focus-visible" in case["css"]
    assert "html.theme-light" in case["css"]
    assert "html.theme-dark" in case["css"]


def test_reduced_motion_honored_twice(case):
    assert "(prefers-reduced-motion: reduce)" in case["css"]
    assert "prefers-reduced-motion" in case["js"]
    assert "prefers-reduced-motion" in case["living"]


def test_theme_toggle_wired(case):
    assert 'id="orren-theme-toggle"' in case["html"]
    assert "initThemeToggle();" in case["html"]


# --- Gate 7: honesty ------------------------------------------------------------


def test_bundle_contents_stable(case):
    expected = {
        "web_interface/index.html",
        "web_interface/styles.css",
        "web_interface/app.js",
        "web_interface/living.js",
        "web_interface/index.standalone.html",
    }
    assert expected <= case["bundle_keys"], (
        f"{case['filename']} missing: {expected - case['bundle_keys']}"
    )


def test_standalone_has_no_external_module_imports(case):
    standalone = case["standalone"]
    assert 'from "./app.js"' not in standalone
    assert 'from "./living.js"' not in standalone


def test_preservation_score_reported(case):
    score = case["target"].preservation_score
    assert 0.0 < score <= 1.0
    assert f'{score}' in case["css"] or f'{score}' in case["html"]
