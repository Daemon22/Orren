"""
Orren Engine — Preview Generator
================================

Produces a single self-contained HTML file that, when opened in a
browser, displays a visual mockup of the described interface — with
the design tokens derived from the .orn's vibe dimensions applied to
the WHOLE PAGE, not just entity badges.

A meditation app, a financial contract, a children's story, and a
robotics device will all look genuinely different because their vibes
drive different palettes, typography, layouts, motion, and texture.

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
    RealizationArtifact,
    SIRGraph,
    SIRNode,
    ToleranceLevel,
)
from . import __version__
from .design_tokens import DesignTokens, extract_design_tokens


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------


def generate_preview(graph: SIRGraph, artifacts: List[RealizationArtifact] = None) -> str:
    """Generate a self-contained HTML preview of the SIR graph."""
    if artifacts is None:
        from .realization_coordinator import RealizationCoordinator
        artifacts = RealizationCoordinator().coordinate(graph)

    tokens = extract_design_tokens(graph)
    app_name = graph.root.name if graph.root else "OrrenApp"
    purpose = _extract_purpose(graph)
    vibe_brief = _extract_vibe_brief(graph)

    # Build sections by layout strategy
    css = _build_css(tokens, graph)
    js = _build_js(tokens)

    # Choose layout renderer
    strategy = tokens.layout_strategy
    if strategy == "document":
        body_inner = _render_document_layout(graph, artifacts, tokens, app_name, purpose, vibe_brief)
    elif strategy == "schematic":
        body_inner = _render_schematic_layout(graph, artifacts, tokens, app_name, purpose, vibe_brief)
    elif strategy == "atmospheric":
        body_inner = _render_atmospheric_layout(graph, artifacts, tokens, app_name, purpose, vibe_brief)
    elif strategy == "dashboard":
        body_inner = _render_dashboard_layout(graph, artifacts, tokens, app_name, purpose, vibe_brief)
    else:  # app
        body_inner = _render_app_layout(graph, artifacts, tokens, app_name, purpose, vibe_brief)

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
{body_inner}
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
# Helpers
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


def _build_css(tokens: DesignTokens, graph: SIRGraph) -> str:
    """Build the complete CSS, with design tokens applied."""
    texture_css = _build_texture_css(tokens)

    # Layout-specific CSS
    layout_css = {
        "document": _LAYOUT_CSS_DOCUMENT,
        "dashboard": _LAYOUT_CSS_DASHBOARD,
        "app": _LAYOUT_CSS_APP,
        "atmospheric": _LAYOUT_CSS_ATMOSPHERIC,
        "schematic": _LAYOUT_CSS_SCHEMATIC,
    }.get(tokens.layout_strategy, _LAYOUT_CSS_DASHBOARD)

    breathing_keyframes = ""
    if tokens.breathing_animation:
        breathing_keyframes = """
