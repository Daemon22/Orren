"""
Orren Engine — Preview Generator
================================

Produces a single self-contained HTML file that, when opened in a
browser, displays a visual mockup of the described interface.

Unlike the codegen module (which produces real implementation files),
the preview module produces a VISUALIZATION — it shows what the
interface would look like, with all vibes applied, structure tree
visible, equilibrium resolutions annotated, and degradation markers
displayed as badges.

The output is one HTML file per .orn source, with inline CSS and JS.
No external dependencies. Just open it in a browser.

Public API:
    generate_preview(graph) -> str   # returns HTML string
    write_preview(graph, path)        # writes HTML to file
"""

from __future__ import annotations

import html
import json
from typing import Dict, List, Optional

from .data_model import (
    Dimension,
    EquilibriumRule,
    RealizationArtifact,
    RealizationTarget,
    SIRGraph,
    SIRNode,
    ToleranceLevel,
)
from . import __version__


# ---------------------------------------------------------------------------
# Color mapping (richer than codegen's — preview needs to look good)
# ---------------------------------------------------------------------------

VIBE_COLOR_MAP = {
    "emerald": "#2ecc71",
    "green": "#27ae60",
    "warm_green": "#52b788",
    "trust_green": "#40916c",
    "amber": "#f59e0b",
    "warm_amber": "#d4a373",
    "amber_glow": "#e8a87c",
    "soft_amber": "#f4a261",
    "warm_amber_with_glow": "#e76f51",
    "amber_to_cream": "linear-gradient(135deg, #d4a373, #fef3c7)",
    "amber_alert": "#f59e0b",
    "warm_white": "#faf6f0",
    "cream_paper": "#f5ebd6",
    "warm_cream_with_blue_accents": "#faf6f0",
    "warm_blue": "#3a86b0",
    "deep_blue": "#1e3a5f",
    "deep_blue_with_amber_lamp": "#1e3a5f",
    "blue": "#3498db",
    "cold_blue": "#4a6fa5",
    "neutral_blue": "#5b8fb9",
    "positional_blue": "#4a90d9",
    "slate_blue": "#4a5568",
    "slate_grey_with_amber_warmth": "#475569",
    "slate_grey": "#64748b",
    "neutral_grey": "#94a3b8",
    "warm_grey": "#78716c",
    "storm_grey": "#475569",
    "dark_text": "#1f2937",
    "black_ink": "#111827",
    "grey_ink": "#6b7280",
    "warm_earth": "#a0522d",
    "warm_spectrum": "linear-gradient(90deg, #f59e0b, #ef4444, #8b5cf6, #3b82f6)",
    "deep_red": "#991b1b",
    "alert_red": "#dc2626",
    "red": "#e74c3c",
    "high_contrast_warm": "#1f2937",
    "soft_amber_warm": "#f4a261",
}

FORM_RADIUS_MAP = {
    "organic": "32px",
    "rounded": "16px",
    "classic": "4px",
    "structured": "2px",
    "generous_line_height": "8px",
}


def _resolve_color(term: str) -> str:
    """Resolve a vibe color term to a CSS color value."""
    term_lower = term.lower().replace(" ", "_")
    if term_lower in VIBE_COLOR_MAP:
        return VIBE_COLOR_MAP[term_lower]
    # Try partial matches
    for key, val in VIBE_COLOR_MAP.items():
        if key in term_lower or term_lower in key:
            return val
    # Fall back to a neutral
    return "#94a3b8"


def _resolve_radius(term: str) -> str:
    term_lower = term.lower()
    for key, val in FORM_RADIUS_MAP.items():
        if key in term_lower:
            return val
    return "8px"


# ---------------------------------------------------------------------------
# Preview generation
# ---------------------------------------------------------------------------


def generate_preview(graph: SIRGraph, artifacts: List[RealizationArtifact] = None) -> str:
    """Generate a self-contained HTML preview of the SIR graph."""
    if artifacts is None:
        from .realization_coordinator import RealizationCoordinator
        artifacts = RealizationCoordinator().coordinate(graph)

    app_name = graph.root.name if graph.root else "OrrenApp"
    purpose = _extract_purpose(graph)
    vibe_brief = _extract_vibe_brief(graph)

    # Build sections
    header_html = _build_header(app_name, purpose, vibe_brief, graph, artifacts)
    structure_html = _build_structure_tree(graph)
    canvas_html = _build_canvas(graph)
    equilibrium_html = _build_equilibrium_panel(graph)
    realization_html = _build_realization_panel(graph, artifacts)
    degradation_html = _build_degradation_panel(graph, artifacts)
    css = _build_css(graph)
    js = _build_js()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Orren Preview: {html.escape(app_name)}</title>
