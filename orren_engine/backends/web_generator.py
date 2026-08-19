"""Premium HTML5 / CSS3 / ES2022 code generator for the web backend.

This module replaces the scaffold-emitting ``_gen_web`` in ``codegen.py``
with a production-grade generator that preserves semantic, vibe, behavioral,
conditional, and temporal dimensions through real, executable HTML, CSS, and
JavaScript.

Gate compliance:
  - Structural  -- semantic elements, data-semantic-id, ARIA roles
  - Syntactic   -- valid HTML5 / CSS3 / ES2022 (parser-checked)
  - Linkable    -- self-contained HTML/CSS/JS (no external deps)
  - Executable  -- browser-runnable ES2022 modules with real logic
  - Behavioral  -- state machine, event handlers, guarded transitions
  - Operational -- error boundary, resource limits, config, persistence
  - Preservation -- PROXY/BRIDGE/DEGRADED markers for every gap

File: orren_engine/backends/web_generator.py
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
import re

from ..data_model import (
    Dimension,
    RealizationTarget,
    SIRGraph,
    SIRNode,
)
from .web_tokens import (
    VibeTokenMap,
    extract_all_tokens,
    extract_locale,
    extract_vibe_tokens,
    _node_id,
)
from .web_gl import (
    LIVING_CANVAS_HTML,
    generate_living_js,
)
from .web_behavior import (
    StateMachine,
    _collect_state_machines,
    _extract_relational_links,
    _extract_temporal_sequences,
    generate_event_handlers,
    generate_state_machine_js,
    _js_safe_id,
)

# ---------------------------------------------------------------------------
# HTML element mapping from SIR node kind
# ---------------------------------------------------------------------------

_HTML_ELEMENT_MAP: Dict[str, str] = {
    "root": "main",
    "entity": "article",
    "component": "section",
    "interface": "nav",
    "service": "aside",
    "action": "button",
    "state": "section",
    "process": "section",
    "attribute": "span",
    "reference": "a",
    "group": "section",
    "flow": "section",
    "control": "form",
    "boundary": "header",
    "gateway": "footer",
}


def _semantic_element(node: SIRNode) -> str:
    """Choose a semantic HTML element for a SIR node based on kind + content."""
    cog = node.get_dimension(Dimension.COGNITIVE)
    for c in cog:
        if isinstance(c, dict):
            pred = c.get("predicate", "")
            if pred in ("activation", "actuation", "trigger", "capture", "control"):
                return "button"
            if pred in ("retention", "storage", "preservation"):
                return "section"
            if pred in ("monitoring", "reading", "transcription", "verification"):
                return "article"
    el = _HTML_ELEMENT_MAP.get(node.kind, "div")
    return el


# ---------------------------------------------------------------------------
# ARIA role mapping from cognitive dimension
# ---------------------------------------------------------------------------

_ARIA_ROLE_MAP: Dict[str, str] = {
    "monitoring": "status",
    "scheduling": "timer",
    "reading": "status",
    "actuation": "button",
    "triaging": "listbox",
    "detection": "alert",
    "verification": "status",
    "retention": "region",
    "storage": "region",
    "logging": "log",
    "notification": "alert",
    "navigation": "navigation",
    "presentation": "main",
    "processing": "progressbar",
    "capture": "button",
    "transcription": "status",
    "preservation": "region",
}


def _aria_label(node: SIRNode) -> str:
    """Derive an accessible ARIA label from the node's expression/cognitive dims."""
    exprs = node.get_dimension(Dimension.EXPRESSION)
    for e in exprs:
        if isinstance(e, dict):
            for key in ("purpose", "label", "aria-label", "title"):
                if key in e and isinstance(e[key], str) and e[key].strip():
                    return e[key]
    return node.name if node.name else node.path


def _aria_role(node: SIRNode) -> str:
    """Derive an ARIA role from the node's cognitive predicates."""
    cog = node.get_dimension(Dimension.COGNITIVE)
    for c in cog:
        if isinstance(c, dict):
            pred = c.get("predicate", "")
            if pred in _ARIA_ROLE_MAP:
                return _ARIA_ROLE_MAP[pred]
    kind_role = {
        "entity": "region",
        "component": "region",
        "interface": "navigation",
        "action": "button",
        "state": "status",
        "process": "region",
        "service": "region",
        "control": "form",
        "boundary": "banner",
        "gateway": "contentinfo",
    }
    return kind_role.get(node.kind, "region")


def _spatial_depth(node: SIRNode) -> int:
    """Count spatial nesting depth from node path."""
    return node.path.count(".")


def _spatial_to_grid(node: SIRNode) -> str:
    """Map spatial dimension to CSS grid area or flex layout hint."""
    spatial = node.get_dimension(Dimension.SPATIAL)
    if not spatial:
        return ""
    first = spatial[0]
    if isinstance(first, dict):
        loc = first.get("location", "") or first.get("relative_to", "")
        return str(loc)
    return ""


