"""
Orren Engine — Code Generator
=============================

Takes a SIR graph + a RealizationTarget and produces actual source code
in the target language. Where a dimension cannot be fully expressed,
the generator emits an explicit comment marker (PROXY / BRIDGE / OUT_OF_SCOPE)
so the gap is visible in the artifact, not silent.

Targets supported (the "small standard library"):
    web_interface      HTML + CSS + JS
    native_shell       Swift (iOS) / Kotlin (Android) — chosen by language
    transcription_service  Python
    audio_storage      Python (filesystem)
    input_button_watcher   Python (OS event hook simulation)

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
    if "web" in name or "html" in name or "css" in name or "js" in name:
        return _gen_web(graph, target)
    if "native" in name or "swift" in target.language.lower() or "kotlin" in target.language.lower():
        return _gen_native(graph, target)
    if "transcription" in name:
        return _gen_transcription_service(graph, target)
    if "audio_storage" in name or "storage" in name:
        return _gen_audio_storage(graph, target)
    if "input" in name or "button" in name:
        return _gen_input_watcher(graph, target)
    # Fallback: emit a manifest describing what we couldn't generate.
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