<style>
{css}
</style>
</head>
<body>
{header_html}
<main class="layout">
  <aside class="panel structure-panel">
    <h2>Structure</h2>
    {structure_html}
  </aside>
  <section class="panel canvas-panel">
    <h2>Interface Preview</h2>
    <p class="hint">Each card represents an entity. Colors and shapes come from vibe dimensions. Hover for details.</p>
    {canvas_html}
  </section>
  <aside class="panel info-panel">
    {equilibrium_html}
    {realization_html}
    {degradation_html}
  </aside>
</main>
<footer>
  <span>Orren Engine v{__version__}</span>
  <span>{len(graph.nodes)} nodes · {len(graph.equilibrium_rules)} equilibrium rules · {len(artifacts)} targets</span>
</footer>
<script>
{js}
</script>
</body>
</html>"""


def write_preview(graph: SIRGraph, path: str, artifacts: List[RealizationArtifact] = None) -> None:
    """Generate and write a preview HTML file."""
    html_content = generate_preview(graph, artifacts)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html_content)


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _extract_purpose(graph: SIRGraph) -> str:
    if graph.root is None:
        return ""
    for entry in graph.root.get_dimension(Dimension.EXPRESSION):
        if isinstance(entry, dict) and entry.get("key") == "purpose":
            return str(entry.get("value", ""))
    return ""


def _extract_vibe_brief(graph: SIRGraph) -> str:
    if graph.root is None:
        return ""
    for entry in graph.root.get_dimension(Dimension.EXPRESSION):
        if isinstance(entry, dict) and entry.get("key") == "vibe_brief":
            return str(entry.get("value", ""))
    return ""


def _build_header(app_name, purpose, vibe_brief, graph, artifacts) -> str:
    avg_score = (
        sum(a.preservation_score for a in artifacts) / len(artifacts)
        if artifacts else 0.0
    )
    return f"""
<header class="app-header">
  <div class="header-content">
    <h1>{html.escape(app_name.replace("_", " ").title())}</h1>
    <p class="purpose">{html.escape(purpose)}</p>
    {f'<p class="vibe-brief">Vibe: <em>{html.escape(vibe_brief)}</em></p>' if vibe_brief else ''}
    <div class="meta-row">
      <span class="badge badge-info">{len(graph.nodes)} entities</span>
      <span class="badge badge-info">{len(graph.equilibrium_rules)} equilibrium rules</span>
      <span class="badge badge-info">{len(artifacts)} realization targets</span>
      <span class="badge badge-score">avg preservation: {avg_score:.2f}</span>
    </div>
  </div>
