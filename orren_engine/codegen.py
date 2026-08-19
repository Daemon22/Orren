"""
Orren Engine — Code Generator
=============================

Takes a SIR graph + a RealizationTarget and produces actual source code
in the target language. Where a dimension cannot be fully expressed,
the generator emits an explicit comment marker (PROXY / BRIDGE / OUT_OF_SCOPE)
so the gap is visible in the artifact, not silent.

Targets supported:
    web_interface       HTML + CSS + JS
    typescript          TypeScript (type-safe web front-end)
    native_shell        Swift (iOS) / Kotlin (Android) — chosen by language
    embedded_controller C (microcontrollers / embedded systems)
    contract_document   LaTeX (typesetting / PDF)
    ambient_audio       WebAudio (browser procedural audio)
    transcription_service   Python (speech-to-text)
    audio_storage       Python (filesystem retention)
    *backend, *service, *engine, *watcher  Python (general service)
    rust_backend        Rust (systems / performance)
    go_backend         Go (backend microservices)
    (fallback)          Manifest describing gaps

Each generator function returns a dict {filename: code_string} so the
caller can write them to disk or inspect them in tests.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from .data_model import (
    Dimension,
    RealizationTarget,
    SIRGraph,
    SIRNode,
    ToleranceLevel,
)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    """Generate code for one target. Returns {filename: code}."""
    name = target.name
    lang = target.language.lower()

    # --- Explicit language dispatch (most specific) ---
    if lang == "c" or "c_source" in name:
        return _gen_c(graph, target)
    if lang == "latex" or "tex" in lang or "latex" in name:
        return _gen_latex(graph, target)
    if "webaudio" in lang or "webaudio" in name:
        return _gen_webaudio(graph, target)
    if lang == "rust":
        return _gen_rust(graph, target)
    if lang == "go":
        return _gen_go(graph, target)
    if lang == "typescript" or "typescript" in name:
        return _gen_typescript(graph, target)
    if lang == "swift":
        return _gen_swift(graph, target)
    if lang == "kotlin":
        return _gen_kotlin(graph, target)
    if lang == "python":
        # Route to the specialized Python generators first, then general.
        if "transcription" in name:
            return _gen_transcription_service(graph, target)
        if "storage" in name:
            return _gen_audio_storage(graph, target)
        if "input" in name or "button" in name:
            return _gen_input_watcher(graph, target)
        return _gen_python_service(graph, target)

    # --- Name-based dispatch (targets without explicit language) ---
    if "web" in name or "html" in name or "css" in name or "js" in name:
        return _gen_web(graph, target)
    if "native" in name or "swift" in lang or "kotlin" in lang:
        return _gen_native(graph, target)

    # --- Fallback: manifest ---
    return _gen_manifest(graph, target)


# ---------------------------------------------------------------------------
# Web target — HTML + CSS + JS
# ---------------------------------------------------------------------------


def _gen_web(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    base = target.name
    html_parts: List[str] = []
    css_parts: List[str] = []
    js_parts: List[str] = []

    html_parts.append("<!DOCTYPE html>")
    html_parts.append('<html lang="en">')
    html_parts.append("<head>")
    html_parts.append(f'  <meta charset="utf-8">')
    html_parts.append(f'  <title>{_escape(_graph_title(graph))}</title>')
    html_parts.append(f'  <link rel="stylesheet" href="styles.css">')
    html_parts.append("</head>")
    html_parts.append("<body>")

    # Walk spatial structure — emit a <div> for each entity node that has
    # spatial or vibe content.
    for node in graph.nodes:
        if node.kind == "root":
            continue
        if not node.has_dimension_content(Dimension.SPATIAL) and not node.has_dimension_content(Dimension.VIBE):
            continue
        depth = node.path.count(".")
        indent = "  " * (depth + 1)
        html_parts.append(f'{indent}<div id="{_css_id(node.path)}" class="orren-entity">')
        html_parts.append(f'{indent}  <!-- entity: {node.path} -->')
        html_parts.append(f'{indent}</div>')

    html_parts.append('  <script src="app.js"></script>')
    html_parts.append("</body>")
    html_parts.append("</html>")

    # CSS — emit rules from vibe payloads.
    css_parts.append("/* Orren-generated stylesheet */")
    css_parts.append("/* PROXY markers indicate vibe aspects expressed as proxy. */")
    css_parts.append("")
    for node in graph.nodes:
        vibes = node.get_dimension(Dimension.VIBE)
        if not vibes:
            continue
        selector = f"#{_css_id(node.path)}"
        rules: List[str] = []
        proxy_comments: List[str] = []
        for v in vibes:
            if not isinstance(v, dict):
                continue
            aspect = v.get("aspect", "")
            term = v.get("term", "")
            if aspect == "color_character":
                color = _map_color(term)
                rules.append(f"  background-color: {color};")
            elif aspect == "form_character":
                radius = "24px" if "organic" in term else "4px"
                rules.append(f"  border-radius: {radius};")
            elif aspect == "tone":
                if "calm" in term:
                    rules.append("  transition: all 600ms ease;")
                else:
                    rules.append("  transition: all 200ms ease;")
            elif aspect == "aesthetic":
                proxy_comments.append(
                    f"  /* PROXY: aesthetic '{term}' has no single CSS signal; "
                    f"approximated via typography + motion. */"
                )
            elif aspect == "activation_signal":
                if "glow" in term:
                    rules.append("  box-shadow: 0 0 16px rgba(80, 200, 120, 0.6);")
                else:
                    proxy_comments.append(
                        f"  /* PROXY: activation_signal '{term}' — no direct CSS equivalent. */"
                    )
        # Apply degradation tolerance markers.
        for key, entry in node.degradation_tolerance.items():
            if entry.level == ToleranceLevel.PROXY:
                proxy_comments.append(
                    f"  /* PROXY (tolerated): {key} — target cannot fully express. */"
                )
        css_parts.append(f"{selector} {{")
        css_parts.extend(rules)
        css_parts.append("}")
        if proxy_comments:
            css_parts.extend(proxy_comments)

    # JS — emit event handlers from conditional + behavioral.
    js_parts.append("// Orren-generated event handlers")
    js_parts.append("'use strict';")
    js_parts.append("")
    for node in graph.nodes:
        conds = node.get_dimension(Dimension.CONDITIONAL)
        behs = node.get_dimension(Dimension.BEHAVIORAL)
        if not conds and not behs:
            continue
        node_id = _css_id(node.path)
        for c in conds:
            if not isinstance(c, dict):
                continue
            cond = c.get("condition", "")
            if "double_click" in cond:
                js_parts.append(
                    f"document.getElementById('{node_id}').addEventListener('dblclick', () => {{"
                )
                js_parts.append(f"  // activates: {c.get('subject', '')} on {cond}")
                js_parts.append(f"  console.log('activated: {node.path}');")
                js_parts.append("});")
                js_parts.append("")
            elif "volume_down" in cond:
                js_parts.append(
                    f"/* BRIDGE: volume_down event not directly available in web; "
                    f"requires native shell or media-keys API. */"
                )
                js_parts.append(
                    f"// {c.get('subject', '')} activates on {cond}"
                )
                js_parts.append("")
            else:
                js_parts.append(
                    f"// {c.get('subject', '')} activates on {cond}"
                )
        for b in behs:
            if not isinstance(b, dict):
                continue
            if b.get("kind") == "lifecycle":
                lifecycle = b.get("lifecycle", [])
                if lifecycle:
                    chain = " -> ".join(
                        f"{t.get('from_state', '')}/{t.get('to_state', '')}"
                        for t in lifecycle
                    )
                    js_parts.append(
                        f"// lifecycle for {b.get('subject', '')}: {chain}"
                    )

    return {
        f"{base}/index.html": "\n".join(html_parts) + "\n",
        f"{base}/styles.css": "\n".join(css_parts) + "\n",
        f"{base}/app.js": "\n".join(js_parts) + "\n",
    }


# ---------------------------------------------------------------------------
# Native shell target — Swift (chosen by default)
# ---------------------------------------------------------------------------


def _gen_native(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    base = target.name
    lang = target.language.lower()
    if "kotlin" in lang:
        return _gen_kotlin(graph, target)
    return _gen_swift(graph, target)


def _gen_swift(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    base = target.name
    title = _graph_title(graph)
    parts: List[str] = []
    parts.append("// Orren-generated Swift (iOS)")
    parts.append(f"// Target: {target.name} ({target.language})")
    parts.append(f"// Application: {title}")
    parts.append("")
    parts.append("import UIKit")
    parts.append("import AVFoundation")
    parts.append("")
    parts.append(f"class {_swift_class_name(title)}: UIViewController {{")
    parts.append("    override func viewDidLoad() {")
    parts.append("        super.viewDidLoad()")
    parts.append("        view.backgroundColor = UIColor(red: 0.0, green: 0.5, blue: 0.3, alpha: 1.0)")
    parts.append("        setupUI()")
    parts.append("    }")
    parts.append("")
    parts.append("    func setupUI() {")
    for node in graph.nodes:
        if node.kind == "root":
            continue
        if not node.has_dimension_content(Dimension.SPATIAL) and not node.has_dimension_content(Dimension.VIBE):
            continue
        var_name = _swift_var(node.name)
        parts.append(f"        let {var_name} = UIView()")
        parts.append(f"        {var_name}.accessibilityIdentifier = \"{node.path}\"")
        # Apply vibe color if present.
        for v in node.get_dimension(Dimension.VIBE):
            if isinstance(v, dict) and v.get("aspect") == "color_character":
                color = _map_color(v.get("term", ""))
                parts.append(f"        {var_name}.backgroundColor = {_swift_color(color)}")
        parts.append(f"        view.addSubview({var_name})")
    parts.append("    }")
    parts.append("")
    # Add device microphone activation if cognitive.activation is present.
    has_mic = any(
        any(
            isinstance(c, dict) and "activation" in str(c.get("predicate", ""))
            for c in node.get_dimension(Dimension.COGNITIVE)
        )
        for node in graph.nodes
    )
    if has_mic:
        parts.append("    private var audioEngine = AVAudioEngine()")
        parts.append("")
        parts.append("    func activateMicrophone() {")
        parts.append("        let session = AVAudioSession.sharedInstance()")
        parts.append("        try? session.setCategory(.record)")
        parts.append("        try? session.setActive(true)")
        parts.append("        let inputNode = audioEngine.inputNode")
        parts.append("        // Recording tap installed")
        parts.append("        try? audioEngine.start()")
        parts.append("    }")
    parts.append("}")
    return {f"{base}/Main.swift": "\n".join(parts) + "\n"}


def _gen_kotlin(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    base = target.name
    title = _graph_title(graph)
    parts: List[str] = []
    parts.append("// Orren-generated Kotlin (Android)")
    parts.append(f"// Target: {target.name} ({target.language})")
    parts.append(f"// Application: {title}")
    parts.append("")
    parts.append("package com.orren.generated")
    parts.append("")
    parts.append("import android.app.Activity")
    parts.append("import android.os.Bundle")
    parts.append("import android.widget.RelativeLayout")
    parts.append("import android.view.View")
    parts.append("")
    parts.append(f"class {_kotlin_class_name(title)} : Activity() {{")
    parts.append("    override fun onCreate(savedInstanceState: Bundle?) {")
    parts.append("        super.onCreate(savedInstanceState)")
    parts.append("        val root = RelativeLayout(this)")
    parts.append("        setContentView(root)")
    for node in graph.nodes:
        if node.kind == "root":
            continue
        if not node.has_dimension_content(Dimension.SPATIAL) and not node.has_dimension_content(Dimension.VIBE):
            continue
        var_name = _swift_var(node.name)
        parts.append(f"        val {var_name} = View(this)")
        parts.append(f"        {var_name}.tag = \"{node.path}\"")
        parts.append(f"        root.addView({var_name})")
    parts.append("    }")
    parts.append("}")
    return {f"{base}/Main.kt": "\n".join(parts) + "\n"}


# ---------------------------------------------------------------------------
# Transcription service target — Python
# ---------------------------------------------------------------------------


def _gen_transcription_service(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    base = target.name
    parts: List[str] = []
    parts.append('"""Orren-generated transcription service.')
    parts.append(f'Target: {target.name} ({target.language})')
    parts.append('')
    parts.append('Scoped responsibility: cognitive.transcription only.')
    parts.append('All other dimensions are OUT_OF_SCOPE for this target.')
    parts.append('"""')
    parts.append('')
    parts.append('from __future__ import annotations')
    parts.append('')
    parts.append('')
    parts.append('def transcribe(audio_recording: bytes) -> str:')
    parts.append('    """Transcribe an audio recording to text.')
    parts.append('')
    parts.append('    This function satisfies the cognitive.transcription contract.')
    parts.append('    The original_audio is preserved upstream (cognitive.preservation).')
    parts.append('    """')
    parts.append('    # PROXY: actual speech-to-text backend not bundled;')
    parts.append('    # wire this to your preferred transcription service.')
    parts.append('    raise NotImplementedError(')
    parts.append('        "Connect transcribe() to a speech-to-text backend."')
    parts.append('    )')
    parts.append('')
    parts.append('')
    parts.append('def transcribe_with_metadata(audio_recording: bytes) -> dict:')
    parts.append('    """Transcribe and return structured metadata."""')
    parts.append('    text = transcribe(audio_recording)')
    parts.append('    return {')
    parts.append('        "text": text,')
    parts.append('        "source_preserved": True,  # cognitive.preservation is honored upstream')
    parts.append('    }')
    return {f"{base}/transcription.py": "\n".join(parts) + "\n"}