@keyframes breathe {
  0%, 100% { transform: scale(1); opacity: 0.85; }
  50% { transform: scale(1.03); opacity: 1; }
}
.breathing { animation: breathe 8s cubic-bezier(0.4, 0, 0.2, 1) infinite; }
@keyframes drift {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
.drift { animation: drift 12s cubic-bezier(0.4, 0, 0.2, 1) infinite; }
"""

    return f"""
:root {{
{tokens.to_css_vars()}
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  font-family: var(--body-font);
  background: {tokens.bg if not tokens.bg_gradient else tokens.bg_gradient};
  color: var(--fg);
  line-height: var(--line-height);
  font-size: var(--body-size);
  letter-spacing: var(--letter-spacing);
  min-height: 100vh;
{texture_css}
}}
{_BASE_CSS}
{breathing_keyframes}
{layout_css}
"""


def _build_texture_css(tokens: DesignTokens) -> str:
    """Build CSS for the texture overlay."""
    if tokens.texture == "none" or tokens.texture_opacity == 0:
        return ""
    opacity = tokens.texture_opacity
    if tokens.texture == "gradient":
        return f"""  background-image: radial-gradient(circle at 30% 20%, rgba(255,255,255,{opacity * 0.3}), transparent 60%),
              radial-gradient(circle at 70% 80%, rgba(255,255,255,{opacity * 0.2}), transparent 60%);"""
    if tokens.texture == "grain":
        # Use a CSS-only grain effect
        return f"""  position: relative;"""
    if tokens.texture == "vignette":
        return f"""  box-shadow: inset 0 0 200px rgba(0,0,0,{opacity});"""
    return ""


# ---------------------------------------------------------------------------
# Layout: Document (books, contracts)
# ---------------------------------------------------------------------------


def _render_document_layout(graph, artifacts, tokens, app_name, purpose, vibe_brief) -> str:
    """A page-like document layout — single column, wide margins, justified."""
    title = html.escape(app_name.replace("_", " ").title())
    sections_html = _render_document_sections(graph, tokens)
    eq_panel = _render_equilibrium_compact(graph, tokens)
    rz_panel = _render_realization_compact(graph, artifacts, tokens)

    return f"""
<div class="document-page">
  <header class="doc-header">
    <h1>{title}</h1>
    {f'<p class="doc-purpose">{html.escape(purpose)}</p>' if purpose else ''}
    {f'<p class="doc-vibe">Vibe: <em>{html.escape(vibe_brief)}</em></p>' if vibe_brief else ''}
  </header>
  <main class="doc-body">
    {sections_html}
  </main>
  <aside class="doc-aside">
    {eq_panel}
    {rz_panel}
  </aside>
  <footer class="doc-footer">
    <span>Orren Engine v{__version__} · {len(graph.nodes)} nodes · {len(artifacts)} targets</span>
  </footer>
</div>"""


def _render_document_sections(graph, tokens) -> str:
    """Render each top-level structure node as a document section."""
    if graph.root is None:
        return "<p class='empty'>No content</p>"
    parts = []
    for child in graph.root.children:
        parts.append(_render_doc_section(child, 1))
    return "\n".join(parts)


def _render_doc_section(node: SIRNode, level: int) -> str:
    """Render a node as a heading + body section."""
    title = html.escape(node.name.replace("_", " ").title())
    tag = f"h{min(level + 1, 6)}"

    # Collect content
    body_parts = []

    # Cognitive content as paragraphs
    for cog in node.get_dimension(Dimension.COGNITIVE):
        if isinstance(cog, dict):
            pred = html.escape(str(cog.get("predicate", "")).replace("_", " "))
            val = html.escape(str(cog.get("value", "")))
            body_parts.append(f"<p><strong>{pred}:</strong> {val}</p>")

    # Conditional content as a list
    conds = node.get_dimension(Dimension.CONDITIONAL)
    if conds:
        items = []
        for c in conds:
            if isinstance(c, dict):
                subj = html.escape(str(c.get("subject", "")))
                cond = html.escape(str(c.get("condition", "")))
                items.append(f"<li>{subj} {c.get('action', '—')} when {cond}</li>")
        body_parts.append(f"<ul>{''.join(items)}</ul>")

    # Children
    for child in node.children:
        body_parts.append(_render_doc_section(child, level + 1))

    return f"<section><{tag}>{title}</{tag}>{''.join(body_parts)}</section>"


# ---------------------------------------------------------------------------
# Layout: Dashboard (information-dense)
# ---------------------------------------------------------------------------


def _render_dashboard_layout(graph, artifacts, tokens, app_name, purpose, vibe_brief) -> str:
    """A 3-column dashboard: structure tree | canvas | info panels."""
    header = _render_header(app_name, purpose, vibe_brief, graph, artifacts, tokens)
    structure_html = _build_structure_tree(graph, tokens)
    canvas_html = _build_canvas(graph, tokens)
    eq_html = _build_equilibrium_panel(graph, tokens)
    rz_html = _build_realization_panel(graph, artifacts, tokens)
    deg_html = _build_degradation_panel(graph, artifacts, tokens)

    return f"""
{header}
<main class="layout-dashboard">
  <aside class="panel structure-panel">
    <h2>Structure</h2>
    {structure_html}
  </aside>
  <section class="panel canvas-panel">
    <h2>Interface Preview</h2>
    <p class="hint">Each card is an entity. Colors and shapes come from vibe dimensions. Hover for details.</p>
    {canvas_html}
  </section>
  <aside class="panel info-panel">
    {eq_html}
    {rz_html}
    {deg_html}
  </aside>
</main>
<footer class="dash-footer">
  <span>Orren Engine v{__version__}</span>
  <span>{len(graph.nodes)} nodes · {len(graph.equilibrium_rules)} eq rules · {len(artifacts)} targets</span>
</footer>"""


# ---------------------------------------------------------------------------
# Layout: App (focused, single-purpose)
# ---------------------------------------------------------------------------


def _render_app_layout(graph, artifacts, tokens, app_name, purpose, vibe_brief) -> str:
    """A focused app layout — centered canvas, panels slide in."""
    header = _render_header(app_name, purpose, vibe_brief, graph, artifacts, tokens)
    canvas_html = _build_canvas(graph, tokens)
    eq_html = _build_equilibrium_panel(graph, tokens)
    rz_html = _build_realization_panel(graph, artifacts, tokens)
    structure_html = _build_structure_tree(graph, tokens)

    return f"""
{header}
<main class="layout-app">
  <section class="app-canvas">
    {canvas_html}
  </section>
  <details class="app-panels">
    <summary>Show details (structure, equilibrium, realization)</summary>
    <div class="app-panels-grid">
      <div class="panel">{structure_html}</div>
      <div class="panel">{eq_html}</div>
      <div class="panel">{rz_html}</div>
    </div>
  </details>
</main>
<footer class="dash-footer">
  <span>Orren Engine v{__version__}</span>
  <span>{len(graph.nodes)} nodes · {len(graph.equilibrium_rules)} eq rules · {len(artifacts)} targets</span>
</footer>"""


# ---------------------------------------------------------------------------
# Layout: Atmospheric (vibe-dominant — meditation, music, narrative)
# ---------------------------------------------------------------------------


def _render_atmospheric_layout(graph, artifacts, tokens, app_name, purpose, vibe_brief) -> str:
    """A vibe-dominant layout — full-bleed canvas, minimal chrome, atmosphere first."""
    title = html.escape(app_name.replace("_", " ").title())
    canvas_html = _build_atmospheric_canvas(graph, tokens)
    eq_html = _build_equilibrium_panel(graph, tokens)
    rz_html = _build_realization_panel(graph, artifacts, tokens)
    structure_html = _build_structure_tree(graph, tokens)

    # Equilibrium as floating wisdom
    wisdom_html = ""
    if graph.equilibrium_rules:
        items = []
        for rule in graph.equilibrium_rules[:3]:  # top 3 most prominent
            if rule.resolution and rule.resolution.text:
                items.append(
                    f"<div class='wisdom-item' title='{html.escape(rule.name)}'>"
                    f"<em>{html.escape(rule.resolution.text)}</em></div>"
                )
        if items:
            wisdom_html = f"<div class='wisdom-panel'>{''.join(items)}</div>"

    return f"""
<div class="atmospheric-scene breathing">
  <div class="atmospheric-vignette"></div>
  <header class="atmospheric-header">
    <h1>{title}</h1>
    {f'<p class="atmospheric-purpose">{html.escape(purpose)}</p>' if purpose else ''}
    {f'<p class="atmospheric-vibe">{html.escape(vibe_brief)}</p>' if vibe_brief else ''}
    <div class="atmospheric-meta">
      <span>{len(graph.nodes)} entities</span>
      <span>{len(graph.equilibrium_rules)} equilibrium rules</span>
      <span>{len(artifacts)} targets</span>
    </div>
  </header>
  <main class="atmospheric-canvas">
    {canvas_html}
  </main>
  {wisdom_html}
  <details class="atmospheric-details">
    <summary>structure · equilibrium · realization</summary>
    <div class="atmospheric-panels">
      <div class="panel">{structure_html}</div>
      <div class="panel">{eq_html}</div>
      <div class="panel">{rz_html}</div>
    </div>
  </details>
  <footer class="atmospheric-footer">
    <span>Orren Engine v{__version__}</span>
    <span>{len(graph.nodes)} nodes · {len(graph.equilibrium_rules)} eq rules · {len(artifacts)} targets</span>
  </footer>
</div>"""


def _build_atmospheric_canvas(graph, tokens) -> str:
    """Render entities as floating organic shapes."""
    if graph.root is None:
        return "<p class='empty'>No entities</p>"

    cards = []
    for node in graph.nodes:
        if node.kind == "root":
            continue
        if not _has_visual_content(node):
            continue
        cards.append(_render_atmospheric_card(node, tokens))

    if not cards:
        return ""

    return f"<div class='atmosphere-grid'>{''.join(cards)}</div>"


def _render_atmospheric_card(node: SIRNode, tokens: DesignTokens) -> str:
    """Render an entity as a floating orb with vibe glow."""
    vibes = node.get_dimension(Dimension.VIBE)
    color = tokens.accent
    label = html.escape(node.name.replace("_", " ").title())
    path_short = html.escape(node.path.split(".")[-1])

    for v in vibes:
        if isinstance(v, dict) and v.get("aspect") == "color_character":
            color = _resolve_card_color(v.get("term", ""), tokens)

    # Equilibrium badges (subtle)
    eq_count = sum(1 for _ in node.get_dimension(Dimension.EQUILIBRIUM))
    eq_badge = f"<span class='atm-eq'>{eq_count}</span>" if eq_count else ""

    return f"""
<div class="atmosphere-card drift" style="--card-glow: {color};">
  <div class="atm-orb" style="background: radial-gradient(circle, {color} 0%, transparent 70%);"></div>
  <div class="atm-label">{label}</div>
  <div class="atm-path">{path_short}</div>
  {eq_badge}
</div>"""


# ---------------------------------------------------------------------------
# Layout: Schematic (technical — devices, robots)
# ---------------------------------------------------------------------------


def _render_schematic_layout(graph, artifacts, tokens, app_name, purpose, vibe_brief) -> str:
    """A technical schematic layout — component diagram style."""
    header = _render_header(app_name, purpose, vibe_brief, graph, artifacts, tokens)
    schematic_html = _build_schematic(graph, tokens)
    eq_html = _build_equilibrium_panel(graph, tokens)
    rz_html = _build_realization_panel(graph, artifacts, tokens)
    structure_html = _build_structure_tree(graph, tokens)

    return f"""
{header}
<main class="layout-schematic">
  <section class="schematic-canvas">
    <h2>Component Diagram</h2>
    {schematic_html}
  </section>
  <aside class="schematic-info">
    <div class="panel">{structure_html}</div>
    {eq_html}
    {rz_html}
  </aside>
</main>
<footer class="dash-footer">
  <span>Orren Engine v{__version__}</span>
  <span>{len(graph.nodes)} components · {len(graph.equilibrium_rules)} safety rules · {len(artifacts)} targets</span>
</footer>"""


def _build_schematic(graph, tokens) -> str:
    """Render the structure as a component diagram."""
    if graph.root is None:
        return "<p class='empty'>No components</p>"

    parts = []
    for child in graph.root.children:
        parts.append(_render_schematic_node(child, tokens, 0))

    return f"<div class='schematic-tree'>{''.join(parts)}</div>"


def _render_schematic_node(node: SIRNode, tokens: DesignTokens, depth: int) -> str:
    """Render a node as a schematic component block."""
    label = html.escape(node.name.replace("_", " "))
    path_short = html.escape(node.path.split(".")[-1])

    # Get cognitive content for component description
    cog_items = []
    for cog in node.get_dimension(Dimension.COGNITIVE):
        if isinstance(cog, dict):
            pred = html.escape(str(cog.get("predicate", "")).replace("_", " "))
            val = html.escape(str(cog.get("value", "")))
            cog_items.append(f"<div class='sch-cog'><span class='sch-cog-pred'>{pred}</span>: <span class='sch-cog-val'>{val}</span></div>")

    # Get behavioral content
    beh_items = []
    for beh in node.get_dimension(Dimension.BEHAVIORAL):
        if isinstance(beh, dict):
            kind = beh.get("kind", "")
            if kind == "lifecycle":
                chain = beh.get("lifecycle", [])
                if chain:
                    states = " → ".join(
                        t.get("to_state", "") for t in chain
                    )
                    beh_items.append(f"<div class='sch-beh'>lifecycle: {html.escape(states)}</div>")
            elif kind == "transitions":
                beh_items.append(
                    f"<div class='sch-beh'>{html.escape(beh.get('from_state', ''))} → {html.escape(beh.get('to_state', ''))} on {html.escape(beh.get('on_event', ''))}</div>"
                )

    children_html = ""
    if node.children:
        children_html = "<div class='sch-children'>" + "".join(
            _render_schematic_node(c, tokens, depth + 1) for c in node.children
        ) + "</div>"

    # Safety/critical marker
    safety_marker = ""
    name_lower = node.name.lower()
    if any(w in name_lower for w in ("safety", "emergency", "alarm", "alarm", "failover")):
        safety_marker = "<span class='sch-safety'>SAFETY</span>"
    elif any(w in name_lower for w in ("sensor", "detector", "monitor")):
        safety_marker = "<span class='sch-sensor'>SENSOR</span>"
    elif any(w in name_lower for w in ("actuator", "motor", "valve", "heater", "ventilator")):
        safety_marker = "<span class='sch-actuator'>ACTUATOR</span>"

    return f"""
<div class="sch-component" data-depth="{depth}">
  <div class="sch-header">
    <span class="sch-name">{label}</span>
    {safety_marker}
    <span class="sch-path">{path_short}</span>
  </div>
  {f"<div class='sch-details'>{''.join(cog_items)}{''.join(beh_items)}</div>" if (cog_items or beh_items) else ''}
  {children_html}
</div>"""


# ---------------------------------------------------------------------------
# Shared section builders
# ---------------------------------------------------------------------------


def _render_header(app_name, purpose, vibe_brief, graph, artifacts, tokens) -> str:
    avg_score = (
        sum(a.preservation_score for a in artifacts) / len(artifacts)
        if artifacts else 0.0
    )
    title = html.escape(app_name.replace("_", " ").title())
    mood_label = tokens.mood.title()
    layout_label = tokens.layout_strategy.title()

    return f"""
<header class="app-header" style="border-bottom-color: var(--accent);">
  <div class="header-content">
    <h1>{title}</h1>
    {f'<p class="purpose">{html.escape(purpose)}</p>' if purpose else ''}
    {f'<p class="vibe-brief">Vibe: <em>{html.escape(vibe_brief)}</em></p>' if vibe_brief else ''}
    <div class="meta-row">
      <span class="badge badge-info">{len(graph.nodes)} entities</span>
      <span class="badge badge-info">{len(graph.equilibrium_rules)} eq rules</span>
      <span class="badge badge-info">{len(artifacts)} targets</span>
      <span class="badge badge-mood">{mood_label}</span>
      <span class="badge badge-layout">{layout_label}</span>
      <span class="badge badge-score">avg preservation: {avg_score:.2f}</span>
    </div>
  </div>
</header>"""


def _has_visual_content(node: SIRNode) -> bool:
    return (
        node.has_dimension_content(Dimension.VIBE)
        or node.has_dimension_content(Dimension.SPATIAL)
        or node.has_dimension_content(Dimension.COGNITIVE)
        or node.has_dimension_content(Dimension.CONDITIONAL)
        or node.has_dimension_content(Dimension.BEHAVIORAL)
    )


def _resolve_card_color(term: str, tokens: DesignTokens) -> str:
    """Resolve a vibe color term — fall back to the design token accent."""
    from .design_tokens import PALETTES
    term_lower = term.lower().replace(" ", "_")
    if term_lower in PALETTES:
        return PALETTES[term_lower]["accent"]
    for key, val in PALETTES.items():
        if key in term_lower or term_lower in key:
            return val["accent"]
    return tokens.accent


def _build_structure_tree(graph, tokens) -> str:
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


def _build_canvas(graph, tokens) -> str:
    if graph.root is None:
        return "<p class='empty'>No entities to display</p>"

    cards = []
    for node in graph.nodes:
        if node.kind == "root":
            continue
        if not _has_visual_content(node):
            continue
        cards.append(_render_entity_card(node, tokens))

    if not cards:
        return "<p class='empty'>No visual entities</p>"

    return f"<div class='canvas-grid'>{''.join(cards)}</div>"


def _render_entity_card(node: SIRNode, tokens: DesignTokens) -> str:
    vibes = node.get_dimension(Dimension.VIBE)
    color = tokens.panel_bg
    radius = tokens.card_radius

    for v in vibes:
        if isinstance(v, dict):
            aspect = v.get("aspect", "")
            term = v.get("term", "")
            if aspect == "color_character":
                color = _resolve_card_color(term, tokens)
            elif aspect == "form_character":
                # Override radius based on form
                form_lower = str(term).lower()
                if "organic" in form_lower:
                    radius = "24px"
                elif "rounded" in form_lower:
                    radius = "16px"

    label = html.escape(node.name.replace("_", " ").title())
    path_short = html.escape(node.path.split(".")[-1])

    dim_badges = []
    for dim in Dimension.semantic():
        if node.has_dimension_content(dim):
            count = len(node.get_dimension(dim))
            dim_badges.append(
                f"<span class='dim-badge dim-{dim.value}' title='{dim.value}: {count} entries'>{dim.value[0].upper()}{count}</span>"
            )

    eq_badges = []
    for eq in node.get_dimension(Dimension.EQUILIBRIUM):
        if isinstance(eq, dict):
            rule_name = eq.get("rule", "")
            eq_badges.append(f"<span class='eq-badge' title='{html.escape(str(eq))}'>⚖ {html.escape(rule_name)}</span>")

    deg_badges = []
    for key, entry in node.degradation_tolerance.items():
        if entry.level in (ToleranceLevel.PROXY, ToleranceLevel.DOCUMENTED, ToleranceLevel.OPTIONAL):
            deg_badges.append(
                f"<span class='deg-badge deg-{entry.level.value}' title='{html.escape(key)}'>{entry.level.value}</span>"
            )

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

    return f"""
<div class="entity-card" style="{style}" data-path="{html.escape(node.path)}">
  <div class="card-header">
    <span class="card-label">{label}</span>
    <span class="card-path">{path_short}</span>
  </div>
  <div class="card-badges">{''.join(dim_badges)}</div>
  {f'<div class="card-vibes">{" ".join(eq_badges)} {" ".join(deg_badges)}</div>' if (eq_badges or deg_badges) else ''}
  {vibe_details}
  <button class="expand-btn" onclick="this.parentElement.querySelector('.vibe-details').hidden = !this.parentElement.querySelector('.vibe-details').hidden">details</button>
</div>"""


def _build_equilibrium_panel(graph, tokens) -> str:
    if not graph.equilibrium_rules:
        return "<div class='sub-panel'><h3>Equilibrium</h3><p class='empty'>No rules declared</p></div>"

    items = []
    for rule in graph.equilibrium_rules:
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


def _render_equilibrium_compact(graph, tokens) -> str:
    """Compact equilibrium view for document layout."""
    if not graph.equilibrium_rules:
        return ""
    items = []
    for rule in graph.equilibrium_rules:
        resolution = rule.resolution.text if rule.resolution else "—"
        items.append(f"<div class='doc-eq'><strong>{html.escape(rule.name)}:</strong> {html.escape(resolution)}</div>")
    return f"<div class='doc-eq-panel'><h3>Equilibrium Resolutions</h3>{''.join(items)}</div>"


def _build_realization_panel(graph, artifacts, tokens) -> str:
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
</div>""")

    return f"""
<div class="sub-panel">
  <h3>Realization ({len(artifacts)} targets)</h3>
  {''.join(items)}
</div>"""