</header>"""


def _build_structure_tree(graph: SIRGraph) -> str:
    """Build a nested <ul> tree of all entities."""
    if graph.root is None:
        return "<p class='empty'>No structure</p>"

    def render_node(node: SIRNode, depth: int = 0) -> str:
        label = html.escape(node.name.replace("_", " "))
        kind_label = f"<span class='kind'>{node.kind}</span>" if node.kind != "entity" else ""
        dim_count = sum(1 for d in Dimension if node.has_dimension_content(d))
        dim_label = f"<span class='dim-count'>{dim_count}d</span>" if dim_count > 0 else ""
        children_html = ""
        if node.children:
            children_html = "<ul>" + "".join(
                render_node(c, depth + 1) for c in node.children
            ) + "</ul>"
        return f"<li><span class='entity-label' data-path='{html.escape(node.path)}'>{label}</span> {kind_label}{dim_label}{children_html}</li>"

    return f"<ul class='tree'>{render_node(graph.root)}</ul>"


def _build_canvas(graph: SIRGraph) -> str:
    """Build the visual mockup — each entity with vibe content becomes
    a visible card with its vibes applied."""
    if graph.root is None:
        return "<p class='empty'>No entities to display</p>"

    cards: List[str] = []
    for node in graph.nodes:
        if node.kind == "root":
            continue
        if not _has_visual_content(node):
            continue
        cards.append(_render_entity_card(node))

    if not cards:
        return "<p class='empty'>No visual entities (add vibe or spatial dimensions to see cards)</p>"

    return f"<div class='canvas-grid'>{''.join(cards)}</div>"


def _has_visual_content(node: SIRNode) -> bool:
    return (
        node.has_dimension_content(Dimension.VIBE)
        or node.has_dimension_content(Dimension.SPATIAL)
        or node.has_dimension_content(Dimension.COGNITIVE)
        or node.has_dimension_content(Dimension.CONDITIONAL)
        or node.has_dimension_content(Dimension.BEHAVIORAL)
    )


def _render_entity_card(node: SIRNode) -> str:
    """Render one entity as a visual card with vibes applied."""
    vibes = node.get_dimension(Dimension.VIBE)
    color = "#64748b"
    radius = "8px"
    tone = ""
    aesthetic = ""
    intensity = ""

    for v in vibes:
        if not isinstance(v, dict):
            continue
        aspect = v.get("aspect", "")
        term = v.get("term", "")
        if aspect == "color_character":
            color = _resolve_color(term)
        elif aspect == "form_character":
            radius = _resolve_radius(term)
        elif aspect == "tone":
            tone = term
        elif aspect == "aesthetic":
            aesthetic = term
        elif aspect == "intensity":
            intensity = term

    label = html.escape(node.name.replace("_", " ").title())
    path_short = html.escape(node.path.split(".")[-1])

    # Dimension badges
    dim_badges = []
    for dim in Dimension.semantic():
        if node.has_dimension_content(dim):
            count = len(node.get_dimension(dim))
            dim_badges.append(
                f"<span class='dim-badge dim-{dim.value}' title='{dim.value}: {count} entries'>{dim.value[0].upper()}{count}</span>"
            )

    # Equilibrium badges
    eq_badges = []
    for eq in node.get_dimension(Dimension.EQUILIBRIUM):
        if isinstance(eq, dict):
            rule_name = eq.get("rule", "")
            eq_badges.append(f"<span class='eq-badge' title='{html.escape(str(eq))}'>⚖ {html.escape(rule_name)}</span>")

    # Degradation badges
    deg_badges = []
    for key, entry in node.degradation_tolerance.items():
        if entry.level in (ToleranceLevel.PROXY, ToleranceLevel.DOCUMENTED, ToleranceLevel.OPTIONAL):
            deg_badges.append(
                f"<span class='deg-badge deg-{entry.level.value}' title='{html.escape(key)}: {entry.level.value}'>{entry.level.value}</span>"
            )

    # Vibe details (collapsible)
    vibe_details = ""
    if vibes:
        vibe_items = []
        for v in vibes:
            if isinstance(v, dict):
                aspect = v.get("aspect", "")
                term = v.get("term", "")
                vibe_items.append(f"<div class='vibe-item'><span class='vibe-aspect'>{html.escape(aspect)}</span>: <span class='vibe-term'>{html.escape(str(term))}</span></div>")
        vibe_details = f"<div class='vibe-details' hidden>{''.join(vibe_items)}</div>"

    style = f"background: {color}; border-radius: {radius};"
    if "linear-gradient" not in color:
        style += " opacity: 0.92;"

    return f"""
<div class="entity-card" style="{style}" data-path="{html.escape(node.path)}">
  <div class="card-header">
    <span class="card-label">{label}</span>
    <span class="card-path">{path_short}</span>
  </div>
  <div class="card-badges">
    {''.join(dim_badges)}
  </div>
  {f'<div class="card-vibes">{" ".join(eq_badges)} {" ".join(deg_badges)}</div>' if (eq_badges or deg_badges) else ''}
  {vibe_details}
  <button class="expand-btn" onclick="this.parentElement.querySelector('.vibe-details').hidden = !this.parentElement.querySelector('.vibe-details').hidden">details</button>
</div>"""


def _build_equilibrium_panel(graph: SIRGraph) -> str:
    if not graph.equilibrium_rules:
        return "<div class='sub-panel'><h3>Equilibrium</h3><p class='empty'>No rules declared</p></div>"

    items = []
    for rule in graph.equilibrium_rules:
        # Find if this rule fired (check nodes for EQUILIBRIUM payload)
        fired = any(
            any(
                isinstance(eq, dict) and eq.get("rule") == rule.name
                for eq in node.get_dimension(Dimension.EQUILIBRIUM)
            )
            for node in graph.nodes
        )
        status = "fired" if fired else "not fired"
        preserve = ", ".join(rule.preserve) if rule.preserve else "—"
        resolution = rule.resolution.text if rule.resolution else "—"
        items.append(f"""
