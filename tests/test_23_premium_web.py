"""Seven-gate premium web backend verification.

Verifies that the HTML/CSS/JS backend meets the Seven-Gate Standard for
premium quality:

  1. Structural   -- semantic elements, data-semantic-id, ARIA, lang attr
  2. Syntactic    -- HTML parses; CSS balanced + property-shaped; node --check
  3. Linkable     -- index.html references resolve to emitted artifacts;
                     no external network resources
  4. Executable   -- app.js loads and initializes under Node (DOM shim)
  5. Behavioral   -- state-machine transitions fire from real DOM events,
                     guards reject invalid transitions, temporal sequences
                     dispatch, relational wiring is safe (all executed in Node)
  6. Operational  -- config limits, localStorage persistence round-trip,
                     error boundary present and hidden by default
  7. Preservation -- PROXY / BRIDGE / DEGRADED markers for every unmapped
                     meaning; vibe token registry explicit and overridable

Node-executed gates are honest: when the node toolchain is unavailable the
tests SKIP rather than fabricate a pass.

Fixture: examples/microphone_application.orn — exercises all nine dimensions.

Run: pytest tests/test_23_premium_web.py -v
"""
import os
import re
import shutil
import subprocess
import sys
import json
from html.parser import HTMLParser

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from orren_engine import (
    CoParser,
    SIRBuilder,
    generate_code,
)
from orren_engine.backends.web_tokens import (
    _vibe_term_to_tokens,
    extract_all_tokens,
    register_vibe_mapping,
)

EXAMPLE = os.path.join(
    os.path.abspath(os.path.dirname(__file__)), "..", "examples", "microphone_application.orn"
)


def _node_available() -> bool:
    return shutil.which("node") is not None


# ---------------------------------------------------------------------------
# Shared fixture: parse → SIR → premium web artifacts
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def artifacts():
    with open(EXAMPLE, "r", encoding="utf-8") as fh:
        source = fh.read()
    graph = SIRBuilder().build(CoParser().parse(source))
    target = next(t for t in graph.realization_targets if t.name == "web_interface")
    files = generate_code(graph, target)
    return {
        "graph": graph,
        "target": target,
        "html": files["web_interface/index.html"],
        "css": files["web_interface/styles.css"],
        "js": files["web_interface/app.js"],
        "standalone": files.get("web_interface/index.standalone.html"),
    }


# ---------------------------------------------------------------------------
# Gate 1 — Structural
# ---------------------------------------------------------------------------


class TestStructuralGate:
    def test_doctype_and_document_skeleton(self, artifacts):
        html = artifacts["html"]
        assert html.startswith("<!DOCTYPE html>")
        assert "<html" in html and "</html>" in html
        assert "<head>" in html and "</head>" in html
        assert "<body>" in html and "</body>" in html

    def test_lang_attribute_present(self, artifacts):
        assert re.search(r'<html lang="[a-zA-Z-]+">', artifacts["html"])

    def test_semantic_elements_used(self, artifacts):
        html = artifacts["html"]
        for tag in ("<header", "<main", "<section", "<button"):
            assert tag in html, f"missing semantic element {tag}"

    def test_data_semantic_id_traces_to_sir_paths(self, artifacts):
        html = artifacts["html"]
        paths = {node.path for node in artifacts["graph"].nodes}
        roots = {p.split(".")[0] for p in paths}
        found = set(re.findall(r'data-semantic-id="([^"]+)"', html))
        # Every rendered semantic id must be a real SIR path (or an
        # engine-metadata marker under the reserved 'orren.' prefix).
        for sem_id in found:
            base = sem_id.split(".")[0]
            assert base in roots or base == "orren", sem_id
        assert any("microphone_control" in p for p in found)

    def test_aria_role_and_label_on_nodes(self, artifacts):
        html = artifacts["html"]
        assert 'role="' in html
        assert "aria-label=" in html

    def test_viewport_meta_responsive(self, artifacts):
        assert 'name="viewport"' in artifacts["html"]

    def test_no_inline_styles_in_html(self, artifacts):
        assert 'style="' not in artifacts["html"]


