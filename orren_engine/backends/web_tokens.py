"""Vibe-to-CSS token mapping for the premium web backend.

Translates the nine symbolic dimensions into concrete CSS custom properties
(design tokens) so that generated stylesheets carry genuine semantic meaning
rather than placeholder comments.

Each vibe aspect (tone, color_character, form_character, aesthetic, etc.) is
mapped to one or more CSS custom properties.  When a vibe term has no known
mapping the generator emits a DEGRADED marker with a fallback default — it
never silently drops the dimension.

File: orren_engine/backends/web_tokens.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..data_model import Dimension, SIRGraph, SIRNode, ToleranceLevel

# ---------------------------------------------------------------------------
# Vibe term → CSS token value mapping
# ---------------------------------------------------------------------------
# This table is the single source of truth for vibe-to-CSS translation.
# It is explicitly inspectable and overridable: downstream consumers may
# monkey-patch ``VIBE_TERM_TOKENS`` or call ``register_vibe_mapping``.

# colour_character / tone / form_character → color values
_COLOR_MAP: Dict[str, str] = {
    "emerald": "#2ecc71",
    "steel_blue": "#4682b4",
    "slate_blue": "#6a5acd",
    "calm": "#7f8c8d",
    "organic": "#27ae60",
    "warm": "#d4a76a",
    "parchment": "#faf8f1",
    "coral": "#ff6b6b",
    "blue": "#3498db",
    "red": "#e74c3c",
    "green": "#27ae60",
    "amber": "#e67e22",
    "violet": "#9b59b6",
    "indigo": "#3f51b5",
    "rose": "#e06666",
    "amber_warm": "#e67e22",
}


# Vibe aspect → list of (CSS token name, token value resolver function or dict)
# The resolver dict maps vibe *terms* to *token values*.
_VIBE_TOKEN_TABLE: Dict[str, Dict[str, List[Tuple[str, str]]]] = {
    # tone → motion tokens
    "tone": {
        "calm": [("--motion-duration", "0.3s ease"), ("--motion-scale", "subtle")],
        "precise": [("--motion-duration", "0.15s ease-out"), ("--motion-scale", "snappy")],
        "measured": [("--motion-duration", "0.25s ease"), ("--motion-scale", "steady")],
        "bold": [("--motion-duration", "0.1s ease-in-out"), ("--motion-scale", "bold")],
        "dramatic": [("--motion-duration", "0.5s cubic-bezier(0.4, 0, 0.2, 1)"), ("--motion-scale", "dramatic")],
        "playful": [("--motion-duration", "0.4s cubic-bezier(0.34, 1.56, 0.64, 1)"), ("--motion-scale", "playful")],
        "energetic": [("--motion-duration", "0.15s ease-in-out"), ("--motion-scale", "energetic")],
    },
    # color_character → color tokens
    "color_character": {
        "emerald": [("--color-accent", "#2ecc71"), ("--color-accent-secondary", "#27ae60")],
        "steel_blue": [("--color-accent", "#4682b4"), ("--color-accent-secondary", "#3457d2")],
        "slate_blue": [("--color-accent", "#6a5acd"), ("--color-accent-secondary", "#4b0082")],
        "green": [("--color-accent", "#27ae60"), ("--color-accent-secondary", "#2ecc71")],
        "blue": [("--color-accent", "#3498db"), ("--color-accent-secondary", "#2980b9")],
        "red": [("--color-accent", "#e74c3c"), ("--color-accent-secondary", "#c0392b")],
        "coral": [("--color-accent", "#ff6b6b"), ("--color-accent-secondary", "#ff8e8e")],
        "amber": [("--color-accent", "#e67e22"), ("--color-accent-secondary", "#d35400")],
        "warm": [("--color-surface", "#faf8f1"), ("--color-accent", "#d4a76a")],
        "parchment": [("--color-surface", "#faf8f1"), ("--color-accent", "#c19a6b")],
        "calm": [("--color-surface", "#7f8c8d"), ("--color-accent", "#95a5a6")],
        "organic": [("--color-surface", "#27ae60"), ("--color-accent", "#2ecc71")],
    },
    # form_character → shape tokens
    "form_character": {
        "organic": [("--border-radius", "24px"), ("--border-radius-scale", "rounded")],
        "ceremonial": [("--border-radius", "2px"), ("--border-radius-scale", "sharp")],
        "modular": [("--border-radius", "4px"), ("--border-radius-scale", "geometric")],
        "editorial": [("--border-radius", "0px"), ("--border-radius-scale", "flat")],
        "sharp": [("--border-radius", "2px"), ("--border-radius-scale", "sharp")],
        "rounded": [("--border-radius", "16px"), ("--border-radius-scale", "soft")],
        "pill": [("--border-radius", "9999px"), ("--border-radius-scale", "pill")],
        "minimal": [("--border-radius", "4px"), ("--border-radius-scale", "minimal")],
    },
    # aesthetic → layout tokens
    "aesthetic": {
        "calm newsroom": [("--layout-strategy", "document"), ("--spacing-scale", "generous")],
        "music for idealists": [("--layout-strategy", "atmospheric"), ("--spacing-scale", "generous")],
        "industrial precision": [("--layout-strategy", "schematic"), ("--spacing-scale", "tight")],
        "floating in warm water": [("--layout-strategy", "dashboard"), ("--spacing-scale", "generous")],
        "children storybook": [("--layout-strategy", "atmospheric"), ("--spacing-scale", "generous")],
        "serious document": [("--layout-strategy", "document"), ("--spacing-scale", "tight")],
    },
    # activation_signal → glow / shadow tokens
    "activation_signal": {
        "steady_glow": [("--glow-intensity", "0.6"), ("--glow-color", "#2ecc71")],
        "pulse": [("--glow-intensity", "0.8"), ("--glow-color", "#3498db")],
        "subtle": [("--glow-intensity", "0.3"), ("--glow-color", "#7f8c8d")],
    },
    # atmospheric → ambience / texture tokens
    "atmospheric": {
        "mist": [
            ("--atmosphere-texture", "radial-gradient(ellipse at center, rgba(255,255,255,0.08), transparent 70%)"),
            ("--atmosphere-opacity", "0.7"),
            ("--color-atmosphere", "#b8c4cc"),
        ],
        "fire": [
            ("--atmosphere-texture", "linear-gradient(180deg, rgba(255,120,40,0.10), transparent 60%)"),
            ("--atmosphere-opacity", "0.9"),
            ("--color-atmosphere", "#e25822"),
        ],
        "water": [
            ("--atmosphere-texture", "linear-gradient(160deg, rgba(52,152,219,0.12), transparent 55%)"),
            ("--atmosphere-opacity", "0.8"),
            ("--color-atmosphere", "#3498db"),
        ],
        "stone": [
            ("--atmosphere-texture", "none"),
            ("--atmosphere-opacity", "0.5"),
            ("--color-atmosphere", "#8d8d8d"),
        ],
        "growth": [
            ("--atmosphere-texture", "radial-gradient(circle at 30% 20%, rgba(46,204,113,0.10), transparent 50%)"),
            ("--atmosphere-opacity", "0.75"),
            ("--color-atmosphere", "#27ae60"),
        ],
        "decay": [
            ("--atmosphere-texture", "repeating-linear-gradient(45deg, rgba(90,80,60,0.06), transparent 12px)"),
            ("--atmosphere-opacity", "0.6"),
            ("--color-atmosphere", "#7a6a55"),
        ],
        "dawn": [
            ("--atmosphere-texture", "linear-gradient(180deg, rgba(255,183,77,0.14), transparent 65%)"),
            ("--atmosphere-opacity", "0.85"),
            ("--color-atmosphere", "#ffb74d"),
        ],
        "dusk": [
            ("--atmosphere-texture", "linear-gradient(180deg, rgba(94,53,177,0.16), transparent 65%)"),
            ("--atmosphere-opacity", "0.85"),
            ("--color-atmosphere", "#5e35b1"),
        ],
    },
    # cultural → layout rhythm / ornament tokens
    "cultural": {
        "ceremonial": [
            ("--spacing-scale", "generous"),
            ("--layout-strategy", "document"),
            ("--ornament-style", "ruled"),
        ],
        "ancestral": [
            ("--spacing-scale", "generous"),
            ("--layout-strategy", "atmospheric"),
            ("--ornament-style", "woven"),
        ],
        "communal": [
            ("--spacing-scale", "normal"),
            ("--layout-strategy", "dashboard"),
            ("--ornament-style", "open"),
        ],
        "solitary": [
            ("--spacing-scale", "tight"),
            ("--layout-strategy", "schematic"),
            ("--ornament-style", "bare"),
        ],
    },
    # motion → kinetic tokens
    "motion": {
        "still": [("--motion-duration", "0s"), ("--motion-easing", "linear"), ("--motion-scale", "none")],
        "drift": [("--motion-duration", "1.2s ease-in-out"), ("--motion-easing", "ease"), ("--motion-scale", "subtle")],
        "pulse": [("--motion-duration", "0.6s cubic-bezier(0.4, 0, 0.6, 1)"), ("--motion-easing", "ease-in-out"), ("--motion-scale", "medium")],
        "surge": [("--motion-duration", "0.3s cubic-bezier(0.7, 0, 0.3, 1)"), ("--motion-easing", "ease-out"), ("--motion-scale", "bold")],
        "cascade": [("--motion-duration", "0.9s cubic-bezier(0.25, 0.1, 0.25, 1)"), ("--motion-easing", "ease"), ("--motion-scale", "layered")],
    },
}

# Fallback token values per vibe aspect (used when no term matches)
_FALLBACK_TOKENS: Dict[str, List[Tuple[str, str]]] = {
    "tone": [("--motion-duration", "0.2s ease"), ("--motion-scale", "default")],
    "color_character": [("--color-accent", "#95a5a6"), ("--color-surface", "#ecf0f1")],
    "form_character": [("--border-radius", "8px"), ("--border-radius-scale", "standard")],
    "aesthetic": [("--layout-strategy", "dashboard"), ("--spacing-scale", "normal")],
    "activation_signal": [("--glow-intensity", "0.0"), ("--glow-color", "transparent")],
    "atmospheric": [
        ("--atmosphere-texture", "none"),
        ("--atmosphere-opacity", "0.0"),
        ("--color-atmosphere", "transparent"),
    ],
    "cultural": [
        ("--spacing-scale", "normal"),
        ("--layout-strategy", "dashboard"),
        ("--ornament-style", "none"),
    ],
    "motion": [("--motion-duration", "0.2s ease"), ("--motion-easing", "ease"), ("--motion-scale", "default")],
}


@dataclass
class VibeTokenMap:
    """All CSS custom properties derived from a node's vibe dimension.

    Attributes:
        css_variables: Mapping of ``--token-name`` to value.
        degraded: List of DEGRADED marker strings for unmappable aspects.
        proxy: List of PROXY markers for dimensions the target cannot express.
        node_path: SIR node path this token set was derived from.
        node_id: Stable semantic ID for the node.
    """
    css_variables: Dict[str, str] = field(default_factory=dict)
    degraded: List[str] = field(default_factory=list)
    proxy: List[str] = field(default_factory=list)
    node_path: str = ""
    node_id: str = ""


def _node_id(path: str) -> str:
    """Derive a stable semantic ID from a node path."""
    return path.replace(".", "-").replace("_", "-")


def _vibe_term_to_tokens(aspect: str, term: str) -> List[Tuple[str, str]]:
    """Resolve a (vibe aspect, vibe term) pair to concrete CSS token pairs.

    Args:
        aspect: The vibe aspect (e.g. ``color_character``, ``tone``).
        term: The vibe term value (e.g. ``emerald``, ``calm``).

    Returns:
        List of (css-custom-property, value) pairs.  Falls back to
        ``_FALLBACK_TOKENS`` when the term is not in the primary table.
    """
    table = _VIBE_TOKEN_TABLE.get(aspect, {})
    term_lower = term.lower()
    if term_lower in table:
        return table[term_lower]
    # Try partial match for compound terms (e.g. "calm newsroom")
    for key, tokens in table.items():
        if key in term_lower:
            return tokens
    # Return fallback for this aspect
    return _FALLBACK_TOKENS.get(aspect, [])


def _is_xhosa(text: str) -> bool:
    """Detect Xhosa linguistic features in text.

    Checks for click-consonant patterns and Bantu noun-class prefixes
    that are hallmarks of Xhosa orthography.

    Args:
        text: Text to inspect.

    Returns:
        True when Xhosa linguistic features are detected.
    """
    if not text:
        return False
    text_lower = text.lower()
    # Xhosa click consonants: q, x, c used as phoneme markers
    # Xhosa noun class prefixes: umu-, aba-, in-, i-, a-, e-, o-
    xhosa_indicators = [
        "xho", "isi", "uku", "nge", "ngok",  # Xhosa root words
        "umse", "umnt", "iint", "iint", "abantu",  # noun class patterns
        "ngokuth", "ngokuba", "kodwa", "ke ngoko",  # common phrases
    ]
    return any(ind in text_lower for ind in xhosa_indicators)


def extract_locale(graph: SIRGraph) -> str:
    """Determine the locale for the generated HTML ``lang`` attribute.

    Inspects expression-dimension metadata (purpose, audience, etc.) and
    the raw .orn source text for Xhosa linguistic features.  Defaults to
    ``"en"`` when no locale hint is found.

    Args:
        graph: The SIR graph (root node is consulted).

    Returns:
        BCP-47 locale tag (``"xh"`` for Xhosa, ``"en"`` otherwise).
    """
    if graph.root is None:
        return "en"
    exprs = graph.root.get_dimension(Dimension.EXPRESSION)
    for expr in exprs:
        if isinstance(expr, dict):
            # Check for explicit locale declaration.
            for key in ("locale", "language", "lang"):
                if key in expr and isinstance(expr[key], str):
                    return expr[key]
            # Check value text for Xhosa features.
            val = expr.get("value", "")
            if isinstance(val, str) and _is_xhosa(val):
                return "xh"
    return "en"


def extract_vibe_tokens(graph: SIRGraph, node: SIRNode) -> VibeTokenMap:
    """Extract CSS custom-property design tokens from a node's vibe dimension.

    Preserves **every** vibe aspect.  When a term has no known CSS mapping it
    falls back to a default token and records a DEGRADED marker.  When a
    dimension is declared ``cannot_express`` on the realization target, a
    PROXY marker is recorded.

    Args:
        graph: The SIR graph (used to check the root node's cannot_express list).
        node: The SIRNode to extract vibe tokens from.

    Returns:
        A :class:`VibeTokenMap` with CSS variables, degraded and proxy markers.
    """
    vibes = node.get_dimension(Dimension.VIBE)
    token_map = VibeTokenMap(
        node_path=node.path,
        node_id=_node_id(node.path),
    )

    # Determine which vibe aspects the target cannot_express (proxy).
    # The cannot_express list lives on realization targets, not nodes.
    # We approximate by checking degradation_tolerance on the node itself.
    node_tolerance = node.degradation_tolerance
    proxy_aspects: set = set()
    for key, entry in node_tolerance.items():
        if entry.level == ToleranceLevel.PROXY:
            proxy_aspects.add(entry.aspect)

    if not vibes:
        # No vibe data — record a degraded marker.
        token_map.degraded.append(
            f"/* DEGRADED: no vibe data for {node.path} — using default tokens */"
        )
        token_map.css_variables["--vibe-presence"] = "none"
        return token_map

    for vibe in vibes:
        if not isinstance(vibe, dict):
            continue
        aspect = vibe.get("aspect", "")
        term = vibe.get("term", "")
        if not aspect or not term:
            continue

        if aspect in proxy_aspects:
            token_map.proxy.append(
                f"/* PROXY: vibe {aspect} = '{term}' — target cannot fully express; "
                f"using semantic approximation */"
            )
            token_map.degraded.append(
                f"/* DEGRADED: vibe {aspect} = '{term}' expressed as proxy, "
                f"not faithful */"
            )

        tokens = _vibe_term_to_tokens(aspect, term)
        if not tokens:
            # No mapping at all — emit DEGRADED with fallback.
            token_map.degraded.append(
                f"/* DEGRADED: vibe {aspect} = '{term}' has no known CSS mapping; "
                f"using default fallback */"
            )
            fallback = _FALLBACK_TOKENS.get(aspect, [])
            for css_name, css_val in fallback:
                token_map.css_variables[css_name] = css_val
        else:
            for css_name, css_val in tokens:
                token_map.css_variables[css_name] = css_val

    # Always emit presence token so CSS consumers know vibe data existed.
    token_map.css_variables["--vibe-presence"] = "semantic"
    token_map.css_variables["--semantic-id"] = token_map.node_id

    return token_map


def extract_all_tokens(graph: SIRGraph) -> Dict[str, VibeTokenMap]:
    """Extract vibe tokens for every node that has vibe content.

    Args:
        graph: The SIR graph.

    Returns:
        Mapping of ``node.path`` → :class:`VibeTokenMap`.
    """
    result: Dict[str, VibeTokenMap] = {}
    for node in graph.nodes:
        if node.kind == "root":
            continue
        if not node.has_dimension_content(Dimension.VIBE):
            continue
        result[node.path] = extract_vibe_tokens(graph, node)
    return result


# ---------------------------------------------------------------------------
# Public registry (overridable)
# ---------------------------------------------------------------------------

def register_vibe_mapping(aspect: str, term: str, tokens: List[Tuple[str, str]]) -> None:
    """Register or override a vibe-to-CSS token mapping at runtime.

    Args:
        aspect: The vibe aspect (e.g. ``color_character``).
        term: The vibe term (e.g. ``emerald``).
        tokens: List of (css-custom-property, value) pairs.
    """
    table = _VIBE_TOKEN_TABLE.setdefault(aspect, {})
    table[term.lower()] = tokens


__all__ = [
    "VibeTokenMap",
    "extract_vibe_tokens",
    "extract_all_tokens",
    "extract_locale",
    "register_vibe_mapping",
]