def _render_realization_compact(graph, artifacts, tokens) -> str:
    """Compact realization view for document layout."""
    if not artifacts:
        return ""
    items = []
    for art in artifacts:
        items.append(
            f"<div class='doc-rz'><strong>{html.escape(art.target_name)}</strong> ({html.escape(art.target_language)}) — preservation {art.preservation_score:.2f}</div>"
        )
    return f"<div class='doc-rz-panel'><h3>Realization Targets</h3>{''.join(items)}</div>"


def _build_degradation_panel(graph, artifacts, tokens) -> str:
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
        for e in proxy_entries[:15]:
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
# CSS — base + per-layout
# ---------------------------------------------------------------------------


_BASE_CSS = """
a { color: var(--accent); text-decoration: none; }
h1, h2, h3, h4 { font-family: var(--heading-font); font-weight: var(--heading-weight); }
.badge { display: inline-block; padding: 4px 10px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 500; }
.badge-info { background: rgba(255,255,255,0.08); color: var(--muted); border: 1px solid var(--panel-border); }
.badge-mood { background: rgba(255,255,255,0.12); color: var(--fg); border: 1px solid var(--accent); }
.badge-layout { background: rgba(255,255,255,0.06); color: var(--muted); border: 1px dashed var(--panel-border); }
.badge-score { background: rgba(16, 185, 129, 0.15); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.3); }
.panel { background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: var(--panel-radius); padding: 16px; overflow-y: auto; }
.panel h2 { font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid var(--panel-border); }
.panel .hint { font-size: 12px; color: var(--muted); margin-bottom: 16px; }
.sub-panel { background: rgba(0,0,0,0.15); border: 1px solid var(--panel-border); border-radius: var(--radius-md); padding: 12px; margin-bottom: 16px; }
.sub-panel h3 { font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 10px; }
.empty { color: var(--muted); font-style: italic; font-size: 12px; }
.tree { list-style: none; font-size: 13px; }
.tree ul { list-style: none; padding-left: 16px; border-left: 1px solid var(--panel-border); margin-left: 4px; }
.tree li { padding: 4px 0; }
.entity-label { color: var(--fg); cursor: pointer; transition: color var(--motion-duration) var(--motion-easing); }
.entity-label:hover { color: var(--accent); }
.kind { font-size: 11px; color: var(--muted); background: rgba(255,255,255,0.08); padding: 1px 6px; border-radius: var(--radius-sm); margin-left: 4px; }
.dim-count { font-size: 11px; color: var(--accent); margin-left: 4px; }
.canvas-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 12px; align-content: start; }
.entity-card { padding: 14px; border: 1px solid rgba(255,255,255,0.15); box-shadow: 0 4px 12px rgba(0,0,0,0.2); min-height: 100px; display: flex; flex-direction: column; gap: 8px; transition: transform var(--motion-duration) var(--motion-easing), box-shadow var(--motion-duration) var(--motion-easing); color: #fff; text-shadow: 0 1px 2px rgba(0,0,0,0.5); }
.entity-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
.card-header { display: flex; justify-content: space-between; align-items: baseline; }
.card-label { font-size: 15px; font-weight: var(--heading-weight); }
.card-path { font-size: 11px; opacity: 0.7; font-family: var(--mono-font); }
.card-badges { display: flex; gap: 4px; flex-wrap: wrap; }
.dim-badge { font-size: 10px; padding: 2px 6px; border-radius: var(--radius-sm); background: rgba(0,0,0,0.4); font-weight: 600; }
.card-vibes { display: flex; gap: 4px; flex-wrap: wrap; font-size: 10px; }
.eq-badge { background: rgba(245, 158, 11, 0.3); color: #fbbf24; padding: 2px 6px; border-radius: var(--radius-sm); }
.deg-badge { background: rgba(239, 68, 68, 0.3); color: #fca5a5; padding: 2px 6px; border-radius: var(--radius-sm); text-transform: uppercase; font-weight: 600; }
.vibe-details { font-size: 11px; border-top: 1px solid rgba(255,255,255,0.2); padding-top: 8px; margin-top: 4px; }
.vibe-item { display: flex; justify-content: space-between; padding: 2px 0; }
.vibe-aspect { opacity: 0.8; }
.vibe-term { font-weight: 500; }
.expand-btn { align-self: flex-start; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2); color: #fff; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 11px; cursor: pointer; margin-top: auto; }
.eq-item { padding: 8px; margin-bottom: 8px; border-radius: var(--radius-sm); border-left: 3px solid; background: rgba(0,0,0,0.2); }
.eq-item.eq-fired { border-color: #10b981; }
.eq-item.eq-not-fired { border-color: var(--muted); opacity: 0.6; }
.eq-name { font-weight: var(--heading-weight); font-size: 13px; margin-bottom: 4px; }
.eq-status { font-size: 11px; text-transform: uppercase; color: var(--muted); margin-bottom: 4px; }
.eq-detail { font-size: 11px; color: var(--muted); margin-top: 2px; }
.rz-item { padding: 8px; margin-bottom: 8px; border-radius: var(--radius-sm); background: rgba(0,0,0,0.2); border-left: 3px solid var(--accent); }
.rz-name { font-weight: var(--heading-weight); font-size: 13px; }
.rz-lang { font-size: 11px; color: var(--muted); font-family: var(--mono-font); }
.rz-score { display: inline-block; padding: 2px 8px; border-radius: var(--radius-sm); font-size: 12px; font-weight: 600; margin: 4px 0; }
.score-high { background: rgba(16, 185, 129, 0.3); color: #6ee7b7; }
.score-mid { background: rgba(245, 158, 11, 0.3); color: #fbbf24; }
.score-low { background: rgba(239, 68, 68, 0.3); color: #fca5a5; }
.rz-detail { font-size: 11px; color: var(--muted); margin-top: 2px; }
.deg-summary { font-size: 11px; color: var(--muted); margin-bottom: 10px; padding: 6px; background: rgba(0,0,0,0.2); border-radius: var(--radius-sm); text-align: center; font-family: var(--mono-font); }
.deg-group { margin-bottom: 12px; }
.deg-group h4 { font-size: 12px; color: var(--muted); margin-bottom: 6px; }
.deg-row { display: flex; gap: 6px; align-items: center; padding: 3px 0; font-size: 11px; border-bottom: 1px solid rgba(255,255,255,0.05); }
.deg-aspect { flex: 1; color: var(--fg); }
.deg-level { font-size: 10px; padding: 1px 5px; border-radius: var(--radius-sm); text-transform: uppercase; font-weight: 600; }
.deg-level.deg-proxy { background: rgba(239,68,68,0.3); color: #fca5a5; }
.deg-level.deg-documented { background: rgba(168,85,247,0.3); color: #c4b5fd; }
.deg-level.deg-optional { background: rgba(100,116,139,0.3); color: #cbd5e1; }
.deg-source { font-size: 10px; padding: 1px 5px; border-radius: var(--radius-sm); background: rgba(139,92,246,0.3); color: #c4b5fd; text-transform: uppercase; font-weight: 600; }
.deg-node { font-family: var(--mono-font); font-size: 10px; color: var(--muted); }
details summary { cursor: pointer; padding: 12px; background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: var(--radius-md); color: var(--muted); font-size: 13px; }
details summary:hover { color: var(--fg); }
"""