<div class="eq-item {'eq-fired' if fired else 'eq-not-fired'}">
  <div class="eq-name">⚖ {html.escape(rule.name)}</div>
  <div class="eq-status">{status}</div>
  <div class="eq-detail"><strong>Preserve:</strong> {html.escape(preserve)}</div>
  <div class="eq-detail"><strong>Resolution:</strong> {html.escape(resolution)}</div>
</div>""")

    return f"""
<div class="sub-panel">
  <h3>Equilibrium ({len(graph.equilibrium_rules)} rules)</h3>
  {''.join(items)}
</div>"""


def _build_realization_panel(graph: SIRGraph, artifacts: List[RealizationArtifact]) -> str:
    if not artifacts:
        return "<div class='sub-panel'><h3>Realization</h3><p class='empty'>No targets</p></div>"

    items = []
    for art in artifacts:
        score_class = "score-high" if art.preservation_score >= 0.9 else "score-mid" if art.preservation_score >= 0.7 else "score-low"
        caps = ", ".join(art.capabilities[:4]) if art.capabilities else "—"
        items.append(f"""
<div class="rz-item">
  <div class="rz-name">{html.escape(art.target_name)}</div>
  <div class="rz-lang">{html.escape(art.target_language)}</div>
  <div class="rz-score {score_class}">{art.preservation_score:.2f}</div>
  <div class="rz-detail"><strong>Capabilities:</strong> {html.escape(caps)}</div>
  <div class="rz-detail"><strong>Output files:</strong> {len(art.output_files)}</div>
  <div class="rz-detail"><strong>Degradation rows:</strong> {len(art.degradation_report)}</div>
</div>""")

    return f"""
<div class="sub-panel">
  <h3>Realization ({len(artifacts)} targets)</h3>
  {''.join(items)}
</div>"""


def _build_degradation_panel(graph: SIRGraph, artifacts: List[RealizationArtifact]) -> str:
    """Collect all PROXY/BRIDGE degradation entries across artifacts."""
    proxy_entries = []
    bridge_entries = []
    out_of_scope = 0

    for art in artifacts:
        for entry in art.degradation_report:
            source = entry.get("source", "")
            if source == "needs_bridge":
                bridge_entries.append(entry)
            elif entry.get("tolerance") in ("proxy", "documented", "optional"):
                proxy_entries.append(entry)
            elif entry.get("severity") == "out_of_scope":
                out_of_scope += 1

    proxy_html = ""
    if proxy_entries:
        items = []
        for e in proxy_entries[:15]:  # cap at 15 for readability
            items.append(
                f"<div class='deg-row'><span class='deg-aspect'>{html.escape(e.get('aspect', ''))}</span>"
                f"<span class='deg-level deg-{e.get('tolerance', '')}'>{e.get('tolerance', '')}</span>"
                f"<span class='deg-node'>{html.escape(e.get('node', '').split('.')[-1])}</span></div>"
            )
        proxy_html = f"<div class='deg-group'><h4>Proxy / Documented ({len(proxy_entries)})</h4>{''.join(items)}</div>"

    bridge_html = ""
    if bridge_entries:
        items = []
        for e in bridge_entries[:10]:
            items.append(
                f"<div class='deg-row'><span class='deg-aspect'>{html.escape(e.get('aspect', ''))}</span>"
                f"<span class='deg-source'>bridge</span>"
                f"<span class='deg-node'>{html.escape(e.get('node', '').split('.')[-1])}</span></div>"
            )
        bridge_html = f"<div class='deg-group'><h4>Needs Bridge ({len(bridge_entries)})</h4>{''.join(items)}</div>"

    summary = f"<div class='deg-summary'>PROXY: {len(proxy_entries)} · BRIDGE: {len(bridge_entries)} · OUT_OF_SCOPE: {out_of_scope}</div>"

    return f"""
<div class="sub-panel">
  <h3>Degradation Map</h3>
  {summary}
  {proxy_html}
  {bridge_html}
</div>"""


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def _build_css(graph: SIRGraph) -> str:
    # Derive a base palette from the root vibe if present.
    bg = "#0f172a"
    fg = "#e2e8f0"
    accent = "#3b82f6"
    if graph.root:
        for v in graph.root.get_dimension(Dimension.VIBE):
            if isinstance(v, dict):
                if v.get("aspect") == "color_character":
                    accent = _resolve_color(v.get("term", ""))
                    break

    return f"""