def _node_label(node: SIRNode) -> str:
    """Derive a human-readable label for the HTML text content."""
    exprs = node.get_dimension(Dimension.EXPRESSION)
    for e in exprs:
        if isinstance(e, dict):
            for key in ("label", "title", "name"):
                if key in e and isinstance(e[key], str) and e[key].strip():
                    return e[key]
    return node.name or node.path


def _graph_purpose(graph: SIRGraph) -> str:
    """Extract the purpose string from the root node's expression dimension."""
    if graph.root is None:
        return ""
    exprs = graph.root.get_dimension(Dimension.EXPRESSION)
    for e in exprs:
        if isinstance(e, dict):
            purpose = e.get("purpose", "")
            if isinstance(purpose, str) and purpose.strip():
                return purpose
    return ""


# ---------------------------------------------------------------------------
# CSS generation
# ---------------------------------------------------------------------------

_DEFAULT_TOKENS: Dict[str, str] = {
    "--color-bg": "#0f172a",
    "--color-surface": "#1e293b",
    "--color-fg": "#e2e8f0",
    "--color-border": "#334155",
    "--font-family-sans": "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif",
    "--font-family-mono": "'Fira Code', 'Cascadia Code', Menlo, Consolas, monospace",
    "--font-size-base": "1rem",
    "--font-weight-body": "400",
    "--font-weight-display": "700",
    "--spacing-unit": "1rem",
    "--radius-standard": "0.5rem",
    "--motion-duration": "0.2s ease",
    "--motion-easing": "ease",
    "--shadow-elevation": "0 1px 3px rgba(0, 0, 0, 0.1)",
    "--shadow-elevation-hover": "0 4px 6px rgba(0, 0, 0, 0.15)",
}


def _generate_css_variables(graph: SIRGraph, target: RealizationTarget) -> Tuple[List[str], List[str]]:
    """Generate the :root { --token: value; } block.

    Returns a tuple of (variable_lines, proxy_marker_lines).
    """
    lines: List[str] = []
    proxy_markers: List[str] = []

    # Root-level design tokens from the root node's vibe.
    root_vibe = VibeTokenMap()
    if graph.root is not None:
        root_vibe = extract_vibe_tokens(graph, graph.root)

    for css_name, css_val in root_vibe.css_variables.items():
        lines.append(f"  {css_name}: {css_val};")

    # Global defaults for tokens not provided by a node.
    for name, val in _DEFAULT_TOKENS.items():
        if name not in root_vibe.css_variables:
            lines.append(f"  {name}: {val};")

    # Collect proxy markers from all nodes.
    all_tokens = extract_all_tokens(graph)
    for node_path, token_map in sorted(all_tokens.items()):
        for proxy in token_map.proxy:
            proxy_markers.append(proxy)

    # Collect proxy markers from target-level cannot_express.
    for dep in target.cannot_express:
        proxy_markers.append(
            f"/* PROXY: target cannot fully express '{dep}'; "
            f"semantic meaning approximated. */"
        )

    return lines, proxy_markers