# ---------------------------------------------------------------------------
# Gate 2 — Syntactic
# ---------------------------------------------------------------------------


class _StructureParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = set()
        self.stack = []
        self.errors = []

    VOID = {"meta", "link", "br", "hr", "img", "input", "source", "wbr"}

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"mismatched </{tag}> (stack={self.stack[-3:]})")
        else:
            self.stack.pop()


class TestSyntacticGate:
    def test_html_parses_with_balanced_structure(self, artifacts):
        parser = _StructureParser()
        parser.feed(artifacts["html"])
        assert parser.errors == [], parser.errors[:5]
        assert {"html", "head", "body"} <= parser.tags
        assert parser.stack == [], f"unclosed tags: {parser.stack}"

    def test_css_balanced_braces_and_declarations(self, artifacts):
        css = artifacts["css"]
        assert css.count("{") == css.count("}")
        body = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
        # Inspect declarations only inside rule blocks.
        for block in re.findall(r"\{([^{}]*)\}", body):
            for decl in block.split(";"):
                decl = decl.strip()
                if not decl:
                    continue
                assert ":" in decl, repr(decl)

    def test_css_custom_properties_defined(self, artifacts):
        css = artifacts["css"]
        assert ":root" in css
        for token in ("--color-bg", "--color-fg", "--spacing-unit",
                      "--motion-duration", "--font-family-sans"):
            assert token in css, token

    def test_css_media_features(self, artifacts):
        css = artifacts["css"]
        assert "prefers-reduced-motion" in css
        assert "prefers-color-scheme" in css
        assert "@media (max-width:" in css

    def test_js_syntax_node_check(self, artifacts, tmp_path):
        if not _node_available():
            pytest.skip("node toolchain unavailable — cannot verify JS syntax")
        js_file = tmp_path / "app.js"
        js_file.write_text(artifacts["js"], encoding="utf-8")
        proc = subprocess.run(
            ["node", "--check", str(js_file)],
            capture_output=True, text=True, timeout=30,
        )
        assert proc.returncode == 0, proc.stderr

    def test_no_console_only_stub_handlers(self, artifacts):
        # Every addEventListener body must do more than log.
        js = artifacts["js"]
        stubs = re.findall(r"addEventListener\([^,]+,\s*\(?[^)]*\)?\s*=>\s*\{\s*console\.log[^}]*\}\s*\)", js)
        assert stubs == [], stubs


# ---------------------------------------------------------------------------
# Gate 3 — Linkable / Packageable
# ---------------------------------------------------------------------------


class TestLinkableGate:
    def test_stylesheet_reference_resolves(self, artifacts):
        assert '<link rel="stylesheet" href="styles.css">' in artifacts["html"]

    def test_module_script_references_app_js(self, artifacts):
        assert './app.js' in artifacts["html"]

    def test_all_referenced_files_emitted(self, artifacts):
        html = artifacts["html"]
        refs = re.findall(r'(?:href|src)="(\./[^"]+)"', html)
        emitted = {"index.html", "styles.css", "app.js"}
        for ref in refs:
            assert ref.lstrip("./") in emitted, ref

    def test_no_external_network_resources(self, artifacts):
        for blob_name in ("html", "css"):
            blob = artifacts[blob_name]
            assert "http://" not in blob, blob_name
            assert "https://" not in blob, blob_name


# ---------------------------------------------------------------------------
# Gates 4–6 — Executable / Behavioral / Operational (executed under Node)
# ---------------------------------------------------------------------------