:root {{
  --bg: {bg};
  --fg: {fg};
  --accent: {accent};
  --panel-bg: #1e293b;
  --panel-border: #334155;
  --muted: #94a3b8;
  --eq-color: #f59e0b;
  --proxy-color: #ef4444;
  --bridge-color: #8b5cf6;
  --good-color: #10b981;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
  background: var(--bg);
  color: var(--fg);
  line-height: 1.5;
  font-size: 14px;
}}
.app-header {{
  background: linear-gradient(135deg, var(--panel-bg), var(--bg));
  border-bottom: 2px solid var(--accent);
  padding: 24px 32px;
}}
.app-header h1 {{
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--fg);
}}
.app-header .purpose {{
  color: var(--muted);
  font-size: 15px;
  margin-bottom: 4px;
  max-width: 80ch;
}}
.app-header .vibe-brief {{
  color: var(--accent);
  font-size: 13px;
  margin-bottom: 12px;
}}
.meta-row {{
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}}
.badge {{
  display: inline-block;
  padding: 4px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}}
.badge-info {{
  background: rgba(59, 130, 246, 0.2);
  color: #93c5fd;
  border: 1px solid rgba(59, 130, 246, 0.3);
}}
.badge-score {{
  background: rgba(16, 185, 129, 0.2);
  color: #6ee7b7;
  border: 1px solid rgba(16, 185, 129, 0.3);
}}
.layout {{
  display: grid;
  grid-template-columns: 280px 1fr 360px;
  gap: 16px;
  padding: 16px;
  min-height: calc(100vh - 200px);
}}
.panel {{
  background: var(--panel-bg);
  border: 1px solid var(--panel-border);
  border-radius: 12px;
  padding: 16px;
  overflow-y: auto;
  max-height: calc(100vh - 120px);
}}
.panel h2 {{
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--panel-border);
}}
.panel .hint {{
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 16px;
}}
.structure-panel .tree {{
  list-style: none;
  font-size: 13px;
}}
.structure-panel .tree ul {{
  list-style: none;
  padding-left: 16px;
  border-left: 1px solid var(--panel-border);
  margin-left: 4px;
}}
.structure-panel .tree li {{
  padding: 4px 0;
}}
.structure-panel .entity-label {{
  color: var(--fg);
  cursor: pointer;
  transition: color 0.15s;
}}
.structure-panel .entity-label:hover {{
  color: var(--accent);
}}
.structure-panel .kind {{
  font-size: 11px;
  color: var(--muted);
  background: rgba(148, 163, 184, 0.15);
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: 4px;
}}
.structure-panel .dim-count {{
  font-size: 11px;
  color: var(--accent);
  margin-left: 4px;
}}
.canvas-panel {{
  display: flex;
  flex-direction: column;
}}
.canvas-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  align-content: start;
}}
.entity-card {{
  padding: 14px;
  border: 1px solid rgba(255,255,255,0.15);
  box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  min-height: 100px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: transform 0.15s, box-shadow 0.15s;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}}
