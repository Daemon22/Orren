"""
Orren Engine — Design Token System
===================================

Maps the vibe dimensions of a SIR graph to a complete set of design
tokens that drive the preview's visual identity.

This is what makes a meditation app look like a meditation app, a
contract look like a contract, and a children's story look like a
children's story — instead of every preview getting the same dark
dashboard.

Tokens produced:
    palette:    bg, fg, accent, panel_bg, panel_border, muted, highlight
    typography: heading_font, body_font, mono_font, heading_weight,
                body_size, line_height, letter_spacing
    shape:      radius_scale (sm/md/lg), card_radius, panel_radius
    spacing:    scale (tight/normal/generous), density
    motion:     duration_base, easing, breathing_animation (bool),
                texture (none/gradient/grain/vignette)
    layout:     strategy (document/dashboard/app/atmospheric/schematic)

The mapping is intentionally opinionated. A vibe of "warm_blue" with
aesthetic "floating in warm water" produces a soft, aqueous palette
with breathing animation and generous whitespace — not a generic dark
theme with a blue accent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .data_model import Dimension, SIRGraph, SIRNode


# ---------------------------------------------------------------------------
# Design token dataclass
# ---------------------------------------------------------------------------


@dataclass
class DesignTokens:
    """Complete visual identity for one preview."""

    # Palette
    bg: str = "#0f172a"
    bg_gradient: Optional[str] = None
    fg: str = "#e2e8f0"
    accent: str = "#3b82f6"
    accent_secondary: Optional[str] = None
    panel_bg: str = "#1e293b"
    panel_border: str = "#334155"
    muted: str = "#94a3b8"
    highlight: str = "#fbbf24"

    # Typography
    heading_font: str = (
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    )
    body_font: str = (
        "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
    )
    mono_font: str = "'SF Mono', 'Cascadia Code', Menlo, Consolas, monospace"
    heading_weight: int = 700
    body_weight: int = 400
    body_size: str = "14px"
    line_height: str = "1.5"
    letter_spacing: str = "0"

    # Shape
    radius_sm: str = "4px"
    radius_md: str = "8px"
    radius_lg: str = "16px"
    card_radius: str = "8px"
    panel_radius: str = "12px"

    # Spacing
    spacing_unit: str = "16px"
    spacing_scale: str = "normal"  # tight/normal/generous/expansive
    content_max_width: str = "1200px"

    # Motion
    motion_duration: str = "200ms"
    motion_easing: str = "ease"
    breathing_animation: bool = False
    hover_lift: bool = True

    # Texture
    texture: str = "none"  # none/gradient/grain/vignette/watermark/noise
    texture_opacity: float = 0.0

    # Layout
    layout_strategy: str = "dashboard"  # document/dashboard/app/atmospheric/schematic

    # Mood
    mood: str = "neutral"  # neutral/warm/cool/serious/playful/atmospheric/technical

    def to_css_vars(self) -> str:
        """Render as CSS custom properties."""
        lines = [
            f"  --bg: {self.bg};",
            f"  --fg: {self.fg};",
            f"  --accent: {self.accent};",
            f"  --panel-bg: {self.panel_bg};",
            f"  --panel-border: {self.panel_border};",
            f"  --muted: {self.muted};",
            f"  --highlight: {self.highlight};",
            f"  --heading-font: {self.heading_font};",
            f"  --body-font: {self.body_font};",
            f"  --mono-font: {self.mono_font};",
            f"  --heading-weight: {self.heading_weight};",
            f"  --body-size: {self.body_size};",
            f"  --line-height: {self.line_height};",
            f"  --letter-spacing: {self.letter_spacing};",
            f"  --radius-sm: {self.radius_sm};",
            f"  --radius-md: {self.radius_md};",
            f"  --radius-lg: {self.radius_lg};",
            f"  --card-radius: {self.card_radius};",
            f"  --panel-radius: {self.panel_radius};",
            f"  --spacing-unit: {self.spacing_unit};",
            f"  --motion-duration: {self.motion_duration};",
            f"  --motion-easing: {self.motion_easing};",
        ]
        if self.bg_gradient:
            lines.append(f"  --bg-gradient: {self.bg_gradient};")
        if self.accent_secondary:
            lines.append(f"  --accent-secondary: {self.accent_secondary};")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Vibe term → palette mapping
# ---------------------------------------------------------------------------

# Each entry returns a FULL palette, not just one color.
# This is what makes "warm_blue" produce a different visual world from
# "deep_blue_with_amber_lamp" — they share blue but the accent, panel_bg,
# and mood differ.

PALETTES: Dict[str, Dict[str, str]] = {
    # Greens — calm agricultural
    "emerald": {
        "bg": "#0a1f1a", "fg": "#d1fae5", "accent": "#10b981",
        "panel_bg": "#0f2a23", "panel_border": "#1f4d3f", "muted": "#6ee7b7",
        "highlight": "#fbbf24", "mood": "cool",
    },
    "green": {
        "bg": "#0a1f1a", "fg": "#d1fae5", "accent": "#22c55e",
        "panel_bg": "#0f2a23", "panel_border": "#1f4d3f", "muted": "#86efac",
        "highlight": "#fbbf24", "mood": "cool",
    },
    "warm_green": {
        "bg": "#1a2e1a", "fg": "#dcfce7", "accent": "#4ade80",
        "panel_bg": "#1e3a2b", "panel_border": "#2d5a3d", "muted": "#86efac",
        "highlight": "#fde047", "mood": "warm",
    },
    "trust_green": {
        "bg": "#0f1f1a", "fg": "#d1fae5", "accent": "#16a34a",
        "panel_bg": "#15291f", "panel_border": "#1f4d3f", "muted": "#6ee7b7",
        "highlight": "#84cc16", "mood": "serious",
    },
    # Ambers — warm inviting
    "warm_amber": {
        "bg": "#1a1208", "fg": "#fef3c7", "accent": "#f59e0b",
        "panel_bg": "#241a0e", "panel_border": "#3f2f1a", "muted": "#fcd34d",
        "highlight": "#fbbf24", "mood": "warm",
    },
    "amber": {
        "bg": "#1a1208", "fg": "#fef3c7", "accent": "#f59e0b",
        "panel_bg": "#241a0e", "panel_border": "#3f2f1a", "muted": "#fcd34d",
        "highlight": "#fde047", "mood": "warm",
    },
    "amber_glow": {
        "bg": "#1a1208", "fg": "#fef3c7", "accent": "#f59e0b",
        "panel_bg": "#241a0e", "panel_border": "#3f2f1a", "muted": "#fcd34d",
        "highlight": "#fbbf24", "mood": "warm",
    },
    "soft_amber": {
        "bg": "#1f1810", "fg": "#fef3c7", "accent": "#f4a261",
        "panel_bg": "#2a2018", "panel_border": "#3f2f1a", "muted": "#fcd34d",
        "highlight": "#fbbf24", "mood": "warm",
    },
    "amber_to_cream": {
        "bg": "linear-gradient(135deg, #1a1208 0%, #2a1f10 100%)",
        "fg": "#fef3c7", "accent": "#f59e0b",
        "panel_bg": "#241a0e", "panel_border": "#3f2f1a", "muted": "#fcd34d",
        "highlight": "#fde047", "mood": "warm",
    },
    "amber_alert": {
        "bg": "#1a0a08", "fg": "#fef3c7", "accent": "#f59e0b",
        "panel_bg": "#241008", "panel_border": "#3f1f1a", "muted": "#fcd34d",
        "highlight": "#ef4444", "mood": "serious",
    },
    # Blues — calm technical
    "warm_blue": {
        "bg": "linear-gradient(180deg, #0a1828 0%, #0f2438 50%, #0a1828 100%)",
        "fg": "#dbeafe", "accent": "#3a86b0",
        "panel_bg": "#0f2438", "panel_border": "#1f3a5a", "muted": "#93c5fd",
        "highlight": "#fbbf24", "mood": "cool",
    },
    "deep_blue": {
        "bg": "#0a0f1f", "fg": "#dbeafe", "accent": "#1e3a5f",
        "panel_bg": "#0f1a2e", "panel_border": "#1f2f4d", "muted": "#93c5fd",
        "highlight": "#fbbf24", "mood": "atmospheric",
    },
    "deep_blue_with_amber_lamp": {
        "bg": "linear-gradient(180deg, #050a14 0%, #0a1224 50%, #050a14 100%)",
        "fg": "#dbeafe", "accent": "#f59e0b",
        "panel_bg": "#0a1224", "panel_border": "#1f2f4d", "muted": "#64748b",
        "highlight": "#fbbf24", "mood": "atmospheric",
    },
    "blue": {
        "bg": "#0a1828", "fg": "#dbeafe", "accent": "#3b82f6",
        "panel_bg": "#0f2438", "panel_border": "#1f3a5a", "muted": "#93c5fd",
        "highlight": "#fbbf24", "mood": "cool",
    },
    "cold_blue": {
        "bg": "#0a1424", "fg": "#dbeafe", "accent": "#4a6fa5",
        "panel_bg": "#0f1f3a", "panel_border": "#1f2f4d", "muted": "#7dd3fc",
        "highlight": "#e0f2fe", "mood": "cool",
    },
    "neutral_blue": {
        "bg": "#0f1824", "fg": "#dbeafe", "accent": "#5b8fb9",
        "panel_bg": "#1a2438", "panel_border": "#2a384d", "muted": "#93c5fd",
        "highlight": "#fbbf24", "mood": "serious",
    },
    "positional_blue": {
        "bg": "#0a1424", "fg": "#dbeafe", "accent": "#4a90d9",
        "panel_bg": "#0f1f3a", "panel_border": "#1f2f4d", "muted": "#7dd3fc",
        "highlight": "#fbbf24", "mood": "technical",
    },
    "slate_blue": {
        "bg": "#1a1f2e", "fg": "#cbd5e1", "accent": "#4a5568",
        "panel_bg": "#242a3a", "panel_border": "#3a4154", "muted": "#94a3b8",
        "highlight": "#f59e0b", "mood": "serious",
    },
    "slate_grey_with_amber_warmth": {
        "bg": "#1a1f2e", "fg": "#cbd5e1", "accent": "#475569",
        "panel_bg": "#242a3a", "panel_border": "#3a4154", "muted": "#94a3b8",
        "highlight": "#f59e0b", "accent_secondary": "#f59e0b",
        "mood": "atmospheric",
    },
    "slate_grey": {
        "bg": "#1a1f2e", "fg": "#cbd5e1", "accent": "#64748b",
        "panel_bg": "#242a3a", "panel_border": "#3a4154", "muted": "#94a3b8",
        "highlight": "#f59e0b", "mood": "serious",
    },
    "neutral_grey": {
        "bg": "#ffffff", "fg": "#1f2937", "accent": "#374151",
        "panel_bg": "#f9fafb", "panel_border": "#e5e7eb", "muted": "#6b7280",
        "highlight": "#111827", "mood": "serious",
    },
    "warm_grey": {
        "bg": "#f5f1eb", "fg": "#3a2f25", "accent": "#78716c",
        "panel_bg": "#ede8e0", "panel_border": "#d6cfc4", "muted": "#a8a29e",
        "highlight": "#92400e", "mood": "warm",
    },
    "storm_grey": {
        "bg": "#1a1f2a", "fg": "#cbd5e1", "accent": "#475569",
        "panel_bg": "#242a38", "panel_border": "#3a4154", "muted": "#64748b",
        "highlight": "#94a3b8", "mood": "atmospheric",
    },
    "dark_text": {
        "bg": "#fafaf9", "fg": "#1f2937", "accent": "#374151",
        "panel_bg": "#ffffff", "panel_border": "#e5e7eb", "muted": "#6b7280",
        "highlight": "#111827", "mood": "serious",
    },
    "black_ink": {
        "bg": "#ffffff", "fg": "#000000", "accent": "#000000",
        "panel_bg": "#ffffff", "panel_border": "#000000", "muted": "#666666",
        "highlight": "#000000", "mood": "serious",
    },
    "grey_ink": {
        "bg": "#fafaf9", "fg": "#3a3a3a", "accent": "#6b7280",
        "panel_bg": "#ffffff", "panel_border": "#d1d5db", "muted": "#9ca3af",
        "highlight": "#4b5563", "mood": "serious",
    },
    # Earth tones
    "warm_earth": {
        "bg": "#3a2a1a", "fg": "#fef3c7", "accent": "#a0522d",
        "panel_bg": "#4a3525", "panel_border": "#5a4535", "muted": "#fcd34d",
        "highlight": "#f59e0b", "mood": "warm",
    },
    "warm_spectrum": {
        "bg": "#1a1208", "fg": "#fef3c7", "accent": "#f59e0b",
        "panel_bg": "#241a0e", "panel_border": "#3f2f1a", "muted": "#fcd34d",
        "highlight": "linear-gradient(90deg, #f59e0b, #ef4444, #8b5cf6, #3b82f6)",
        "mood": "playful",
    },
    # Reds
    "deep_red": {
        "bg": "#1f0808", "fg": "#fee2e2", "accent": "#991b1b",
        "panel_bg": "#2a0e0e", "panel_border": "#3f1a1a", "muted": "#fca5a5",
        "highlight": "#ef4444", "mood": "serious",
    },
    "alert_red": {
        "bg": "#1a0a0a", "fg": "#fee2e2", "accent": "#dc2626",
        "panel_bg": "#241010", "panel_border": "#3f1a1a", "muted": "#fca5a5",
        "highlight": "#ef4444", "mood": "serious",
    },
    "red": {
        "bg": "#1a0a0a", "fg": "#fee2e2", "accent": "#e74c3c",
        "panel_bg": "#241010", "panel_border": "#3f1a1a", "muted": "#fca5a5",
        "highlight": "#fbbf24", "mood": "serious",
    },
    # Neutrals
    "warm_white": {
        "bg": "#faf6f0", "fg": "#3a2f25", "accent": "#92400e",
        "panel_bg": "#ffffff", "panel_border": "#e7e0d4", "muted": "#a8a29e",
        "highlight": "#c2410c", "mood": "warm",
    },
    "cream_paper": {
        "bg": "#f5ebd6", "fg": "#3a2f1a", "accent": "#92400e",
        "panel_bg": "#faf4e6", "panel_border": "#d6cfc4", "muted": "#8a7860",
        "highlight": "#1f2937", "mood": "serious",
    },
    "warm_cream_with_blue_accents": {
        "bg": "#faf6f0", "fg": "#1f2937", "accent": "#3a86b0",
        "panel_bg": "#ffffff", "panel_border": "#e7e0d4", "muted": "#6b7280",
        "highlight": "#1e40af", "mood": "warm",
    },
    "high_contrast_warm": {
        "bg": "#1a1208", "fg": "#fef3c7", "accent": "#f59e0b",
        "panel_bg": "#241a0e", "panel_border": "#3f2f1a", "muted": "#fcd34d",
        "highlight": "#fde047", "mood": "warm",
    },
}


def _resolve_palette(color_term: str) -> Dict[str, str]:
    """Resolve a color_character vibe term to a full palette."""
    term_lower = color_term.lower().replace(" ", "_")
    if term_lower in PALETTES:
        return PALETTES[term_lower]
    # Try partial matches
    for key, val in PALETTES.items():
        if key in term_lower or term_lower in key:
            return val
    # Default — neutral dark
    return PALETTES["slate_grey"]


# ---------------------------------------------------------------------------
# Typography mapping
# ---------------------------------------------------------------------------

# Map aesthetic / form terms to font stacks.
SERIF_FONTS = "Georgia, 'Times New Roman', 'Noto Serif', serif"
SANS_FONTS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif"
HUMANIST_SANS = "'Hiragino Sans', 'Source Sans Pro', 'Inter', system-ui, sans-serif"
ROUNDED_SANS = "'SF Pro Rounded', 'Nunito', 'Quicksand', system-ui, sans-serif"
MONO_FONTS = "'SF Mono', 'JetBrains Mono', Menlo, Consolas, monospace"
LITERARY_SERIF = "'Iowan Old Style', 'Palatino', 'Source Serif Pro', Georgia, serif"


def _resolve_typography(aesthetic: str, form: str, mood: str) -> Tuple[str, str, str, int]:
    """Return (heading_font, body_font, mono_font, heading_weight)."""
    aesthetic_lower = aesthetic.lower()
    form_lower = form.lower()
    combo = aesthetic_lower + " " + form_lower

    # Literary / atmospheric / narrative → serif
    if any(w in combo for w in ["literary", "atmospheric", "salt", "wood", "rain", "lighthouse", "narrative"]):
        return (LITERARY_SERIF, LITERARY_SERIF, MONO_FONTS, 600)
    # Classic / timeless / document / contract → serif
    if any(w in combo for w in ["classic", "timeless", "contract", "document", "book", "paper"]):
        return (SERIF_FONTS, SERIF_FONTS, MONO_FONTS, 700)
    # Organic / human / warm → humanist sans
    if any(w in combo for w in ["organic", "human", "warm", "inviting", "dignified", "floating"]):
        return (HUMANIST_SANS, HUMANIST_SANS, MONO_FONTS, 600)
    # Youthful / playful → rounded sans
    if any(w in combo for w in ["youthful", "playful", "rounded", "inviting"]):
        return (ROUNDED_SANS, ROUNDED_SANS, MONO_FONTS, 700)
    # Technical / device / strict → sans (clean)
    if any(w in combo for w in ["technical", "device", "strict", "structured", "schematic"]):
        return (SANS_FONTS, SANS_FONTS, MONO_FONTS, 700)
    # Default
    return (SANS_FONTS, SANS_FONTS, MONO_FONTS, 700)


# ---------------------------------------------------------------------------
# Layout strategy selection
# ---------------------------------------------------------------------------


def _select_layout_strategy(graph: SIRGraph, mood: str) -> str:
    """Choose a layout strategy based on the expression type and mood."""
    # Check expression type
    expr_type = ""
    if graph.root:
        for entry in graph.root.get_dimension(Dimension.EXPRESSION):
            if isinstance(entry, dict) and "__type__" in entry:
                expr_type = entry.get("__type__", "")
                break

    if expr_type == "Document":
        return "document"
    if expr_type == "Device":
        return "schematic"

    # Vibe-dominant apps
    if mood == "atmospheric":
        return "atmospheric"

    # Check for dashboard-like structure (many leaf entities)
    if graph.root:
        leaf_count = sum(1 for n in graph.nodes if not n.children)
        if leaf_count >= 8:
            return "dashboard"

    return "app"


# ---------------------------------------------------------------------------
# Form character → shape
# ---------------------------------------------------------------------------


def _resolve_shape(form_term: str) -> Tuple[str, str, str, str, str]:
    """Return (radius_sm, radius_md, radius_lg, card_radius, panel_radius)."""
    form_lower = form_term.lower()
    if "organic" in form_lower:
        return ("8px", "20px", "32px", "24px", "32px")
    if "rounded" in form_lower:
        return ("6px", "12px", "20px", "16px", "16px")
    if "classic" in form_lower:
        return ("0px", "2px", "4px", "2px", "0px")
    if "structured" in form_lower:
        return ("0px", "0px", "0px", "0px", "0px")
    if "generous" in form_lower:
        return ("8px", "16px", "24px", "20px", "16px")
    return ("4px", "8px", "16px", "8px", "12px")


# ---------------------------------------------------------------------------
# Tone → motion
# ---------------------------------------------------------------------------


def _resolve_motion(tone: str, intensity: str) -> Tuple[str, str, bool]:
    """Return (duration, easing, breathing_animation)."""
    tone_lower = tone.lower()
    intensity_lower = intensity.lower()

    if "calm" in tone_lower or "warm" in tone_lower or "floating" in tone_lower:
        return ("600ms", "cubic-bezier(0.4, 0, 0.2, 1)", True)
    if "urgent" in tone_lower:
        return ("150ms", "ease-out", False)
    if "strict" in tone_lower or "formal" in tone_lower:
        return ("0ms", "linear", False)
    if "barely_there" in intensity_lower or "subdued" in intensity_lower:
        return ("1200ms", "cubic-bezier(0.4, 0, 0.2, 1)", True)
    if "playful" in tone_lower:
        return ("300ms", "cubic-bezier(0.34, 1.56, 0.64, 1)", False)
    return ("200ms", "ease", False)


# ---------------------------------------------------------------------------
# Spacing scale
# ---------------------------------------------------------------------------


def _resolve_spacing(intensity: str, mood: str) -> Tuple[str, str, str]:
    """Return (spacing_unit, spacing_scale, content_max_width)."""
    intensity_lower = intensity.lower()
    if "barely_there" in intensity_lower or "subdued" in intensity_lower:
        return ("24px", "expansive", "900px")
    if "atmospheric" in intensity_lower:
        return ("20px", "generous", "1000px")
    if "measured" in intensity_lower or "serious" in mood:
        return ("14px", "tight", "1100px")
    if "playful" in mood:
        return ("18px", "generous", "1100px")
    return ("16px", "normal", "1200px")


# ---------------------------------------------------------------------------
# Texture selection
# ---------------------------------------------------------------------------


def _resolve_texture(aesthetic: str, mood: str) -> Tuple[str, float]:
    """Return (texture, opacity)."""
    aesthetic_lower = aesthetic.lower()
    if "rain" in aesthetic_lower or "water" in aesthetic_lower:
        return ("gradient", 0.15)
    if "salt" in aesthetic_lower or "wood" in aesthetic_lower or "lighthouse" in aesthetic_lower:
        return ("grain", 0.08)
    if "paper" in aesthetic_lower or "book" in aesthetic_lower or "contract" in aesthetic_lower:
        return ("grain", 0.04)
    if "atmospheric" in mood:
        return ("vignette", 0.3)
    if "warm" in mood:
        return ("gradient", 0.1)
    return ("none", 0.0)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def extract_design_tokens(graph: SIRGraph) -> DesignTokens:
    """Extract a complete set of design tokens from the graph's vibe dimensions.

    If the root node has its own vibe dimensions, those drive the design.
    Otherwise, we look at the root's first-level children and aggregate
    their vibes — so an app whose root has no vibe block but whose
    children do still gets a distinct visual identity.
    """
    tokens = DesignTokens()

    if graph.root is None:
        return tokens

    # Collect vibe dimensions from root, falling back to children if empty.
    color_term = ""
    tone = ""
    aesthetic = ""
    form = ""
    intensity = ""

    root_vibes = graph.root.get_dimension(Dimension.VIBE)
    if root_vibes:
        for v in root_vibes:
            if not isinstance(v, dict):
                continue
            aspect = v.get("aspect", "")
            term = str(v.get("term", ""))
            if aspect == "color_character":
                color_term = term
            elif aspect == "tone":
                tone = term
            elif aspect == "aesthetic":
                aesthetic = term
            elif aspect == "form_character":
                form = term
            elif aspect == "intensity":
                intensity = term
    else:
        # Aggregate from first-level children.
        child_colors = []
        child_tones = []
        child_aesthetics = []
        child_forms = []
        child_intensities = []
        for child in graph.root.children:
            for v in child.get_dimension(Dimension.VIBE):
                if not isinstance(v, dict):
                    continue
                aspect = v.get("aspect", "")
                term = str(v.get("term", ""))
                if aspect == "color_character":
                    child_colors.append(term)
                elif aspect == "tone":
                    child_tones.append(term)
                elif aspect == "aesthetic":
                    child_aesthetics.append(term)
                elif aspect == "form_character":
                    child_forms.append(term)
                elif aspect == "intensity":
                    child_intensities.append(term)
        # Take the first (most prominent) of each.
        if child_colors:
            color_term = child_colors[0]
        if child_tones:
            tone = child_tones[0]
        if child_aesthetics:
            aesthetic = child_aesthetics[0]
        if child_forms:
            form = child_forms[0]
        if child_intensities:
            intensity = child_intensities[0]

    # Also check context vibe_brief
    for entry in graph.root.get_dimension(Dimension.EXPRESSION):
        if isinstance(entry, dict) and entry.get("key") == "vibe_brief":
            brief = str(entry.get("value", ""))
            if not aesthetic:
                aesthetic = brief
            # Use brief to augment other fields if they're empty.
            if not tone:
                tone = brief
            if not form:
                # Infer form from brief keywords.
                brief_lower = brief.lower()
                if any(w in brief_lower for w in ("organic", "warm", "human", "inviting")):
                    form = "organic"
                elif any(w in brief_lower for w in ("classic", "timeless", "literary")):
                    form = "classic"

    # Apply palette
    if color_term:
        palette = _resolve_palette(color_term)
        tokens.bg = palette.get("bg", tokens.bg)
        tokens.fg = palette.get("fg", tokens.fg)
        tokens.accent = palette.get("accent", tokens.accent)
        tokens.panel_bg = palette.get("panel_bg", tokens.panel_bg)
        tokens.panel_border = palette.get("panel_border", tokens.panel_border)
        tokens.muted = palette.get("muted", tokens.muted)
        tokens.highlight = palette.get("highlight", tokens.highlight)
        tokens.mood = palette.get("mood", tokens.mood)
        if "accent_secondary" in palette:
            tokens.accent_secondary = palette["accent_secondary"]

    # If no color_term was found, try to infer from aesthetic / vibe_brief.
    if not color_term:
        inferred = _infer_palette_from_aesthetic(aesthetic + " " + tone)
        if inferred:
            palette = _resolve_palette(inferred)
            tokens.bg = palette.get("bg", tokens.bg)
            tokens.fg = palette.get("fg", tokens.fg)
            tokens.accent = palette.get("accent", tokens.accent)
            tokens.panel_bg = palette.get("panel_bg", tokens.panel_bg)
            tokens.panel_border = palette.get("panel_border", tokens.panel_border)
            tokens.muted = palette.get("muted", tokens.muted)
            tokens.highlight = palette.get("highlight", tokens.highlight)
            tokens.mood = palette.get("mood", tokens.mood)

    # Detect gradient backgrounds
    if "gradient" in str(tokens.bg).lower():
        tokens.bg_gradient = tokens.bg

    # Apply typography
    heading_font, body_font, mono_font, heading_weight = _resolve_typography(
        aesthetic, form, tokens.mood
    )
    tokens.heading_font = heading_font
    tokens.body_font = body_font
    tokens.mono_font = mono_font
    tokens.heading_weight = heading_weight

    # Apply shape
    if form:
        rs, rm, rl, cr, pr = _resolve_shape(form)
        tokens.radius_sm = rs
        tokens.radius_md = rm
        tokens.radius_lg = rl
        tokens.card_radius = cr
        tokens.panel_radius = pr

    # Apply motion
    duration, easing, breathing = _resolve_motion(tone, intensity)
    tokens.motion_duration = duration
    tokens.motion_easing = easing
    tokens.breathing_animation = breathing

    # Apply spacing
    spacing_unit, scale, max_width = _resolve_spacing(intensity, tokens.mood)
    tokens.spacing_unit = spacing_unit
    tokens.spacing_scale = scale
    tokens.content_max_width = max_width

    # Apply texture
    texture, opacity = _resolve_texture(aesthetic, tokens.mood)
    tokens.texture = texture
    tokens.texture_opacity = opacity

    # Apply layout strategy
    tokens.layout_strategy = _select_layout_strategy(graph, tokens.mood)

    # Adjust body size based on layout
    if tokens.layout_strategy == "document":
        tokens.body_size = "16px"
        tokens.line_height = "1.7"
    elif tokens.layout_strategy == "atmospheric":
        tokens.body_size = "15px"
        tokens.line_height = "1.7"
        tokens.letter_spacing = "0.01em"
    elif tokens.layout_strategy == "schematic":
        tokens.body_size = "13px"
        tokens.line_height = "1.5"
    elif tokens.layout_strategy == "dashboard":
        tokens.body_size = "14px"
        tokens.line_height = "1.5"

    return tokens


def _infer_palette_from_aesthetic(text: str) -> Optional[str]:
    """If no explicit color_character was set, try to infer one from the
    aesthetic / tone / vibe_brief text."""
    text_lower = text.lower()
    # Map aesthetic keywords to palette names.
    if any(w in text_lower for w in ("warm", "amber", "cream", "earth")):
        return "warm_amber"
    if any(w in text_lower for w in ("calm", "blue", "water", "floating")):
        return "warm_blue"
    if any(w in text_lower for w in ("green", "organic", "natural")):
        return "green"
    if any(w in text_lower for w in ("dark", "midnight", "deep")):
        return "deep_blue"
    if any(w in text_lower for w in ("serious", "strict", "formal", "document")):
        return "neutral_grey"
    if any(w in text_lower for w in ("youthful", "playful", "vibrant")):
        return "warm_earth"
    return None


__all__ = ["DesignTokens", "extract_design_tokens", "PALETTES"]