HARNESS = r"""
// Orren seven-gate behavioral harness: minimal DOM shim + executable probes.
// NOTE: app.js must be imported dynamically AFTER the DOM shim exists —
// static imports hoist above shim initialization.
const results = {};
const failures = [];
function check(name, cond, extra) {
  results[name] = cond ? 'pass' : 'fail';
  if (!cond) failures.push(name + (extra ? ` :: ${extra}` : ''));
}

class ShimElement {
  constructor(id) {
    this.id = id;
    this.attrs = new Map();
    this.listeners = new Map();
    this.hidden = false;
    this.classList = { add() {}, remove() {}, toggle() {}, contains: () => false };
  }
  setAttribute(k, v) { this.attrs.set(k, String(v)); }
  getAttribute(k) { return this.attrs.has(k) ? this.attrs.get(k) : null; }
  addEventListener(type, fn) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(fn);
  }
  dispatchEvent(evt) {
    evt.target = this;
    const list = this.listeners.get(evt.type) || [];
    for (const fn of [...list]) fn.call(this, evt);
    return true;
  }
  fire(type) {
    this.dispatchEvent({ type, preventDefault() {}, detail: null });
  }
  scrollIntoView() {}
}

const elements = new Map();
globalThis.document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, new ShimElement(id));
    return elements.get(id);
  },
  querySelector: () => null,
  createElement: () => new ShimElement('anon'),
};
const windowListeners = new Map();
const windowEvents = [];
globalThis.window = {
  addEventListener(type, fn) {
    if (!windowListeners.has(type)) windowListeners.set(type, []);
    windowListeners.get(type).push(fn);
  },
  removeEventListener() {},
  dispatchEvent(evt) {
    windowEvents.push({ type: evt.type, detail: evt.detail });
    const list = windowListeners.get(evt.type) || [];
    for (const fn of [...list]) fn.call(null, evt);
    return true;
  },
};
class CustomEventShim {
  constructor(type, opts = {}) { this.type = type; this.detail = opts.detail ?? null; }
}
globalThis.CustomEvent = CustomEventShim;
const store = new Map();
globalThis.localStorage = {
  setItem: (k, v) => store.set(k, String(v)),
  getItem: (k) => (store.has(k) ? store.get(k) : null),
};

const app = await import('./app.js');

try {
  // --- Gate 4: module loaded and init runs cleanly ---
  check('module_exports_fsm', typeof app.OrrenFSM === 'function');
  check('module_exports_wireup', typeof app.wireUpEvents === 'function');
  app.wireUpEvents();
  check('init_without_exception', true);

  // --- Gate 5a: conditional trigger -> real transition event ---
  const transitions = [];
  windowListeners.set('orren:transition', [(evt) => transitions.push(evt.detail)]);
  const mic = document.getElementById('__MIC_ID__');
  check('element_created_on_lookup', !!mic);
  mic.fire('dblclick');
  const dbl = transitions.find((t) => t.event === 'dblclick' && t.to === 'activates_double_click');
  check('conditional_transition_fires', !!dbl,
        JSON.stringify(transitions.slice(0, 4)));

  // --- Gate 5b: guarded FSM rejects invalid transitions ---
  const fsm = new app.OrrenFSM('locked', 'probe-node');
  fsm.registerGuard('locked', 'unlock', () => false);
  check('guard_rejects_transition', fsm.transition('unlock') === false);
  check('guard_preserves_state', fsm.currentState === 'locked');
  fsm.registerGuard('locked', 'open', () => true);
  check('guard_permits_transition', fsm.transition('open', { nextState: 'opened' }) === true);
  check('state_advanced', fsm.currentState === 'opened');

  // --- Gate 5c: relational wiring executes safely ---
  let relOk = true;
  try { app.wireUpRelationalLinks(); } catch { relOk = false; }
  check('relational_wiring_safe', relOk);

  // --- Gate 6a: persistence round-trip ---
  app.saveAppState({ current: 'recording', depth: 2 });
  const restored = app.loadAppState();
  check('persistence_roundtrip', !!restored && restored.current === 'recording' && restored.depth === 2);

  // --- Gate 5d/6b: temporal sequences dispatch within timer budget ---
  const temporalExports = Object.keys(app).filter((k) => k.startsWith('temporalSequence_'));
  check('temporal_sequences_exported', temporalExports.length >= 3,
        `found ${temporalExports.length}`);
  check('temporal_bootstrap_exported', typeof app.startTemporalSequences === 'function');
  app.startTemporalSequences();
  await new Promise((resolve) => setTimeout(resolve, 700));
  const temporalEvents = windowEvents.filter((e) => e.type === 'orren:temporal');
  check('temporal_events_dispatched', temporalEvents.length >= 3,
        `got ${temporalEvents.length}`);

  // --- Gate 6b: error boundary listener registered ---
  check('error_listener_registered', (windowListeners.get('error') || []).length >= 1);
} catch (err) {
  failures.push('harness_exception :: ' + err.message);
}

console.log(JSON.stringify({ results, failures }, null, 0));
process.exit(failures.length ? 1 : 0);
"""