.entity-card:hover {{
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
}}
.card-header {{
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}}
.card-label {{
  font-size: 15px;
  font-weight: 600;
}}
.card-path {{
  font-size: 11px;
  opacity: 0.7;
  font-family: monospace;
}}
.card-badges {{
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}}
.dim-badge {{
  font-size: 10px;
  padding: 2px 6px;
  border-radius: 4px;
  background: rgba(0,0,0,0.4);
  font-weight: 600;
}}
.card-vibes {{
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
  font-size: 10px;
}}
.eq-badge {{
  background: rgba(245, 158, 11, 0.3);
  color: #fbbf24;
  padding: 2px 6px;
  border-radius: 4px;
}}
.deg-badge {{
  background: rgba(239, 68, 68, 0.3);
  color: #fca5a5;
  padding: 2px 6px;
  border-radius: 4px;
  text-transform: uppercase;
  font-weight: 600;
}}
.deg-badge.deg-proxy {{ background: rgba(239, 68, 68, 0.3); color: #fca5a5; }}
.deg-badge.deg-documented {{ background: rgba(168, 85, 247, 0.3); color: #c4b5fd; }}
.deg-badge.deg-optional {{ background: rgba(100, 116, 139, 0.3); color: #cbd5e1; }}
.vibe-details {{
  font-size: 11px;
  border-top: 1px solid rgba(255,255,255,0.2);
  padding-top: 8px;
  margin-top: 4px;
}}
.vibe-item {{
  display: flex;
  justify-content: space-between;
  padding: 2px 0;
}}
.vibe-aspect {{ opacity: 0.8; }}
.vibe-term {{ font-weight: 500; }}
.expand-btn {{
  align-self: flex-start;
  background: rgba(0,0,0,0.3);
  border: 1px solid rgba(255,255,255,0.2);
  color: #fff;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
  margin-top: auto;
}}
.expand-btn:hover {{
  background: rgba(0,0,0,0.5);
}}
.info-panel {{
  display: flex;
  flex-direction: column;
  gap: 16px;
}}
.sub-panel {{
  background: rgba(15, 23, 42, 0.5);
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  padding: 12px;
}}
.sub-panel h3 {{
  font-size: 13px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--muted);
  margin-bottom: 10px;
}}
.eq-item {{
  padding: 8px;
  margin-bottom: 8px;
  border-radius: 6px;
  border-left: 3px solid;
  background: rgba(30, 41, 59, 0.6);
}}
.eq-item.eq-fired {{
  border-color: var(--good-color);
}}
.eq-item.eq-not-fired {{
  border-color: var(--muted);
  opacity: 0.6;
}}
.eq-name {{
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 4px;
}}
.eq-status {{
  font-size: 11px;
  text-transform: uppercase;
  color: var(--muted);
  margin-bottom: 4px;
}}
.eq-detail {{
  font-size: 11px;
  color: var(--muted);
  margin-top: 2px;
}}
.rz-item {{
  padding: 8px;
  margin-bottom: 8px;
  border-radius: 6px;
  background: rgba(30, 41, 59, 0.6);
  border-left: 3px solid var(--accent);
}}
.rz-name {{
  font-weight: 600;
  font-size: 13px;
}}
.rz-lang {{
  font-size: 11px;
  color: var(--muted);
  font-family: monospace;
}}
.rz-score {{
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  margin: 4px 0;
}}
.score-high {{ background: rgba(16, 185, 129, 0.3); color: #6ee7b7; }}
.score-mid {{ background: rgba(245, 158, 11, 0.3); color: #fbbf24; }}
.score-low {{ background: rgba(239, 68, 68, 0.3); color: #fca5a5; }}
.rz-detail {{
  font-size: 11px;
  color: var(--muted);
  margin-top: 2px;
}}
.deg-summary {{
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 10px;
  padding: 6px;
  background: rgba(30, 41, 59, 0.6);
  border-radius: 4px;
  text-align: center;
}}
.deg-group {{
  margin-bottom: 12px;
}}
.deg-group h4 {{
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 6px;
}}
.deg-row {{
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 3px 0;
  font-size: 11px;
  border-bottom: 1px solid rgba(51, 65, 85, 0.4);
}}
.deg-aspect {{
  flex: 1;
  color: var(--fg);
}}
.deg-level {{
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  text-transform: uppercase;
  font-weight: 600;
}}
.deg-level.deg-proxy {{ background: rgba(239,68,68,0.3); color: #fca5a5; }}
.deg-level.deg-documented {{ background: rgba(168,85,247,0.3); color: #c4b5fd; }}
.deg-level.deg-optional {{ background: rgba(100,116,139,0.3); color: #cbd5e1; }}
.deg-source {{
  font-size: 10px;
  padding: 1px 5px;
  border-radius: 3px;
  background: rgba(139,92,246,0.3);
  color: #c4b5fd;
  text-transform: uppercase;
  font-weight: 600;
}}
.deg-node {{
  font-family: monospace;
  font-size: 10px;
  color: var(--muted);
}}
.empty {{
  color: var(--muted);
  font-style: italic;
  font-size: 12px;
}}
footer {{
  padding: 12px 32px;
  border-top: 1px solid var(--panel-border);
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--muted);
}}
@media (max-width: 1024px) {{
  .layout {{
    grid-template-columns: 1fr;
  }}
  .panel {{
    max-height: none;
  }}
}}
"""


# ---------------------------------------------------------------------------
# JS
# ---------------------------------------------------------------------------


def _build_js() -> str:
    return """
document.querySelectorAll('.entity-label').forEach(el => {
  el.addEventListener('click', () => {
    const path = el.dataset.path;
    const card = document.querySelector(`.entity-card[data-path="${path}"]`);
    if (card) {
      card.scrollIntoView({behavior: 'smooth', block: 'center'});
      card.style.outline = '3px solid #3b82f6';
      setTimeout(() => card.style.outline = '', 1500);
    }
  });
});
"""


__all__ = ["generate_preview", "write_preview"]