def generate_css(graph: SIRGraph, target: RealizationTarget) -> str:
    """Generate a complete, production-grade CSS3 stylesheet.

    Features:
      - CSS custom properties mapped from vibe dimensions.
      - Responsive breakpoints.
      - Dark / light theme media query.
      - Reduced-motion media query.
      - Per-node vibe tokens applied via ID selectors.
    """
    lines: List[str] = []
    lines.append("/* === Orren-generated premium stylesheet ===")
    lines.append(f" * Target: {target.name} ({target.language})")
    lines.append(f" * Preservation score: {target.preservation_score}")
    lines.append(" * ===")
    lines.append(" */")
    lines.append("")

    # :root custom properties.
    var_lines, proxy_markers = _generate_css_variables(graph, target)
    lines.append(":root {")
    lines.extend(var_lines)
    lines.append("}")
    lines.append("")

    # Reduced motion.
    lines.append("@media (prefers-reduced-motion: reduce) {")
    lines.append("  :root { --motion-duration: 0s; }")
    lines.append("}")
    lines.append("")

    # Dark / light theme.
    lines.append("@media (prefers-color-scheme: light) {")
    lines.append("  :root {")
    lines.append("    --color-bg: #faf8f1;")
    lines.append("    --color-surface: #ffffff;")
    lines.append("    --color-fg: #1a1a1a;")
    lines.append("    --color-border: #e0e0e0;")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    # Responsive breakpoints.
    lines.append("@media (max-width: 768px) {")
    lines.append("  :root { --spacing-unit: 0.75rem; }")
    lines.append("  .orren-container { max-width: 100%; }")
    lines.append("}")
    lines.append("")
    lines.append("@media (max-width: 480px) {")
    lines.append("  :root { --font-size-base: 0.875rem; }")
    lines.append("  .orren-grid { grid-template-columns: 1fr; }")
    lines.append("}")
    lines.append("")

    # Base styles.
    lines.append("/* === Base styles (from vibe dimensions) === */")
    lines.append("* { box-sizing: border-box; }")
    lines.append("html { font-size: var(--font-size-base, 1rem); }")
    lines.append("body {")
    lines.append("  margin: 0;")
    lines.append("  font-family: var(--font-family-sans);")
    lines.append("  background-color: var(--color-bg);")
    lines.append("  color: var(--color-fg);")
    lines.append("  transition: background-color var(--motion-duration, 0.2s ease),")
    lines.append("              color var(--motion-duration, 0.2s ease);")
    lines.append("  padding: var(--spacing-unit, 1rem);")
    lines.append("}")
    lines.append("")
    lines.append(".orren-container {")
    lines.append("  max-width: 1200px;")
    lines.append("  margin: 0 auto;")
    lines.append("  display: grid;")
    lines.append("  gap: var(--spacing-unit, 1rem);")
    lines.append("}")
    lines.append("")
    lines.append(".orren-error-boundary {")
    lines.append("  border: 1px solid var(--color-border, #334155);")
    lines.append("  border-radius: var(--radius-standard, 0.5rem);")
    lines.append("  background-color: var(--color-surface, #1e293b);")
    lines.append("  padding: calc(var(--spacing-unit, 1rem) * 0.75);")
    lines.append("  margin-bottom: var(--spacing-unit, 1rem);")
    lines.append("}")
    lines.append("")

    # Keyboard accessibility: always-visible focus indicator (WCAG 2.4.7).
    lines.append(":focus-visible {")
    lines.append("  outline: 3px solid var(--color-accent, #3b82f6);")
    lines.append("  outline-offset: 2px;")
    lines.append("}")
    lines.append("")

    # Comfortable touch targets on coarse pointers (WCAG 2.5.8).
    lines.append("@media (pointer: coarse) {")
    lines.append("  button, a.orren-entity, .orren-theme-toggle {")
    lines.append("    min-height: 44px;")
    lines.append("    min-width: 44px;")
    lines.append("  }")
    lines.append("}")
    lines.append("")

    # Explicit theme classes — user preference overrides the OS default.
    lines.append("html.theme-dark {")
    lines.append("  --color-bg: #0f172a;")
    lines.append("  --color-surface: #1e293b;")
    lines.append("  --color-fg: #e2e8f0;")
    lines.append("  --color-border: #334155;")
    lines.append("  color-scheme: dark;")
    lines.append("}")
    lines.append("")
    lines.append("html.theme-light {")
    lines.append("  --color-bg: #faf8f1;")
    lines.append("  --color-surface: #ffffff;")
    lines.append("  --color-fg: #1a1a1a;")
    lines.append("  --color-border: #e0e0e0;")
    lines.append("  color-scheme: light;")
    lines.append("}")
    lines.append("")

    # Card / entity styles.
    lines.append(".orren-entity {")
    lines.append("  background-color: var(--color-surface, #1e293b);")
    lines.append("  border: 1px solid var(--color-border, #334155);")
    lines.append("  border-radius: var(--border-radius, var(--radius-standard, 0.5rem));")
    lines.append("  padding: calc(var(--spacing-unit, 1rem) * 1.5);")
    lines.append("  transition: transform var(--motion-duration, 0.2s ease),")
    lines.append("              box-shadow var(--motion-duration, 0.2s ease);")
    lines.append("}")
    lines.append(".orren-entity:hover {")
    lines.append("  box-shadow: var(--shadow-elevation-hover, 0 4px 6px rgba(0, 0, 0, 0.15));")
    lines.append("}")
    lines.append("")

    # Typography from vibe.
    lines.append("h1, h2, h3, h4, h5, h6 {")
    lines.append("  font-weight: var(--font-weight-display, 700);")
    lines.append("  letter-spacing: var(--letter-spacing, 0);")
    lines.append("  line-height: 1.2;")
    lines.append("}")
    lines.append("")
    lines.append("code, .orren-mono {")
    lines.append("  font-family: var(--font-family-mono, 'Fira Code', monospace);")
    lines.append("  font-weight: var(--font-weight-mono, 400);")
    lines.append("}")
    lines.append("")

    # Activation signal glow (box-shadow from steady_glow vibe).
    lines.append("/* === Activation signal styles (from vibe.activation_signal) === */")
    lines.append(".orren-activation {")
    lines.append("  animation: orren-pulse var(--motion-duration, 0.5s) infinite alternate;")
    lines.append("}")
    lines.append("@keyframes orren-pulse {")
    lines.append("  from { box-shadow: 0 0 var(--glow-intensity, 0) var(--glow-color, transparent); }")
    lines.append("  to { box-shadow: 0 0 16px var(--glow-color, #2ecc71); }")
    lines.append("}")
    lines.append("")

    # Status badges.
    lines.append(".orren-status {")
    lines.append("  display: inline-block;")
    lines.append("  padding: 0.125rem 0.5rem;")
    lines.append("  border-radius: var(--border-radius, 9999px);")
    lines.append("  font-size: 0.75rem;")
    lines.append("  font-weight: var(--font-weight-body, 400);")
    lines.append("  background-color: var(--color-accent, #3b82f6);")
    lines.append("  color: #ffffff;")
    lines.append("}")
    lines.append("")

    # Theme toggle control.
    lines.append(".orren-theme-toggle {")
    lines.append("  border: 1px solid var(--color-border, #334155);")
    lines.append("  border-radius: var(--radius-standard, 0.5rem);")
    lines.append("  background-color: var(--color-surface, #1e293b);")
    lines.append("  color: var(--color-fg, #e2e8f0);")
    lines.append("  padding: calc(var(--spacing-unit, 1rem) * 0.5) var(--spacing-unit, 1rem);")
    lines.append("  cursor: pointer;")
    lines.append("  transition: background-color var(--motion-duration, 0.2s ease),")
    lines.append("              color var(--motion-duration, 0.2s ease);")
    lines.append("}")
    lines.append("")

    # Per-node CSS rules.
    all_tokens = extract_all_tokens(graph)
    node_css = _generate_node_css(graph, all_tokens)
    if node_css:
        lines.append("/* === Node-specific vibe tokens === */")
        lines.extend(node_css)

    # Proxy / DEGRADED markers from nodes.
    lines.extend(proxy_markers)
    lines.append("")

    return "\n".join(lines) + "\n"