_LAYOUT_CSS_DASHBOARD = """
.app-header { padding: 24px 32px; border-bottom: 2px solid var(--panel-border); background: linear-gradient(180deg, var(--panel-bg), transparent); }
.app-header h1 { font-size: 28px; margin-bottom: 8px; }
.app-header .purpose { color: var(--muted); font-size: 15px; margin-bottom: 4px; max-width: 80ch; }
.app-header .vibe-brief { color: var(--accent); font-size: 13px; margin-bottom: 12px; }
.meta-row { display: flex; gap: 8px; flex-wrap: wrap; }
.layout-dashboard { display: grid; grid-template-columns: 280px 1fr 360px; gap: 16px; padding: 16px; min-height: calc(100vh - 200px); }
.layout-dashboard .panel { max-height: calc(100vh - 120px); }
.dash-footer { padding: 12px 32px; border-top: 1px solid var(--panel-border); display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); }
@media (max-width: 1024px) { .layout-dashboard { grid-template-columns: 1fr; } }
"""


_LAYOUT_CSS_APP = """
.app-header { padding: 32px; border-bottom: 2px solid var(--panel-border); text-align: center; }
.app-header h1 { font-size: 32px; margin-bottom: 8px; }
.app-header .purpose { color: var(--muted); font-size: 16px; max-width: 60ch; margin: 0 auto 4px; }
.app-header .vibe-brief { color: var(--accent); font-size: 14px; margin-bottom: 12px; }
.meta-row { display: flex; gap: 8px; flex-wrap: wrap; justify-content: center; }
.layout-app { max-width: var(--content-max-width); margin: 0 auto; padding: 32px; }
.app-canvas { margin-bottom: 24px; }
.app-panels { margin-top: 24px; }
.app-panels-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; margin-top: 16px; }
.app-panels-grid .panel { background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: var(--panel-radius); padding: 16px; }
.dash-footer { padding: 12px 32px; border-top: 1px solid var(--panel-border); text-align: center; font-size: 11px; color: var(--muted); }
"""