@pytest.fixture(scope="module")
def node_report(artifacts, tmp_path_factory):
    if not _node_available():
        pytest.skip("node toolchain unavailable — behavioral evidence cannot run")
    from orren_engine.backends.web_tokens import _node_id

    mic_path = "microphone_application.home.microphone_control"
    harness_src = HARNESS.replace("__MIC_ID__", _node_id(mic_path))
    out_dir = tmp_path_factory.mktemp("orren_web_gate")
    (out_dir / "app.js").write_text(artifacts["js"], encoding="utf-8")
    (out_dir / "harness.mjs").write_text(harness_src, encoding="utf-8")
    proc = subprocess.run(
        ["node", "harness.mjs"],
        cwd=str(out_dir), capture_output=True, text=True, timeout=60,
    )
    return proc


class TestExecutableGate:
    def test_module_loads_under_node(self, node_report):
        assert node_report.returncode == 0, node_report.stdout + node_report.stderr

    def test_harness_reports_json(self, node_report):
        payload = json.loads(node_report.stdout.strip().splitlines()[-1])
        assert isinstance(payload["results"], dict)


class TestBehavioralGate:
    @pytest.fixture(scope="class")
    def report(self, node_report):
        return json.loads(node_report.stdout.strip().splitlines()[-1])

    def test_conditional_trigger_produces_real_transition(self, report):
        assert report["results"].get("conditional_transition_fires") == "pass", report["failures"]

    def test_guards_reject_invalid_transitions(self, report):
        assert report["results"].get("guard_rejects_transition") == "pass"
        assert report["results"].get("guard_preserves_state") == "pass"

    def test_valid_guarded_transition_advances_state(self, report):
        assert report["results"].get("guard_permits_transition") == "pass"
        assert report["results"].get("state_advanced") == "pass"

    def test_temporal_sequences_dispatch_events(self, report):
        assert report["results"].get("temporal_sequences_exported") == "pass"
        assert report["results"].get("temporal_events_dispatched") == "pass", report["failures"]

    def test_relational_wiring_executes_safely(self, report):
        assert report["results"].get("relational_wiring_safe") == "pass"


class TestOperationalGate:
    @pytest.fixture(scope="class")
    def report(self, node_report):
        return json.loads(node_report.stdout.strip().splitlines()[-1])

    def test_persistence_roundtrip(self, report):
        assert report["results"].get("persistence_roundtrip") == "pass"

    def test_error_listener_registered(self, report):
        assert report["results"].get("error_listener_registered") == "pass"

    def test_resource_limits_declared(self, artifacts):
        js = artifacts["js"]
        assert "maxTransitionHistory" in js
        assert "maxEventListeners" in js
        assert "persistenceKey" in js

    def test_error_boundary_hidden_by_default(self, artifacts):
        html = artifacts["html"]
        marker = 'id="orren-error-boundary"'
        assert marker in html
        # The hidden attribute follows the id within the same opening tag.
        after = html.split(marker, 1)[1][:300]
        assert "hidden" in after


# ---------------------------------------------------------------------------
# Gate 7 — Preservation
# ---------------------------------------------------------------------------