def _generate_node_css(graph: SIRGraph, all_tokens: Dict[str, VibeTokenMap]) -> List[str]:
    """Generate per-node CSS rules with vibe-derived custom properties."""
    lines: List[str] = []
    for node_path, token_map in sorted(all_tokens.items()):
        node_id = token_map.node_id
        css_vars = token_map.css_variables
        if not css_vars:
            continue
        lines.append(f"#{node_id} {{")
        for css_name, css_val in css_vars.items():
            lines.append(f"  {css_name}: {css_val};")
        lines.append("}")
        for proxy in token_map.proxy:
            lines.append(proxy)
        for deg in token_map.degraded:
            lines.append(deg)
        lines.append("")
    return lines


# ---------------------------------------------------------------------------
# HTML generation
# ---------------------------------------------------------------------------


def _html_escape(text: str) -> str:
    """Escape HTML special characters."""
    return (text.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;"))


def _html_attrs(attrs: List[str]) -> str:
    """Join attribute list into a space-separated string."""
    return " ".join(attrs)


def _html_node(
    graph: SIRGraph,
    node: SIRNode,
    indent: int = 0,
    relational_links: Optional[List[Tuple[str, str, str, str]]] = None,
) -> List[str]:
    """Recursively generate HTML for a node and its children."""
    pad = "  " * indent
    node_id = _node_id(node.path)
    element = _semantic_element(node)
    label = _node_label(node)
    role = _aria_role(node)
    aria_label = _aria_label(node)

    # Build attribute list.
    attrs: List[str] = []
    attrs.append(f'id="{node_id}"')
    attrs.append(f'data-semantic-id="{node.path}"')
    attrs.append(f'data-node-type="{node.kind}"')
    attrs.append(f'role="{role}"')
    attrs.append(f'aria-label="{_html_escape(aria_label)}"')

    depth = _spatial_depth(node)
    attrs.append(f'data-depth="{depth}"')

    spatial_hint = _spatial_to_grid(node)
    if spatial_hint:
        attrs.append(f'data-spatial="{spatial_hint}"')

    if relational_links:
        for src, rel, tgt, _ in relational_links:
            if src == node.path:
                attrs.append(f'data-rel-{rel}="{tgt}"')

    token_map = extract_vibe_tokens(graph, node)
    if token_map.css_variables:
        attrs.append(f'class="orren-entity orren-node-{node_id}"')
    else:
        attrs.append('class="orren-entity"')

    attr_str = _html_attrs(attrs)

    lines: List[str] = []
    if element == "button":
        lines.append(f"{pad}<button {attr_str}>")
        lines.append(f"{pad}  {_html_escape(label)}")
        lines.append(f"{pad}</button>")
    elif element == "a":
        lines.append(f'{pad}<a {attr_str} href="#">{_html_escape(label)}</a>')
    elif element == "form":
        lines.append(f"{pad}<form {attr_str}>")
        for child in node.children:
            lines.extend(_html_node(graph, child, indent + 1, relational_links))
        lines.append(f"{pad}</form>")
    elif element == "header":
        lines.append(f"{pad}<header {attr_str}>")
        lines.append(f"{pad}  <h1>{_html_escape(label)}</h1>")
        for child in node.children:
            lines.extend(_html_node(graph, child, indent + 1, relational_links))
        lines.append(f"{pad}</header>")
    elif element == "footer":
        lines.append(f"{pad}<footer {attr_str}>")
        lines.append(f"{pad}  <p>{_html_escape(label)}</p>")
        lines.append(f"{pad}</footer>")
    elif element == "nav":
        lines.append(f"{pad}<nav {attr_str}>")
        lines.append(f"{pad}  <h2>{_html_escape(label)}</h2>")
        for child in node.children:
            lines.extend(_html_node(graph, child, indent + 1, relational_links))
        lines.append(f"{pad}</nav>")
    elif element == "main":
        lines.append(f"{pad}<main {attr_str}>")
        for child in node.children:
            lines.extend(_html_node(graph, child, indent + 1, relational_links))
        lines.append(f"{pad}</main>")
    elif element == "aside":
        lines.append(f"{pad}<aside {attr_str}>")
        lines.append(f"{pad}  <h2>{_html_escape(label)}</h2>")
        for child in node.children:
            lines.extend(_html_node(graph, child, indent + 1, relational_links))
        lines.append(f"{pad}</aside>")
    else:
        is_block = element in ("article", "section", "div")
        if is_block:
            lines.append(f"{pad}<{element} {attr_str}>")
            cog = node.get_dimension(Dimension.COGNITIVE)
            if cog:
                for c in cog:
                    if isinstance(c, dict):
                        predicate = c.get("predicate", "")
                        value = c.get("value", "")
                        if predicate and value:
                            lines.append(
                                f"{pad}  <dl><dt>{_html_escape(predicate)}</dt>"
                                f"<dd data-semantic-id=\"{node.path}.{predicate}\">{_html_escape(value)}</dd></dl>"
                            )
            conds = node.get_dimension(Dimension.CONDITIONAL)
            if conds:
                for c in conds:
                    if isinstance(c, dict):
                        cond_str = c.get("condition", "")
                        action = c.get("action", "")
                        lines.append(
                            f"{pad}  <span class=\"orren-condition\" "
                            f"data-condition=\"{_html_escape(cond_str)}\" "
                            f"data-action=\"{_html_escape(action)}\">{action} on {cond_str}</span>"
                        )
            lines.append(f"{pad}  <h{depth + 2}>{_html_escape(label)}</h{depth + 2}>")
            for child in node.children:
                lines.extend(_html_node(graph, child, indent + 1, relational_links))
            lines.append(f"{pad}</{element}>")
        else:
            lines.append(f"{pad}<{element} {attr_str}>{_html_escape(label)}</{element}>")

    return lines


def generate_html(graph: SIRGraph, target: RealizationTarget) -> str:
    """Generate a complete, production-grade HTML5 document.

    Features:
      - Semantic HTML5 elements derived from spatial dimension.
      - ARIA labels and roles derived from cognitive dimension.
      - ``data-semantic-id`` on every generated element.
      - ``lang`` attribute matching the .orn expression's declared locale.
      - Responsive viewport, accessibility meta tags.
      - Error boundary container for client-side JS.
    """
    locale = extract_locale(graph)
    title = graph.root.name if graph.root else "OrrenApp"
    relational_links = _extract_relational_links(graph)

    parts: List[str] = []
    parts.append("<!DOCTYPE html>")
    parts.append(f'<html lang="{locale}">')
    parts.append("<head>")
    parts.append('  <meta charset="utf-8">')
    parts.append('  <meta name="viewport" content="width=device-width, initial-scale=1">')
    parts.append('  <meta name="color-scheme" content="dark light">')
    # Theme color derives from the most specific vibe accent token in the
    # graph (root first, then child nodes), matching what the stylesheet
    # actually renders.
    accent = "#2ea04f"
    if graph.root is not None:
        candidates: List[VibeTokenMap] = []
        if extract_vibe_tokens(graph, graph.root).css_variables.get("--color-accent"):
            candidates.append(extract_vibe_tokens(graph, graph.root))
        candidates.extend(
            tm
            for _, tm in sorted(extract_all_tokens(graph).items())
            if tm.css_variables.get("--color-accent")
        )
        if candidates:
            accent = candidates[0].css_variables["--color-accent"]
    parts.append(f'  <meta name="theme-color" content="{accent}">')
    parts.append(f"  <title>{_html_escape(title)}</title>")
    parts.append('  <meta name="description" content="Orren-generated semantic web target">')
    parts.append('  <link rel="stylesheet" href="styles.css">')
    parts.append("</head>")
    parts.append("<body>")
    # Living-layer backdrop (decorative; hidden from assistive tech).
    from .web_gl import LIVING_CANVAS_HTML
    parts.append(LIVING_CANVAS_HTML)
    parts.append('  <header class="orren-header" role="banner">')
    parts.append(f'    <h1>{_html_escape(title)}</h1>')
    parts.append('    <button id="orren-theme-toggle" class="orren-theme-toggle" '
                 'aria-pressed="false" data-semantic-id="orren.theme_toggle">Theme</button>')
    parts.append(f'    <p data-semantic-id="orren.purpose">{_html_escape(_graph_purpose(graph))}</p>')
    parts.append("  </header>")
    parts.append('  <section id="orren-content" class="orren-section" role="region" aria-label="Main content">')
    parts.append('  <div id="orren-root" class="orren-container" data-app-id="orren-app" role="main">')

    # Error boundary.
    parts.append('    <div id="orren-error-boundary" class="orren-error-boundary" role="alert" aria-live="assertive" hidden>')
    parts.append('      <p>An error occurred in the Orren application. State preserved in localStorage.</p>')
    parts.append("    </div>")
    parts.append("")

    # Root node rendering.
    if graph.root is not None:
        node_lines = _html_node(graph, graph.root, indent=2, relational_links=relational_links)
        parts.extend(node_lines)

    parts.append("  </div>")
    parts.append("  </section>")

    # Footer with app metadata.
    parts.append('  <footer class="orren-footer" role="contentinfo" data-semantic-id="orren.metadata">')
    parts.append(f"    <p>{_html_escape(title)} — generated by Orren</p>")
    parts.append(f'    <p>Locale: <span id="orren-locale">{locale}</span> | '
                 f'Preservation: <span id="orren-preservation">{target.preservation_score}</span></p>')
    parts.append("  </footer>")

    # App initialization script (ES2022 module).
    parts.append('  <script type="module">')
    parts.append('    import { wireUpEvents, startTemporalSequences, initThemeToggle } from "./app.js";')
    parts.append('    window.OrrenApp = { fsmInstances: new Map(), config: {} };')
    parts.append('    try {')
    parts.append('      initThemeToggle();')
    parts.append('      wireUpEvents();')
    parts.append('      startTemporalSequences?.();')
    parts.append('      const living = await import("./living.js").then(m => m.autoWireLivingLayer()).catch(() => null);')
    parts.append('      if (living) console.info("[Orren] living layer:", living.renderer);')
    parts.append('      console.info("[Orren] Application initialized.");')
    parts.append('    } catch (err) {')
    parts.append('      const boundary = document.getElementById("orren-error-boundary");')
    parts.append('      if (boundary) { boundary.hidden = false; }')
    parts.append('      console.error("[Orren] Initialization error:", err);')
    parts.append('      localStorage.setItem("orren:error", JSON.stringify({')
    parts.append('        timestamp: Date.now(),')
    parts.append('        error: String(err),')
    parts.append('        stack: err?.stack || ""')
    parts.append('      }));')
    parts.append('    }')
    parts.append("</script>")
    parts.append("</body>")
    parts.append("</html>")

    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# JavaScript generation (ES2022 module)
# ---------------------------------------------------------------------------


def generate_js(graph: SIRGraph, target: RealizationTarget) -> str:
    """Generate a complete, production-grade ES2022 JavaScript module.

    Features:
      - Real state machine (OrrenFSM class) from behavioral/temporal dimensions.
      - Wire-up event handlers from conditional triggers.
      - Guarded transitions for conditional semantics.
      - Temporal sequences via setTimeout chains.
      - Relational link event delegation.
      - Error boundary and persistence to localStorage.
      - Resource limits (max listeners, transition cap).
      - Bridge markers for native capabilities not available in browser.
    """
    machines = _collect_state_machines(graph)
    parts: List[str] = []

    # ESM module header.
    parts.append("/**")
    parts.append(f" * Orren-generated ES2022 JavaScript module")
    parts.append(f" * Target: {target.name} ({target.language})")
    parts.append(f" * Preservation score: {target.preservation_score}")
    parts.append(" */")
    parts.append("")
    parts.append("'use strict';")
    parts.append("")

    # --- Configuration ---
    parts.append("const OrrenConfig = {")
    parts.append("  maxTransitionHistory: 100,")
    parts.append("  maxEventListeners: 50,")
    parts.append("  persistenceKey: 'orren:app_state',")
    parts.append("  debug: true,")
    parts.append("};")
    parts.append("")
    parts.append("export { OrrenConfig };")
    parts.append("")

    # --- State machine class + instances ---
    parts.append("/* --- State Machines (from behavioral/conditional/temporal) --- */")
    fsm_js = generate_state_machine_js(machines)
    parts.append(fsm_js)
    parts.append("")

    # --- Event wire-up ---
    parts.append("/* --- Event Handlers (from conditional dimension) --- */")
    handlers_js = generate_event_handlers(graph, machines)
    parts.append(handlers_js)
    parts.append("")

    # --- Temporal sequences (explicitly named for traceability) ---
    parts.append("// --- Temporal sequences (from temporal dimension) ---")
    temporal_added = False
    temporal_fns: List[str] = []
    machine_js_ids = {sm.js_id for sm in machines}
    for node in graph.nodes:
        seqs = _extract_temporal_sequences(node)
        # Root node temporal data is used for app-level sequencing.
        if not seqs and node.kind != "root":
            continue
        if not seqs:
            continue
        node_id = _node_id(node.path)
        js_id = _js_safe_id(node.path)
        # State machines exist only for non-root nodes; generated code must
        # never reference an undeclared identifier.
        has_machine = js_id in machine_js_ids
        for i, seq in enumerate(seqs):
            temporal_added = True
            fn_name = f"temporalSequence_{js_id}_{i}"
            temporal_fns.append(fn_name)
            parts.append(f"// Temporal sequence for {node.path}: {seq}")
            parts.append(f"export function {fn_name}() {{")
            parts.append("  let delay = 0;")
            for j, step in enumerate(seq):
                parts.append("  setTimeout(() => {")
                parts.append(f"    console.debug('temporal step {j}: {step}');")
                if has_machine:
                    parts.append(
                        f"    fsm_{js_id}?.transition('step_{j}', "
                        f"{{ nextState: 'step_{j}' }});"
                    )
                parts.append("    window.dispatchEvent(new CustomEvent('orren:temporal', {")
                parts.append(f"      detail: {{ nodeId: '{node_id}', step: {j}, event: '{step}' }}")
                parts.append("    }));")
                parts.append(f"  }}, delay);")
                parts.append("  delay += 200;")
            parts.append("}")
            parts.append("")
    if not temporal_added:
        parts.append("// No temporal sequences in this graph.")
        parts.append("")
    # Temporal bootstrap contract: app-level sequences self-start so the
    # temporal dimension is realized at runtime, not merely declared.
    # Always exported (no-op when the graph has no sequences) because the
    # HTML init script imports it by name.  Honors prefers-reduced-motion:
    # under reduced motion the sequences are NOT auto-started (an explicit
    # startTemporalSequences(true) still runs them).
    parts.append("// --- Temporal bootstrap (self-starting sequences) ---")
    parts.append("export function startTemporalSequences(force = false) {")
    parts.append("  if (!force && typeof matchMedia === 'function' &&")
    parts.append("      matchMedia('(prefers-reduced-motion: reduce)').matches) {")
    parts.append("    console.info('[Orren] temporal sequences deferred (reduced motion)');")
    parts.append("    return false;")
    parts.append("  }")
    parts.append("  const sequenceFns = [" + ", ".join(temporal_fns) + "];")
    parts.append("  for (const fn of sequenceFns) {")
    parts.append("    try { fn(); } catch (e) {")
    parts.append("      console.warn('[Orren] temporal sequence failed:', e);")
    parts.append("    }")
    parts.append("  }")
    parts.append("  return true;")
    parts.append("}")
    parts.append("")

    # --- Relational link delegation ---
    links = _extract_relational_links(graph)
    parts.append("// --- Relational links (from relational dimension) ---")
    if links:
        parts.append("export function wireUpRelationalLinks() {")
        # Fan-in graphs reference the same target from several sources;
        # each element lookup is emitted exactly once.
        emitted: set = set()
        for src, rel, tgt, _ in links:
            for node_path in (src, tgt):
                js_name = _js_safe_id(node_path)
                if js_name not in emitted:
                    emitted.add(js_name)
                    parts.append(
                        f"  const el_{js_name} = "
                        f"document.getElementById('{_node_id(node_path)}');"
                    )
        seen_pairs: set = set()
        for src, rel, tgt, _ in links:
            pair = (src, rel, tgt)
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)
            src_js = _js_safe_id(src)
            tgt_js = _js_safe_id(tgt)
            parts.append(f"  // {src} --{rel}--> {tgt}")
            parts.append(f"  if (el_{src_js} && el_{tgt_js}) {{")
            parts.append(f"    el_{src_js}.setAttribute('data-relates-to', '{tgt}');")
            parts.append(f"    el_{tgt_js}.setAttribute('data-related-from', '{src}');")
            parts.append(f"    el_{src_js}.addEventListener('click', () => {{")
            parts.append(f"      el_{tgt_js}.scrollIntoView({{ behavior: 'smooth' }});")
            parts.append(f"      el_{tgt_js}.dispatchEvent(new CustomEvent('orren:relate', {{")
            parts.append(f"        detail: {{ relation: '{rel}', source: '{src}', target: '{tgt}' }}")
            parts.append(f"      }}));")
            parts.append(f"    }});")
            parts.append(f"  }}")
            parts.append("")
        parts.append("}")
    else:
        parts.append("// No relational links in this graph.")
        parts.append("")

    # --- Persistence ---
    parts.append("// --- State persistence to localStorage ---")
    parts.append("export function saveAppState(state) {")
    parts.append("  try {")
    parts.append("    localStorage.setItem(OrrenConfig.persistenceKey, JSON.stringify(state));")
    parts.append("  } catch (e) {")
    parts.append("    console.warn('[Orren] Persistence failed:', e);")
    parts.append("  }")
    parts.append("}")
    parts.append("")
    parts.append("export function loadAppState() {")
    parts.append("  try {")
    parts.append("    const saved = localStorage.getItem(OrrenConfig.persistenceKey);")
    parts.append("    return saved ? JSON.parse(saved) : null;")
    parts.append("  } catch (e) {")
    parts.append("    console.warn('[Orren] State recovery failed:', e);")
    parts.append("    return null;")
    parts.append("  }")
    parts.append("}")
    parts.append("")

    # --- Error handling ---
    parts.append("// --- Error handling ---")
    parts.append("window.addEventListener('error', (evt) => {")
    parts.append("  const boundary = document.getElementById('orren-error-boundary');")
    parts.append("  if (boundary) { boundary.hidden = false; }")
    parts.append("  console.error('[Orren] Unhandled error:', evt.error);")
    parts.append("});")
    parts.append("")

    # --- Theme toggle (explicit class-based light/dark override) ---
    parts.append("// --- Theme toggle (explicit preference over OS default) ---")
    parts.append("export function initThemeToggle() {")
    parts.append("  const root = document.documentElement;")
    parts.append("  const stored = (() => {")
    parts.append("    try { return localStorage.getItem('orren:theme'); } catch (e) { return null; }")
    parts.append("  })();")
    parts.append("  const apply = (theme) => {")
    parts.append("    root.classList.remove('theme-light', 'theme-dark');")
    parts.append("    if (theme === 'light' || theme === 'dark') root.classList.add('theme-' + theme);")
    parts.append("    const btn = document.getElementById('orren-theme-toggle');")
    parts.append("    if (btn) btn.setAttribute('aria-pressed', String(theme === 'dark'));")
    parts.append("  };")
    parts.append("  if (stored === 'light' || stored === 'dark') apply(stored);")
    parts.append("  else if (typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: dark)').matches) apply('dark');")
    parts.append("  const btn = document.getElementById('orren-theme-toggle');")
    parts.append("  if (!btn) return;")
    parts.append("  btn.addEventListener('click', () => {")
    parts.append("    const next = root.classList.contains('theme-dark') ? 'light' : 'dark';")
    parts.append("    apply(next);")
    parts.append("    try { localStorage.setItem('orren:theme', next); } catch (e) { /* private mode */ }")
    parts.append("    window.dispatchEvent(new CustomEvent('orren:theme', { detail: { theme: next } }));")
    parts.append("  });")
    parts.append("}")
    parts.append("")

    # --- Bridge markers ---
    parts.append("// --- Bridge markers (native capabilities not available in browser) ---")
    for tgt in graph.realization_targets:
        for bridge in tgt.needs_bridge:
            parts.append(f"// BRIDGE: {bridge} - requires native bridge, not available in browser.")
    for dep in target.needs_bridge:
        parts.append(f"// BRIDGE: {dep} - requires native bridge, not available in browser.")
    parts.append("")

    return "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def _make_standalone(html: str, css: str, js: str) -> str:
    """Build a single-file variant that works when opened via ``file://``.

    ES module imports fail under the ``file://`` protocol (opaque origins
    forbid fetching local modules), so the standalone bundle inlines the
    stylesheet and strips export keywords before inlining the script.
    """
    out = html.replace(
        '<link rel="stylesheet" href="styles.css">',
        "<style>\n" + css + "</style>",
    )
    # Strip module exports: the init block below calls these names directly.
    body = re.sub(r"^export\s+(?=function|class)", "", js, flags=re.MULTILINE)
    body = re.sub(r"^export default \w+;$", "", body, flags=re.MULTILINE)
    body = re.sub(r"^export \{[^}]*\};$", "", body, flags=re.MULTILINE)
    import_line = (
        '    import { wireUpEvents, startTemporalSequences, initThemeToggle } '
        'from "./app.js";'
    )
    out = out.replace(import_line, "    " + body.replace("\n", "\n    ").rstrip())
    return out