_LAYOUT_CSS_ATMOSPHERIC = """
.atmospheric-scene { min-height: 100vh; position: relative; overflow: hidden; padding: 0; }
.atmospheric-vignette { position: absolute; inset: 0; pointer-events: none; box-shadow: inset 0 0 200px rgba(0,0,0,0.6); }
.atmospheric-header { text-align: center; padding: 80px 32px 40px; position: relative; z-index: 2; }
.atmospheric-header h1 { font-size: 36px; margin-bottom: 12px; font-weight: var(--heading-weight); }
.atmospheric-purpose { color: var(--muted); font-size: 16px; max-width: 60ch; margin: 0 auto 8px; line-height: 1.7; }
.atmospheric-vibe { color: var(--accent); font-size: 14px; font-style: italic; }
.atmospheric-meta { display: flex; gap: 16px; justify-content: center; margin-top: 16px; font-size: 12px; color: var(--muted); font-family: var(--mono-font); }
.atmospheric-meta span { padding: 4px 10px; border: 1px solid var(--panel-border); border-radius: var(--radius-sm); background: rgba(0,0,0,0.2); }
.atmospheric-canvas { padding: 0 32px 60px; position: relative; z-index: 2; }
.atmosphere-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 32px; max-width: 1000px; margin: 0 auto; }
.atmosphere-card { display: flex; flex-direction: column; align-items: center; padding: 24px; text-align: center; position: relative; min-height: 140px; }
.atm-orb { width: 80px; height: 80px; border-radius: 50%; margin-bottom: 12px; filter: blur(8px); opacity: 0.7; }
.atm-label { font-size: 13px; color: var(--fg); margin-bottom: 4px; }
.atm-path { font-size: 10px; color: var(--muted); font-family: var(--mono-font); }
.atm-eq { position: absolute; top: 8px; right: 8px; font-size: 10px; padding: 2px 6px; border-radius: var(--radius-sm); background: rgba(245,158,11,0.3); color: #fbbf24; }
.wisdom-panel { max-width: 700px; margin: 0 auto 60px; padding: 0 32px; position: relative; z-index: 2; }
.wisdom-item { font-size: 15px; color: var(--muted); text-align: center; margin-bottom: 12px; font-style: italic; line-height: 1.7; }
.atmospheric-details { max-width: 1000px; margin: 0 auto 60px; padding: 0 32px; position: relative; z-index: 2; }
.atmospheric-panels { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-top: 16px; }
.atmospheric-panels .panel { background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: var(--panel-radius); padding: 16px; }
.atmospheric-footer { text-align: center; padding: 24px 32px; border-top: 1px solid var(--panel-border); position: relative; z-index: 2; font-size: 11px; color: var(--muted); display: flex; justify-content: space-between; max-width: 1000px; margin: 0 auto; }
"""