# ---------------------------------------------------------------------------
# Audio storage target — Python (filesystem)
# ---------------------------------------------------------------------------


def _gen_audio_storage(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    base = target.name
    parts: List[str] = []
    parts.append('"""Orren-generated audio storage service.')
    parts.append(f'Target: {target.name} ({target.language})')
    parts.append('')
    parts.append('Scoped responsibility: cognitive.preservation (retain original_audio).')
    parts.append('HARD CONTRACT: original_audio is retained unconditionally,')
    parts.append('even if storage is constrained or transcription succeeds.')
    parts.append('"""')
    parts.append('')
    parts.append('from __future__ import annotations')
    parts.append('')
    parts.append('import os')
    parts.append('import hashlib')
    parts.append('import time')
    parts.append('')
    parts.append('')
    parts.append('class AudioStorage:')
    parts.append('    def __init__(self, root_dir: str = "/var/orren/audio"):')
    parts.append('        self.root_dir = root_dir')
    parts.append('        os.makedirs(root_dir, exist_ok=True)')
    parts.append('')
    parts.append('    def retain(self, audio_bytes: bytes, recording_id: str | None = None) -> str:')
    parts.append('        """Retain original audio. This is an unconditional contract."""')
    parts.append('        if recording_id is None:')
    parts.append('            recording_id = hashlib.sha256(audio_bytes).hexdigest()[:16]')
    parts.append('        path = os.path.join(self.root_dir, f"{recording_id}.bin")')
    parts.append('        with open(path, "wb") as f:')
    parts.append('            f.write(audio_bytes)')
    parts.append('        # Write a sidecar manifest recording the preservation contract.')
    parts.append('        manifest = {')
    parts.append('            "recording_id": recording_id,')
    parts.append('            "retained_at": time.time(),')
    parts.append('            "bytes": len(audio_bytes),')
    parts.append('            "contract": "unconditional_preservation",')
    parts.append('        }')
    parts.append('        with open(path + ".manifest.json", "w") as f:')
    parts.append('            import json')
    parts.append('            json.dump(manifest, f)')
    parts.append('        return path')
    parts.append('')
    parts.append('    def retrieve(self, recording_id: str) -> bytes:')
    parts.append('        path = os.path.join(self.root_dir, f"{recording_id}.bin")')
    parts.append('        with open(path, "rb") as f:')
    parts.append('            return f.read()')
    return {f"{base}/storage.py": "\n".join(parts) + "\n"}


# ---------------------------------------------------------------------------
# Input button watcher target — Python
# ---------------------------------------------------------------------------


def _gen_input_watcher(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    base = target.name
    parts: List[str] = []
    parts.append('"""Orren-generated input button watcher.')
    parts.append(f'Target: {target.name} ({target.language})')
    parts.append('')
    parts.append('Scoped responsibility: detect activation conditions')
    parts.append('(double_click, volume_down x2) and emit activation signals.')
    parts.append('"""')
    parts.append('')
    parts.append('from __future__ import annotations')
    parts.append('')
    parts.append('import time')
    parts.append('from collections import deque')
    parts.append('')
    parts.append('')
    parts.append('class InputButtonWatcher:')
    parts.append('    """Detects double-click and volume-down-x2 sequences."""')
    parts.append('')
    parts.append('    DOUBLE_CLICK_WINDOW_MS = 400')
    parts.append('    VOLUME_DOWN_SEQUENCE = 2')
    parts.append('    VOLUME_DOWN_WINDOW_MS = 800')
    parts.append('')
    parts.append('    def __init__(self) -> None:')
    parts.append('        self._click_times: deque = deque(maxlen=2)')
    parts.append('        self._volume_down_times: deque = deque(maxlen=self.VOLUME_DOWN_SEQUENCE)')
    parts.append('        self._activation_callbacks = []')
    parts.append('')
    parts.append('    def on_activation(self, callback) -> None:')
    parts.append('        self._activation_callbacks.append(callback)')
    parts.append('')
    parts.append('    def _fire_activation(self, source: str) -> None:')
    parts.append('        for cb in self._activation_callbacks:')
    parts.append('            cb(source)')
    parts.append('')
    parts.append('    def report_click(self) -> None:')
    parts.append('        now_ms = time.time() * 1000')
    parts.append('        self._click_times.append(now_ms)')
    parts.append('        if len(self._click_times) == 2:')
    parts.append('            if self._click_times[1] - self._click_times[0] <= self.DOUBLE_CLICK_WINDOW_MS:')
    parts.append('                self._fire_activation("double_click")')
    parts.append('                self._click_times.clear()')
    parts.append('')
    parts.append('    def report_volume_down(self) -> None:')
    parts.append('        now_ms = time.time() * 1000')
    parts.append('        self._volume_down_times.append(now_ms)')
    parts.append('        if len(self._volume_down_times) == self.VOLUME_DOWN_SEQUENCE:')
    parts.append('            span = self._volume_down_times[-1] - self._volume_down_times[0]')
    parts.append('            if span <= self.VOLUME_DOWN_WINDOW_MS:')
    parts.append('                self._fire_activation("volume_down_x2")')
    parts.append('                self._volume_down_times.clear()')
    return {f"{base}/watcher.py": "\n".join(parts) + "\n"}


# ---------------------------------------------------------------------------
# WebAudio target — browser procedural audio via Web Audio API
# ---------------------------------------------------------------------------


def _gen_webaudio(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    """Generate JavaScript using the Web Audio API from vibe dimensions."""
    base = target.name
    parts: List[str] = []
    parts.append("// Orren-generated WebAudio (procedural audio)")
    parts.append(f"// Target: {target.name} ({target.language})")
    parts.append(f"// Application: {_graph_title(graph)}")
    parts.append("")
    parts.append("const audioContext = new (window.AudioContext || window.webkitAudioContext)();")
    parts.append("")

    # Emit one function per vibe node with audio-relevant aspects
    for node in graph.nodes:
        vibes = node.get_dimension(Dimension.VIBE)
        if not vibes:
            continue
        fn_name = f"play_{_js_identifier(node.path)}"
        parts.append(f"function {fn_name}() {{")
        parts.append(f"  // entity: {node.path}")
        has_audio_vibe = False
        for v in vibes:
            if not isinstance(v, dict):
                continue
            aspect = v.get("aspect", "")
            term = v.get("term", "")
            if aspect in ("tone", "aesthetic", "form_character"):
                has_audio_vibe = True
                if aspect == "tone":
                    # Map tone terms to frequency
                    freq = _vibe_to_freq(term)
                    parts.append(f"  // vibe.tone = {term}")
                    parts.append(f"  const oscillator = audioContext.createOscillator();")
                    parts.append(f"  oscillator.frequency.value = {freq};")
                    parts.append(f"  oscillator.connect(audioContext.destination);")
                    parts.append(f"  oscillator.start();")
                    parts.append(f"  oscillator.stop(audioContext.currentTime + 0.5);")
                elif aspect == "aesthetic":
                    parts.append(f"  // PROXY: aesthetic '{term}' approximated via waveform + envelope")
                    parts.append(f"  const osc = audioContext.createOscillator();")
                    parts.append(f"  osc.type = '{_aesthetic_to_waveform(term)}';")
                    parts.append(f"  osc.connect(audioContext.destination);")
                    parts.append(f"  osc.start();")
                    parts.append(f"  osc.stop(audioContext.currentTime + 0.3);")
            else:
                parts.append(f"  // VIBE {aspect}={term} (not directly mappable to audio)")
        if not has_audio_vibe:
            parts.append(f"  // No audio-relevant vibe on this node; emitting silence marker.")
            parts.append(f"  // OUT_OF_SCOPE: {node.path} has vibe but no tone/aesthetic")
        parts.append("}")
        parts.append("")

    # Emit cognitive-driven audio processing if present
    has_cog = False
    for node in graph.nodes:
        cog = node.get_dimension(Dimension.COGNITIVE)
        for c in cog:
            if isinstance(c, dict) and ("audio" in str(c.get("predicate", "")) or "sound" in str(c.get("subject", ""))):
                has_cog = True
                parts.append(f"// cognitive: {c.get('subject','')} {c.get('predicate','')} = {c.get('value','')}")
    if not has_cog:
        parts.append("// No cognitive audio processing specified")
    parts.append("")

    # Check for degradation tolerance
    for node in graph.nodes:
        for key, entry in node.degradation_tolerance.items():
            if entry.level == ToleranceLevel.PROXY:
                parts.append(f"// PROXY (tolerated): {node.path}.{key} — audio quality proxy")

    return {f"{base}/audio_engine.js": "\n".join(parts) + "\n"}


def _vibe_to_freq(term: str) -> str:
    """Map vibe tone terms to approximate frequencies in Hz."""
    lower = term.lower()
    mapping = {
        "calm": "220",
        "warm": "330",
        "cool": "440",
        "bright": "660",
        "deep": "110",
        "gentle": "261",
        "intense": "880",
    }
    for key, freq in mapping.items():
        if key in lower:
            return freq
    return "440"


def _aesthetic_to_waveform(term: str) -> str:
    """Map aesthetic vibe terms to Web Audio oscillator types."""
    lower = term.lower()
    if "dark" in lower or "mysterious" in lower:
        return "sawtooth"
    if "calm" in lower or "smooth" in lower:
        return "sine"
    if "energetic" in lower or "bright" in lower:
        return "square"
    return "sine"


# ---------------------------------------------------------------------------
# Type-safe TypeScript target — typed web front-end
# ---------------------------------------------------------------------------


def _gen_typescript(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    """Generate TypeScript interfaces and classes from the SIR graph."""
    base = target.name
    title = _graph_title(graph)
    parts: List[str] = []
    parts.append("// Orren-generated TypeScript")
    parts.append(f"// Target: {target.name} ({target.language})")
    parts.append(f"// Application: {title}")
    parts.append("")

    # Emit interfaces for each spatial entity with vibe properties
    parts.append("// --- Entity Interfaces ---")
    for node in graph.nodes:
        if node.kind == "root":
            continue
        if not node.has_dimension_content(Dimension.SPATIAL) and not node.has_dimension_content(Dimension.VIBE):
            continue
        has_vibe = bool(node.get_dimension(Dimension.VIBE))
        has_cog = bool(node.get_dimension(Dimension.COGNITIVE))

        if has_vibe or has_cog:
            iface_name = _typescript_class_name(node.path)
            parts.append(f"export interface {iface_name} {{")

            if has_cog:
                for c in node.get_dimension(Dimension.COGNITIVE):
                    if isinstance(c, dict):
                        pred = c.get("predicate", "value")
                        val = c.get("value", "any")
                        parts.append(f"  {pred}: {_infer_ts_type(val)};")

            if has_vibe:
                for v in node.get_dimension(Dimension.VIBE):
                    if isinstance(v, dict):
                        aspect = v.get("aspect", "property")
                        parts.append(f"  vibe_{aspect}: string;")

            # Spatial location
            spatial = node.get_dimension(Dimension.SPATIAL)
            if spatial:
                for s in spatial:
                    if isinstance(s, dict):
                        parts.append(f"  located_{s.get('relation','located_in')}: string;")

            # Conditional activation
            conds = node.get_dimension(Dimension.CONDITIONAL)
            if conds:
                parts.append("  onActivate: (source: string) => void;")

            parts.append("}")
            parts.append("")

    # Emit a main class
    parts.append("// --- Main Component Class ---")
    class_name = _typescript_class_name(title)
    parts.append(f"export class {class_name} {{")
    parts.append(f"  private entities: Map<string, object> = new Map();")
    parts.append("")

    # Instantiate entities from spatial structure
    for node in graph.nodes:
        if node.kind == "root" or not node.has_dimension_content(Dimension.SPATIAL):
            continue
        var_name = _typescript_var_name(node.path)
        parts.append(f"  public {var_name}: {_typescript_class_name(node.path)} | null = null;")

    parts.append("")
    parts.append("  constructor() {")
    parts.append("    this.initialize();")
    parts.append("  }")
    parts.append("")
    parts.append("  private initialize(): void {")

    for node in graph.nodes:
        if node.kind == "root" or not node.has_dimension_content(Dimension.SPATIAL):
            continue
        var_name = _typescript_var_name(node.path)
        parts.append(f"    this.{var_name} = {{ /* {node.path} */ }};")

    # Type-safe vibe properties
    parts.append("")
    parts.append("    // Vibe properties (type-safe)")
    for node in graph.nodes:
        vibes = node.get_dimension(Dimension.VIBE)
        if not vibes:
            continue
        var_name = _typescript_var_name(node.path)
        for v in vibes:
            if isinstance(v, dict):
                aspect = v.get("aspect", "property")
                term = v.get("term", "")
                parts.append(f"    if (this.{var_name}) {{")
                parts.append(f"      (this.{var_name} as any).vibe_{aspect} = '{term}';")
                parts.append(f"    }}")

    parts.append("  }")
    parts.append("")

    # Event handling from conditional dimensions
    conds_found = False
    for node in graph.nodes:
        conds = node.get_dimension(Dimension.CONDITIONAL)
        for c in conds:
            if isinstance(c, dict):
                conds_found = True
                cond = c.get("condition", "activation")
                subject = c.get("subject", node.name)
                parts.append(f"  public handle{subject.capitalize()}: (event: Event) => void = (event) => {{")
                parts.append(f"    // activates on: {cond}")
                parts.append(f"    console.log('activated: {node.path}');")
                parts.append(f"  }};")
                parts.append("")

    if not conds_found:
        parts.append("  // No conditional activations specified")
        parts.append("  public handleActivate: (event: Event) => void = (event) => {")
        parts.append("    console.log('default activation handler');")
        parts.append("  };")
        parts.append("")

    # Degradation tolerance markers
    proxy_count = 0
    for node in graph.nodes:
        for key, entry in node.degradation_tolerance.items():
            if entry.level == ToleranceLevel.PROXY:
                proxy_count += 1
    if proxy_count:
        parts.append(f"  // DEGRADATION: {proxy_count} proxy tolerances acknowledged")

    parts.append("}")
    parts.append("")
    parts.append(f"export default {class_name};")

    return {f"{base}/app.ts": "\n".join(parts) + "\n"}


def _infer_ts_type(val: str) -> str:
    """Infer a TypeScript type from a cognitive value string."""
    v = val.strip().lower()
    if v in ("true", "false"):
        return "boolean"
    if v.isdigit():
        return "number"
    if v.startswith("'") or v.startswith('"') or v.startswith("0") or v.startswith("#"):
        return "string"
    # Multi-word = string
    if " " in v:
        return "string"
    return "any"


def _typescript_class_name(path: str) -> str:
    """Convert a dot-path to a PascalCase TypeScript class/interface name."""
    parts = path.replace("_", " ").split(".")
    return "".join(p.capitalize() for p in parts if p)


def _typescript_var_name(path: str) -> str:
    """Convert a dot-path to a camelCase TypeScript variable name."""
    parts = path.split(".")
    if len(parts) == 1:
        return parts[0].lower()
    return parts[-1].replace("_", "").lower()


# ---------------------------------------------------------------------------
# C target — embedded systems / microcontrollers
# ---------------------------------------------------------------------------


def _gen_c(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    """Generate C code for embedded/microcontroller targets."""
    base = target.name
    title = _graph_title(graph)
    parts: List[str] = []
    parts.append("// Orren-generated C (embedded system)")
    parts.append(f"// Target: {target.name} ({target.language})")
    parts.append(f"// Application: {title}")
    parts.append("")
    parts.append("#include <stdint.h>")
    parts.append("#include <stdbool.h>")
    parts.append("#include <string.h>")
    parts.append("")

    # Emit structs for each entity node
    parts.append("// --- Entity State Structs ---")
    for node in graph.nodes:
        if node.kind == "root":
            continue
        cog = node.get_dimension(Dimension.COGNITIVE)
        if not cog:
            continue
        struct_name = _c_struct_name(node.path)
        parts.append(f"typedef struct {{")
        for c in cog:
            if isinstance(c, dict):
                pred = c.get("predicate", "value")
                parts.append(f"    bool {pred}_active;")
        parts.append(f"}} {struct_name};")
        parts.append("")

    # Instantiate state for each entity
    parts.append("// --- Entity State Instances ---")
    for node in graph.nodes:
        cog = node.get_dimension(Dimension.COGNITIVE)
        if not cog:
            continue
        struct_name = _c_struct_name(node.path)
        var_name = _c_var_name(node.path)
        parts.append(f"static {struct_name} {var_name};")
    parts.append("")

    # Vibe → LED color mapping
    parts.append("// --- LED Color Definitions (from vibe dimensions) ---")
    color_count = 0
    for node in graph.nodes:
        vibes = node.get_dimension(Dimension.VIBE)
        if not vibes:
            continue
        for v in vibes:
            if isinstance(v, dict) and v.get("aspect") == "color_character":
                color = _map_color(v.get("term", ""))
                var_name = _c_var_name(node.path)
                parts.append(f"// {node.path}: color_character = {v.get('term', '')}")
                parts.append(f"#define {var_name.upper()}_LED_COLOR 0x{color[1:].upper()}")
                color_count += 1
    if color_count == 0:
        parts.append("// No vibe color_character dimensions; using default")
    parts.append("")

    # Main loop with conditional activation
    parts.append("// --- Main Loop ---")
    parts.append("int main(void) {")
    parts.append(f"    // App: {title}")
    parts.append("")

    for node in graph.nodes:
        conds = node.get_dimension(Dimension.CONDITIONAL)
        if not conds:
            continue
        var_name = _c_var_name(node.path)
        for c in conds:
            if isinstance(c, dict):
                action = c.get("action", "activate")
                cond = c.get("condition", "")
                subject = c.get("subject", node.name)
                parts.append(f"    // {subject} {action} on {cond}")
                parts.append(f"    if ({var_name}.{subject}_active) {{")
                parts.append(f"        /* PROXY: conditional logic requires external signal input */")
                parts.append(f"        /* OUT_OF_SCOPE: {cond} — hardware interrupt not modeled */")
                parts.append(f"    }}")
                parts.append("")

    # Cognitive state machine
    parts.append("    // State machine from cognitive dimensions")
    for node in graph.nodes:
        cog = node.get_dimension(Dimension.COGNITIVE)
        if not cog:
            continue
        var_name = _c_var_name(node.path)
        for c in cog:
            if isinstance(c, dict):
                pred = c.get("predicate", "state")
                val = c.get("value", "")
                parts.append(f"    // {node.path}: {pred} = {val}")
                parts.append(f"    {var_name}.{pred}_active = true;")

    # Behavioral lifecycle
    behs = []
    for node in graph.nodes:
        behs.extend(node.get_dimension(Dimension.BEHAVIORAL))
    lifecycle_behs = [b for b in behs if isinstance(b, dict) and b.get("kind") == "lifecycle" and b.get("lifecycle")]
    if lifecycle_behs:
        parts.append("")
        parts.append("    // Behavioral lifecycle states")
        for b in lifecycle_behs:
            subject = b.get("subject", "entity")
            lifecycle = b.get("lifecycle", [])
            parts.append(f"    // {subject} lifecycle:")
            for t in lifecycle:
                parts.append(f"    //   {t.get('from_state', '')} -> {t.get('to_state', '')}")

    parts.append("")
    parts.append("    while (1) {")
    parts.append("        /* Polling loop — PROXY: real embedded uses interrupts */")
    parts.append("        /* BRIDGE: vibe/behavioral dimensions not directly mappable to C */")
    parts.append("    }")
    parts.append("    return 0;")
    parts.append("}")
    parts.append("")

    # Degradation tolerance markers
    for node in graph.nodes:
        for key, entry in node.degradation_tolerance.items():
            if entry.level == ToleranceLevel.PROXY:
                parts.append(f"// PROXY (tolerated): {node.path}.{key} — degraded in C target")

    return {f"{base}/main.c": "\n".join(parts) + "\n"}


def _c_struct_name(path: str) -> str:
    return _pascal_case(path) + "State"


def _c_var_name(path: str) -> str:
    return _camel_case(path) + "_state"


def _pascal_case(path: str) -> str:
    """Convert a dotted path to PascalCase.

    'sensor_hub.dashboard.sensor_panel' -> 'SensorHubDashboardSensorPanel'
    """
    words = re.findall(r"[a-zA-Z0-9]+", path)
    return "".join(w[0].upper() + w[1:] for w in words) or "App"


def _camel_case(path: str) -> str:
    parts = [p for p in path.replace("_", " ").split(".") if p]
    if not parts:
        return "app"
    if len(parts) == 1:
        return parts[0].lower()
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


# ---------------------------------------------------------------------------
# LaTeX target — document generation / typesetting
# ---------------------------------------------------------------------------


def _gen_latex(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    """Generate LaTeX document from the SIR graph."""
    base = target.name
    parts: List[str] = []
    parts.append("% Orren-generated LaTeX")
    parts.append(f"% Target: {target.name} ({target.language})")
    parts.append(f"% Application: {_graph_title(graph)}")
    parts.append("")
    parts.append("\\documentclass[11pt]{article}")
    parts.append("\\usepackage[utf8]{inputenc}")
    parts.append("\\usepackage{geometry}")
    parts.append("\\usepackage{xcolor}")
    parts.append("\\usepackage{longtable}")
    parts.append("\\usepackage{enumitem}")
    parts.append("\\geometry{a4paper, margin=1in}")
    parts.append("")

    # Document metadata from context
    expr = graph.expressions[0] if graph.expressions else None
    if expr:
        for stmt in expr.context:
            if stmt.key == "purpose":
                parts.append(f"\\title{{{_escape_latex(stmt.value)} }}")
            elif stmt.key == "audience":
                parts.append(f"\\author{{{_escape_latex(stmt.value)} }}")
        parts.append("\\date{\\today}")
    else:
        parts.append("\\title{Orren-generated Document}")
        parts.append("\\author{Orren Language Engine}")

    parts.append("")
    parts.append("\\begin{document}")
    parts.append("\\maketitle")
    parts.append("")

    # Table of contents from structure
    parts.append("\\section{Structure}")
    parts.append("\\begin{itemize}")
    for node in graph.nodes:
        if node.kind == "root":
            continue
        if node.has_dimension_content(Dimension.SPATIAL) or node.has_dimension_content(Dimension.VIBE):
            parts.append(f"\\item \\textbf{{{_escape_latex(node.path)}}}")
            vibes = node.get_dimension(Dimension.VIBE)
            for v in vibes:
                if isinstance(v, dict):
                    aspect = v.get("aspect", "")
                    term = v.get("term", "")
                    parts.append(f"  \\subitem Vibe: {aspect}={term}")
            conds = node.get_dimension(Dimension.CONDITIONAL)
            for c in conds:
                if isinstance(c, dict):
                    parts.append(f"  \\subitem Conditional: {c.get('subject','')} {c.get('action','')} on {c.get('condition','')}")
    parts.append("\\end{itemize}")
    parts.append("")

    # Cognitive content as a table
    parts.append("\\section{Cognitive Model}")
    parts.append("\\begin{longtable}{|l|l|l|}")
    parts.append("\\hline")
    parts.append("Entity & Predicate & Value \\\\")
    parts.append("\\hline")
    parts.append("\\endfirsthead")
    for node in graph.nodes:
        cog = node.get_dimension(Dimension.COGNITIVE)
        for c in cog:
            if isinstance(c, dict):
                parts.append(f"{_escape_latex(node.path)} & {_escape_latex(c.get('predicate',''))} & {_escape_latex(c.get('value',''))} \\\\")
                parts.append("\\hline")
    parts.append("\\end{longtable}")
    parts.append("")

    # Equilibrium rules
    eq_rules = getattr(graph, 'equilibrium_rules', [])
    if eq_rules:
        parts.append("\\section{Equilibrium Rules}")
        parts.append("\\begin{enumerate}")
        for rule in eq_rules:
            parts.append(f"\\item \\textbf{{{_escape_latex(rule.name)}}}: preserve {', '.join(_escape_latex(p) for p in rule.preserve)}")
        parts.append("\\end{enumerate}")
        parts.append("")

    # Vibe aesthetic notes
    parts.append("\\section{Aesthetic Specifications}")
    for node in graph.nodes:
        vibes = node.get_dimension(Dimension.VIBE)
        if not vibes:
            continue
        parts.append(f"\\subsection*{{{_escape_latex(node.path)}}}")
        parts.append("\\begin{itemize}")
        for v in vibes:
            if isinstance(v, dict):
                parts.append(f"\\item \\textbf{{{_escape_latex(v.get('aspect',''))}}}: {v.get('term','')}")
        parts.append("\\end{itemize}")
    parts.append("")

    # Degradation report
    parts.append("\\section{Degradation Report}")
    parts.append("\\begin{itemize}")
    for node in graph.nodes:
        for key, entry in node.degradation_tolerance.items():
            parts.append(f"\\item {node.path}.{key}: {entry.level.value} ({entry.mode})")
    parts.append("\\end{itemize}")
    parts.append("")

    # Preservation status — use the target's own score (coordination already done)
    parts.append("\\section{Preservation Scores}")
    parts.append("\\begin{itemize}")
    parts.append(f"\\item \\textbf{{{_escape_latex(target.name)}}}: {target.preservation_score:.2f}")
    parts.append("\\end{itemize}")
    parts.append("")

    parts.append("\\end{document}")

    return {f"{base}/document.tex": "\n".join(parts) + "\n"}


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    if not text:
        return ""
    for char, repl in [("&", r"\&"), ("%", r"\%"), ("$", r"\$"), ("#", r"\#"),
                        ("_", r"\_"), ("{", r"\{"), ("}", r"\}"),
                        ("~", r"\textasciitilde{}"), ("^", r"\textasciicircum{}")]:
        text = text.replace(char, repl)
    return text


# ---------------------------------------------------------------------------
# Rust target — systems / performance programming
# ---------------------------------------------------------------------------


def _gen_rust(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    """Generate Rust code for systems/performance targets."""
    base = target.name
    title = _graph_title(graph)
    parts: List[str] = []
    parts.append("// Orren-generated Rust")
    parts.append(f"// Target: {target.name} ({target.language})")
    parts.append(f"// Application: {title}")
    parts.append("")
    parts.append("use std::collections::HashMap;")
    parts.append("")

    # Emit structs for entity nodes with cognitive dimensions
    parts.append("// --- Entity Structs ---")
    for node in graph.nodes:
        if node.kind == "root":
            continue
        cog = node.get_dimension(Dimension.COGNITIVE)
        if not cog:
            continue
        struct_name = _rust_struct_name(node.path)
        parts.append(f"#[derive(Debug, Clone, Default)]")
        parts.append(f"pub struct {struct_name} {{")
        for c in cog:
            if isinstance(c, dict):
                pred = c.get("predicate", "state")
                parts.append(f"    pub {pred}: bool,")
        parts.append("}")
        parts.append("")

    # Emit a state machine enum
    parts.append("// --- State Machine ---")
    for node in graph.nodes:
        behs = node.get_dimension(Dimension.BEHAVIORAL)
        lifecycle_behs = [b for b in behs if isinstance(b, dict) and b.get("kind") == "lifecycle" and b.get("lifecycle")]
        if not lifecycle_behs:
            continue
        for b in lifecycle_behs:
            subject = b.get("subject", node.name)
            lifecycle = b.get("lifecycle", [])
            parts.append(f"#[derive(Debug, Clone, PartialEq)]")
            parts.append(f"pub enum {subject.capitalize()}State {{")
            states = set()
            for t in lifecycle:
                states.add(t.get("from_state", ""))
                states.add(t.get("to_state", ""))
            for s in sorted(states):
                parts.append(f"    {s.capitalize()},")
            parts.append("}")
            parts.append("")

    # Main processing function
    parts.append("// --- Processing Function ---")
    parts.append(f"pub fn process(title: &str) -> HashMap<String, String> {{")
    parts.append(f"    let mut results = HashMap::new();")
    parts.append(f"    results.insert(\"application\".to_string(), \"{title}\".to_string());")
    parts.append("    results.insert(\"input_title\".to_string(), title.to_string());")
    parts.append("")

    # Vibe → performance parameters (PROXY markers where vibe can't be expressed)
    parts.append("    // Vibe mapping (performance parameters)")
    for node in graph.nodes:
        vibes = node.get_dimension(Dimension.VIBE)
        if not vibes:
            continue
        var = _rust_var_name(node.path)
        for v in vibes:
            if isinstance(v, dict):
                aspect = v.get("aspect", "")
                term = v.get("term", "")
                if aspect == "tone":
                    if "calm" in term:
                        parts.append(f"    // PROXY: vibe.tone={term} → latency=high, throughput=medium")
                        parts.append(f"    let {var}_latency_ms: u64 = 200;")
                        parts.append(f"    results.insert(\"{node.path}.latency_ms\".to_string(), {var}_latency_ms.to_string());")
                    elif "intense" in term:
                        parts.append(f"    // vibe.tone={term} → latency=low, throughput=high")
                        parts.append(f"    let {var}_latency_ms: u64 = 10;")
                        parts.append(f"    results.insert(\"{node.path}.latency_ms\".to_string(), {var}_latency_ms.to_string());")
                    else:
                        parts.append(f"    // PROXY: vibe.tone={term} has no Rust equivalent")
                        parts.append(f"    let {var}_latency_ms: u64 = 50;")
                        parts.append(f"    results.insert(\"{node.path}.latency_ms\".to_string(), {var}_latency_ms.to_string());")
                else:
                    parts.append(f"    // PROXY: vibe.{aspect}={term} — not directly mappable in Rust")

    # Cognitive processing
    parts.append("")
    parts.append("    // Cognitive processing (type-safe)")
    for node in graph.nodes:
        cog = node.get_dimension(Dimension.COGNITIVE)
        for c in cog:
            if isinstance(c, dict):
                subject = c.get("subject", "")
                pred = c.get("predicate", "")
                val = c.get("value", "")
                parts.append(f"    // {node.path}: {subject} {pred} = {val}")
                parts.append(f"    results.insert(\"{node.path}.{pred}\".to_string(), \"{val}\".to_string());")

    # Degradation tolerance
    parts.append("")
    parts.append("    // Degradation acknowledgment")
    for node in graph.nodes:
        for key, entry in node.degradation_tolerance.items():
            if entry.level in (ToleranceLevel.PROXY, ToleranceLevel.DOCUMENTED):
                parts.append(f"    // DEGRADED: {node.path}.{key} = {entry.level.value}")

    parts.append("    results")
    parts.append("}")
    parts.append("")
    parts.append("fn main() {")
    parts.append(f"    let results = process(\"{title}\");")
    parts.append("    let mut entries: Vec<_> = results.iter().collect();")
    parts.append("    entries.sort_by(|(left, _), (right, _)| left.cmp(right));")
    parts.append("    for (key, value) in entries {")
    parts.append("        println!(\"{}={}\", key, value);")
    parts.append("    }")
    parts.append("}")
    parts.append("")

    return {f"{base}/main.rs": "\n".join(parts) + "\n"}


def _rust_struct_name(path: str) -> str:
    return _pascal_case(path)


def _rust_var_name(path: str) -> str:
    return _snake_case(path)


def _snake_case(text: str) -> str:
    return text.replace(".", "_").replace("-", "_").replace(" ", "_").lower()


# ---------------------------------------------------------------------------
# Go target — backend microservices
# ---------------------------------------------------------------------------


def _gen_go(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    """Generate Go code for backend microservice targets."""
    base = target.name
    title = _graph_title(graph)
    parts: List[str] = []
    parts.append("// Orren-generated Go (microservice)")
    parts.append(f"// Target: {target.name} ({target.language})")
    parts.append(f"// Application: {title}")
    parts.append("")
    parts.append("package main")
    parts.append("")
    parts.append("import (")
    parts.append('\t"fmt"')
    parts.append('\t"net/http"')
    parts.append('\t"context"')
    parts.append('\t"encoding/json"')
    parts.append(")")
    parts.append("")

    # Entity structs from cognitive dimensions
    parts.append("// --- Entity Models ---")
    for node in graph.nodes:
        if node.kind == "root":
            continue
        cog = node.get_dimension(Dimension.COGNITIVE)
        if not cog:
            continue
        struct_name = _go_struct_name(node.path)
        parts.append(f"type {struct_name} struct {{")
        for c in cog:
            if isinstance(c, dict):
                pred = c.get("predicate", "Value")
                go_field = _go_field_name(pred)
                parts.append(f'\t{go_field} string `json:"{pred}"`')
        parts.append("}")
        parts.append("")

    # HTTP handler
    parts.append("// --- HTTP Handler ---")
    parts.append(f"func handle{title.replace(' ','').replace('_','')}(")
    parts.append("    w http.ResponseWriter,")
    parts.append("    r *http.Request,")
    parts.append(") {")
    parts.append('\tw.Header().Set("Content-Type", "application/json")')
    parts.append("")

    # Cognitive processing in handler
    parts.append("\t// Cognitive dimensions → business logic")
    for node in graph.nodes:
        cog = node.get_dimension(Dimension.COGNITIVE)
        for c in cog:
            if isinstance(c, dict):
                pred = c.get("predicate", "")
                val = c.get("value", "")
                parts.append(f'\t// {node.path}: {pred} = {val}')

    parts.append("")
    parts.append("\t// Conditional activation (from conditional dimension)")
    for node in graph.nodes:
        conds = node.get_dimension(Dimension.CONDITIONAL)
        for c in conds:
            if isinstance(c, dict):
                cond = c.get("condition", "")
                action = c.get("action", "activate")
                parts.append(f'\t// {c.get("subject","")} {action} on {cond}')
                parts.append(f'\t_ = r.URL.Query().Get("{c.get('subject','signal')}")')

    # Relational data flow
    parts.append("")
    parts.append("\t// Relational data flow")
    for node in graph.nodes:
        rels = node.get_dimension(Dimension.RELATIONAL)
        for r in rels:
            if isinstance(r, dict):
                parts.append(f'\t// {r.get("source","")} {r.get("relation","flows")} {r.get("target","")}')

    parts.append("\t")
    parts.append("\tresp := map[string]interface{}{")
    parts.append(f'\t\t"status": "ok",')
    entity_count = sum(1 for n in graph.nodes if n.kind != "root")
    parts.append(f'\t\t"application": "{title}",')
    parts.append(f'\t\t"entities": {entity_count},')
    parts.append("\t}")
    parts.append("\tw.WriteHeader(http.StatusOK)")
    parts.append("\tjson.NewEncoder(w).Encode(resp)")
    parts.append("}")
    parts.append("")

    # Main function
    parts.append("func main() {")
    parts.append(f'\taddr := ":8080"')
    parts.append('\thttp.HandleFunc("/api/process", handle' + title.replace(' ','').replace('_','') + ')')
    parts.append('\tfmt.Printf("Listening on %s\\n", addr)')
    parts.append('\thttp.ListenAndServe(addr, nil)')
    parts.append("}")
    parts.append("")

    # Degradation tolerance
    for node in graph.nodes:
        for key, entry in node.degradation_tolerance.items():
            if entry.level == ToleranceLevel.PROXY:
                parts.append(f"// PROXY (tolerated): {node.path}.{key} — degraded in Go target")

    return {f"{base}/main.go": "\n".join(parts) + "\n"}


def _go_struct_name(path: str) -> str:
    return _pascal_case(path)


def _go_field_name(pred: str) -> str:
    return "".join(p.capitalize() for p in pred.replace("_", " ").split()) or "Value"


# ---------------------------------------------------------------------------
# General Python service target — Python
# ---------------------------------------------------------------------------


def _gen_python_service(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    """Generate a Python service class for generic backend targets.

    Used when the target language is Python but the name doesn't match
    a specialized generator (transcription, audio_storage, input_watcher).
    """
    base = target.name
    title = _graph_title(graph)
    parts: List[str] = []
    parts.append(f'"""Orren-generated Python service: {target.name}.')
    parts.append(f'')
    parts.append(f'Target: {target.name} ({target.language})')
    parts.append(f'Application: {title}')
    parts.append(f'Capabilities: {target.capabilities}')
    parts.append(f'"""')
    parts.append(f'')
    parts.append(f'from __future__ import annotations')
    parts.append(f'from dataclasses import dataclass, field')
    parts.append(f'from typing import Any')
    parts.append(f'')
    parts.append(f'')
    parts.append(f'class {title.replace(" ", "").replace("_", "").capitalize()}Service:')
    parts.append(f'    """Service generated from {title} realization target: {target.name}.')
    parts.append(f'')
    parts.append(f'    Capabilities: {target.capabilities}')
    parts.append(f'    Cannot express: {target.cannot_express}')
    parts.append(f'    """')
    parts.append(f'')
    parts.append(f'    def __init__(self) -> None:')
    parts.append(f'        self._state: dict[str, Any] = {{')

    # Emit cognitive state from graph
    for node in graph.nodes:
        cog = node.get_dimension(Dimension.COGNITIVE)
        for c in cog:
            if isinstance(c, dict):
                pred = c.get("predicate", "")
                val = c.get("value", "")
                parts.append(f'            "{node.path}.{pred}": "{val}",')

    parts.append(f'        }}')
    parts.append(f'')
    parts.append(f'')

    # Emit process method using cognitive + relational dimensions
    parts.append(f'    def process(self, context: dict[str, Any] | None = None) -> dict[str, Any]:')
    parts.append(f'        """Process a request through the cognitive pipeline."""')
    parts.append(f'        ctx = context or {{}}')
    parts.append(f'')

    for node in graph.nodes:
        cog = node.get_dimension(Dimension.COGNITIVE)
        for c in cog:
            if isinstance(c, dict):
                subject = c.get("subject", "")
                pred = c.get("predicate", "")
                val = c.get("value", "")
                parts.append(f'        # {node.path}: {subject}.{pred} = {val}')
                parts.append(f'        self._state["{node.path}.{pred}"] = "{val}"')

    parts.append(f'')
    parts.append(f'        # Relational data flow')
    for node in graph.nodes:
        rels = node.get_dimension(Dimension.RELATIONAL)
        for r in rels:
            if isinstance(r, dict):
                parts.append(f'        # {r.get("source","")} {r.get("relation","flows")} {r.get("target","")}')

    parts.append(f'        # Conditional activation')
    for node in graph.nodes:
        conds = node.get_dimension(Dimension.CONDITIONAL)
        for c in conds:
            if isinstance(c, dict):
                parts.append(f'        # {c.get("subject","")} {c.get("action","")} on {c.get("condition","")}')

    parts.append(f'')
    parts.append(f'        return self._state')
    parts.append(f'')
    parts.append(f'')
    parts.append(f'if __name__ == "__main__":')
    parts.append(f'    svc = {title.replace(" ", "").replace("_", "").capitalize()}Service()')
    parts.append(f'    result = svc.process()')
    parts.append(f'    print(f"Processed: {{len(result)}} state entries")')
    parts.append(f'')

    return {f"{base}/service.py": "\n".join(parts) + "\n"}


# ---------------------------------------------------------------------------
# Fallback manifest
# ---------------------------------------------------------------------------


def _gen_manifest(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    base = target.name
    parts: List[str] = []
    parts.append('"""Orren manifest — no code generator available for this target."""')
    parts.append(f' Target: {target.name}')
    parts.append(f' Language: {target.language}')
    parts.append(f' Capabilities: {target.capabilities}')
    parts.append(f' Preservation score: {target.preservation_score}')
    return {f"{base}/MANIFEST.txt": "\n".join(parts) + "\n"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_COLOR_MAP = {
    "emerald": "#2ecc71",
    "blue": "#3498db",
    "red": "#e74c3c",
    "green": "#27ae60",
    "calm": "#7f8c8d",
    "organic": "#27ae60",
}


def _map_color(term: str) -> str:
    term_lower = term.lower()
    for key, val in _COLOR_MAP.items():
        if key in term_lower:
            return val
    return "#888888"


def _css_id(path: str) -> str:
    return path.replace(".", "-").replace("_", "-")


def _js_identifier(path: str) -> str:
    """Convert a semantic path into a valid JavaScript identifier fragment."""
    value = path.replace(".", "_").replace("-", "_")
    value = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value)
    return value or "node"


def _swift_class_name(title: str) -> str:
    parts = re.split(r"[^A-Za-z0-9]+", title)
    return "".join(p.capitalize() for p in parts if p) or "GeneratedApp"


def _kotlin_class_name(title: str) -> str:
    name = _swift_class_name(title)
    return name[0].lower() + name[1:] if name else "generatedApp"


def _swift_var(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "_", name)


def _swift_color(hex_color: str) -> str:
    # Convert "#2ecc71" → UIColor literal
    h = hex_color.lstrip("#")
    if len(h) == 6:
        r = int(h[0:2], 16) / 255.0
        g = int(h[2:4], 16) / 255.0
        b = int(h[4:6], 16) / 255.0
        return f"UIColor(red: {r:.3f}, green: {g:.3f}, blue: {b:.3f}, alpha: 1.0)"
    return "UIColor.gray"


def _escape(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;").replace("&", "&amp;")


def _graph_title(graph: SIRGraph) -> str:
    if graph.root is not None:
        return graph.root.name
    return "OrrenApp"


__all__ = ["generate"]