def generate_web(graph: SIRGraph, target: RealizationTarget) -> Dict[str, str]:
    """Generate premium HTML5, CSS3, and ES2022 artifacts for a web target.

    Args:
        graph: The SIR graph to realize.
        target: The realization target (expected language ``"HTML/CSS/JS"``).

    Returns:
        Dict mapping ``"{target_name}/index.html"``, ``"{target_name}/styles.css"``,
        ``"{target_name}/app.js"``, and ``"{target_name}/index.standalone.html"``
        to their generated source strings.  The standalone variant is a single
        self-contained file that also works when opened directly from disk.
    """
    base = target.name
    html = generate_html(graph, target)
    css = generate_css(graph, target)
    js = generate_js(graph, target)
    living = generate_living_js(graph, target)
    artifacts = {
        f"{base}/index.html": html,
        f"{base}/styles.css": css,
        f"{base}/app.js": js,
        f"{base}/living.js": living,
        f"{base}/index.standalone.html": _make_standalone(html, css, js),
    }
    # Opt-in bundler scaffolding; empty unless the target asks for it.
    from .web_bundler import generate_bundler_files
    artifacts.update(generate_bundler_files(graph, target))
    return artifacts


__all__ = [
    "generate_web",
    "generate_html",
    "generate_css",
    "generate_js",
]