_LAYOUT_CSS_SCHEMATIC = """
.app-header { padding: 24px 32px; border-bottom: 2px solid var(--panel-border); background: linear-gradient(180deg, var(--panel-bg), transparent); }
.app-header h1 { font-size: 26px; margin-bottom: 8px; font-family: var(--mono-font); }
.app-header .purpose { color: var(--muted); font-size: 14px; margin-bottom: 4px; max-width: 80ch; font-family: var(--mono-font); }
.app-header .vibe-brief { color: var(--accent); font-size: 12px; margin-bottom: 12px; font-family: var(--mono-font); }
.meta-row { display: flex; gap: 8px; flex-wrap: wrap; }
.layout-schematic { display: grid; grid-template-columns: 1fr 360px; gap: 16px; padding: 16px; min-height: calc(100vh - 200px); }
.schematic-canvas { background: var(--panel-bg); border: 1px solid var(--panel-border); border-radius: var(--panel-radius); padding: 20px; overflow-x: auto; }
.schematic-canvas h2 { font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 16px; font-family: var(--mono-font); }
.schematic-tree { font-family: var(--mono-font); font-size: 12px; }
.sch-component { border: 1px solid var(--panel-border); border-radius: var(--radius-sm); padding: 10px; margin-bottom: 10px; background: rgba(0,0,0,0.2); }
.sch-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.sch-name { font-weight: var(--heading-weight); color: var(--fg); }
.sch-path { color: var(--muted); font-size: 10px; margin-left: auto; }
.sch-safety { background: rgba(239,68,68,0.3); color: #fca5a5; padding: 1px 6px; border-radius: var(--radius-sm); font-size: 9px; font-weight: 700; }
.sch-sensor { background: rgba(59,130,246,0.3); color: #93c5fd; padding: 1px 6px; border-radius: var(--radius-sm); font-size: 9px; font-weight: 700; }
.sch-actuator { background: rgba(16,185,129,0.3); color: #6ee7b7; padding: 1px 6px; border-radius: var(--radius-sm); font-size: 9px; font-weight: 700; }
.sch-details { font-size: 11px; color: var(--muted); padding-left: 8px; border-left: 2px solid var(--panel-border); }
.sch-cog { padding: 2px 0; }
.sch-cog-pred { color: var(--accent); }
.sch-cog-val { color: var(--fg); }
.sch-beh { padding: 2px 0; color: var(--muted); }
.sch-children { margin-left: 16px; margin-top: 8px; padding-left: 12px; border-left: 1px dashed var(--panel-border); }
.schematic-info { max-height: calc(100vh - 120px); overflow-y: auto; }
.dash-footer { padding: 12px 32px; border-top: 1px solid var(--panel-border); display: flex; justify-content: space-between; font-size: 11px; color: var(--muted); font-family: var(--mono-font); }
@media (max-width: 1024px) { .layout-schematic { grid-template-columns: 1fr; } }
"""