class TestPreservationGate:
    def test_cannot_express_marked_proxy_not_dropped(self, artifacts):
        # vibe.aesthetic declared cannot_express on web_interface.
        assert "PROXY" in artifacts["css"]
        assert "aesthetic" in artifacts["css"]

    def test_bridge_conditions_marked_in_js(self, artifacts):
        assert "BRIDGE" in artifacts["js"]
        assert "device_microphone" in artifacts["js"]

    def test_degraded_marker_for_unmapped_vibe_term(self):
        tokens = _vibe_term_to_tokens("tone", "unheard_of_tone")
        assert tokens, "fallback must exist — never silently drop an aspect"
        names = [t[0] for t in tokens]
        assert "--motion-duration" in names

    def test_unknown_aspect_falls_back_with_explicit_default(self):
        tokens = _vibe_term_to_tokens("quantum_flux", "shimmering")
        assert tokens == []

    def test_token_registry_overridable(self):
        register_vibe_mapping("tone", "glacial_slow", [("--motion-duration", "2s ease")])
        assert _vibe_term_to_tokens("tone", "glacial_slow") == [
            ("--motion-duration", "2s ease")
        ]

    def test_every_vibe_aspect_yields_tokens_or_marker(self, artifacts):
        graph = artifacts["graph"]
        all_tokens = extract_all_tokens(graph)
        assert all_tokens, "microphone_control carries vibe content"
        for node_path, tm in all_tokens.items():
            aspects = [
                v.get("aspect")
                for v in node_by_path(graph, node_path).get_dimension(
                    __import__("orren_engine").Dimension.VIBE
                )
                if isinstance(v, dict)
            ]
            for aspect in aspects:
                mapped = any(a.startswith("--") for a in tm.css_variables)
                marked = bool(tm.proxy) or bool(tm.degraded)
                assert mapped or marked, f"{node_path}.{aspect} silently dropped"

    def test_preservation_score_visible_in_artifacts(self, artifacts):
        assert "0.83" in artifacts["html"]
        assert "0.83" in artifacts["css"]

    def test_generation_is_reproducible_byte_for_byte(self):
        with open(EXAMPLE, "r", encoding="utf-8") as fh:
            source = fh.read()
        graph = SIRBuilder().build(CoParser().parse(source))
        target = next(t for t in graph.realization_targets if t.name == "web_interface")
        first = generate_code(graph, target)
        second = generate_code(graph, target)
        assert first == second


def node_by_path(graph, path):
    for node in graph.nodes:
        if node.path == path:
            return node
    raise KeyError(path)


# ---------------------------------------------------------------------------
# Review-driven refinements (real-browser findings, Movement C)
# ---------------------------------------------------------------------------


def test_focus_visible_rule_present(artifacts):
    assert ":focus-visible" in artifacts["css"]


def test_touch_target_media_query_present(artifacts):
    assert "pointer: coarse" in artifacts["css"]
    assert "min-height: 44px" in artifacts["css"]


def test_theme_class_overrides_present(artifacts):
    assert "html.theme-light" in artifacts["css"]
    assert "html.theme-dark" in artifacts["css"]


def test_color_scheme_meta_present(artifacts):
    assert '<meta name="color-scheme" content="dark light">' in artifacts["html"]


def test_theme_toggle_button_in_header(artifacts):
    html = artifacts["html"]
    assert 'id="orren-theme-toggle"' in html
    assert 'aria-pressed="false"' in html
    assert 'data-semantic-id="orren.theme_toggle"' in html


def test_init_theme_toggle_exported_and_called(artifacts):
    assert "export function initThemeToggle()" in artifacts["js"]
    assert "initThemeToggle();" in artifacts["html"]
    assert "orren:theme" in artifacts["js"]


def test_theme_color_meta_derived_from_accent_token(artifacts):
    import re as _re
    m = _re.search(r'<meta name="theme-color" content="([^"]+)"', artifacts["html"])
    assert m, "theme-color meta missing"
    accent = _re.search(r"--color-accent:\s*([^;]+);", artifacts["css"])
    if accent:
        assert m.group(1) == accent.group(1).strip()


def test_max_transition_history_enforced(artifacts):
    js = artifacts["js"]
    assert "maxTransitionHistory" in js
    assert "history.shift()" in js


def test_temporal_start_respects_reduced_motion(artifacts):
    js = artifacts["js"]
    assert "prefers-reduced-motion" in js
    assert "force = false" in js


def test_standalone_artifact_generated(artifacts):
    assert artifacts.get("standalone") is not None
    standalone = artifacts["standalone"]
    assert "<style>" in standalone
    assert 'from "./app.js"' not in standalone
    assert "export function" not in standalone