_LAYOUT_CSS_DOCUMENT = """
.document-page { max-width: 900px; margin: 40px auto; padding: 60px 80px; background: var(--panel-bg); border: 1px solid var(--panel-border); box-shadow: 0 8px 32px rgba(0,0,0,0.2); }
.doc-header { text-align: center; margin-bottom: 48px; padding-bottom: 24px; border-bottom: 2px solid var(--fg); }
.doc-header h1 { font-size: 32px; margin-bottom: 12px; }
.doc-purpose { color: var(--muted); font-size: 15px; margin-bottom: 4px; font-style: italic; }
.doc-vibe { color: var(--accent); font-size: 13px; }
.doc-body { font-size: var(--body-size); line-height: 1.8; }
.doc-body section { margin-bottom: 32px; }
.doc-body h2 { font-size: 22px; margin-bottom: 12px; padding-bottom: 6px; border-bottom: 1px solid var(--panel-border); }
.doc-body h3 { font-size: 18px; margin: 20px 0 8px; color: var(--fg); }
.doc-body h4 { font-size: 16px; margin: 16px 0 6px; color: var(--accent); }
.doc-body p { margin-bottom: 12px; text-align: justify; }
.doc-body ul { margin: 8px 0 12px 24px; }
.doc-body li { margin-bottom: 4px; }
.doc-body strong { color: var(--accent); }
.doc-aside { margin-top: 48px; padding-top: 24px; border-top: 1px solid var(--panel-border); }
.doc-eq-panel, .doc-rz-panel { margin-bottom: 24px; }
.doc-eq-panel h3, .doc-rz-panel h3 { font-size: 14px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--muted); margin-bottom: 12px; }
.doc-eq, .doc-rz { font-size: 13px; margin-bottom: 8px; padding: 8px; background: rgba(0,0,0,0.05); border-radius: var(--radius-sm); }
.doc-footer { text-align: center; padding: 24px 0 0; border-top: 1px solid var(--panel-border); margin-top: 32px; font-size: 11px; color: var(--muted); }
"""


# ---------------------------------------------------------------------------
# JS
# ---------------------------------------------------------------------------


def _build_js(tokens: DesignTokens) -> str:
    return """
document.querySelectorAll('.entity-label').forEach(el => {
  el.addEventListener('click', () => {
    const path = el.dataset.path;
    const card = document.querySelector(`.entity-card[data-path="${path}"], .atmosphere-card[data-path="${path}"], .sch-component[data-path="${path}"]`);
    if (card) {
      card.scrollIntoView({behavior: 'smooth', block: 'center'});
      card.style.outline = '3px solid var(--accent)';
      setTimeout(() => card.style.outline = '', 1500);
    }
  });
});
"""


__all__ = ["generate_preview", "write_preview"]