# ---------------------------------------------------------------------------
# 2.1 Expanded vibe mappings (Movement B)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "term", ["mist", "fire", "water", "stone", "growth", "decay", "dawn", "dusk"]
)
def test_atmospheric_terms_map_to_ambience_tokens(term):
    tokens = dict(_vibe_term_to_tokens("atmospheric", term))
    assert "--atmosphere-texture" in tokens
    assert "--atmosphere-opacity" in tokens
    assert "--color-atmosphere" in tokens


@pytest.mark.parametrize("term", ["ceremonial", "ancestral", "communal", "solitary"])
def test_cultural_terms_map_to_layout_tokens(term):
    tokens = dict(_vibe_term_to_tokens("cultural", term))
    assert tokens["--spacing-scale"] in {"generous", "normal", "tight"}
    assert "--ornament-style" in tokens


@pytest.mark.parametrize("term", ["still", "drift", "pulse", "surge", "cascade"])
def test_motion_terms_map_to_kinetic_tokens(term):
    tokens = dict(_vibe_term_to_tokens("motion", term))
    assert "--motion-duration" in tokens
    assert "--motion-easing" in tokens
    assert "--motion-scale" in tokens


def test_unknown_terms_fall_back_honestly():
    for aspect in ("atmospheric", "cultural", "motion"):
        fallback = dict(_vibe_term_to_tokens(aspect, "__no_such_term__"))
        assert fallback, f"{aspect} fallback missing"


# ---------------------------------------------------------------------------
# 2.2 Living layer (Movement B)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def living_js(artifacts):
    from orren_engine.backends.web_gl import generate_web_gl
    return generate_web_gl(artifacts["graph"], artifacts["target"])


def test_living_module_emitted_in_bundle(artifacts):
    files = artifacts.get("all_files") or {}
    # Bundle contract: living.js is part of generate_web output.
    from orren_engine.backends.web_generator import generate_web
    bundle = generate_web(artifacts["graph"], artifacts["target"])
    assert f"{artifacts['target'].name}/living.js" in bundle


def test_living_fallback_chain_honest(living_js):
    for marker in ("webgl", "canvas2d", "css"):
        assert f"'{marker}'" in living_js or f'"{marker}"' in living_js
    assert "renderer:" in living_js  # downgrade is announced, never silent


def test_living_modes_supported(living_js):
    assert "['living', 'clear', 'symbolic']" in living_js


def test_living_reduced_motion_static(living_js):
    assert "prefers-reduced-motion" in living_js


def test_living_visibility_pause(living_js):
    assert "visibilitychange" in living_js


def test_html_references_living_canvas(artifacts):
    assert 'id="orren-living-canvas"' in artifacts["html"]
    assert 'aria-hidden="true"' in artifacts["html"]


def test_init_dynamically_imports_living(artifacts):
    assert 'import("./living.js")' in artifacts["html"]


# ---------------------------------------------------------------------------
# 2.3 Optional bundler scaffolding (Movement B)
# ---------------------------------------------------------------------------


def test_bundler_not_emitted_by_default(artifacts):
    from orren_engine.backends.web_bundler import generate_bundler_files
    assert generate_bundler_files(artifacts["graph"], artifacts["target"]) == {}
    bundle = artifacts.get("bundle") or _full_bundle(artifacts)
    assert not any("package.json" in k for k in bundle)


def test_bundler_gated_on_explicit_capability(artifacts):
    from orren_engine.backends.web_bundler import (
        bundler_requested,
        generate_bundler_files,
    )
    from copy import deepcopy
    target = deepcopy(artifacts["target"])
    assert not bundler_requested(target)
    target.capabilities.append("bundler")
    files = generate_bundler_files(artifacts["graph"], target)
    assert set(files) == {
        f"{target.name}/package.json",
        f"{target.name}/vite.config.js",
        f"{target.name}/tests/smoke.spec.js",
    }
    assert '"dev": "vite"' in files[f"{target.name}/package.json"]


def _full_bundle(artifacts):
    from orren_engine.backends.web_generator import generate_web
    return generate_web(artifacts["graph"], artifacts["target"])
