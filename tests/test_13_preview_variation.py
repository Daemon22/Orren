"""Preview variation tests.

Validates that previews for different .orn files produce GENUINELY
DIFFERENT visual identities — not the same dark dashboard with a
different accent color.

A meditation app should look like a meditation app.
A contract should look like a contract.
A children's story should look like a children's story.
A robotics device should look like a robotics device.

This test file locks in that requirement by checking:
  - Different apps produce different design tokens (palette, fonts, layout)
  - The CSS varies meaningfully between apps (not just color values)
  - No two unrelated apps share an identical visual identity
  - Specific apps hit their expected visual profiles

Run: pytest tests/test_13_preview_variation.py -v
"""
import hashlib
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from orren_engine import Engine, generate_preview, extract_design_tokens


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_example(src_path):
    full_path = os.path.join(os.path.dirname(__file__), "..", src_path)
    with open(full_path) as f:
        src = f.read()
    engine = Engine()
    return engine.run(src)


def _css_hash(html_str):
    """Extract the <style>...</style> content and hash it."""
    start = html_str.index("<style>") + len("<style>")
    end = html_str.index("</style>")
    css = html_str[start:end]
    return hashlib.sha256(css.encode("utf-8")).hexdigest()[:16]


def _font_family(tokens):
    """Categorize the heading font into a family name."""
    f = tokens.heading_font.lower()
    if "iowan" in f or "palatino" in f or "source serif" in f:
        return "literary_serif"
    if "georgia" in f or "times" in f or "noto serif" in f:
        return "serif"
    if "mono" in f or "jetbrains" in f or "menlo" in f:
        return "mono"
    if "rounded" in f or "nunito" in f or "quicksand" in f:
        return "rounded_sans"
    if "hiragino" in f or "source sans" in f or "inter" in f:
        return "humanist_sans"
    return "sans"


# ---------------------------------------------------------------------------
# Variation: every preview should be visually distinct
# ---------------------------------------------------------------------------


ALL_EXAMPLES = [
    ("examples/01_irrigation.orn",            "Irrigation"),
    ("examples/02_news_researcher.orn",       "News Researcher"),
    ("examples/03_farmer_dashboard.orn",      "Farmer Dashboard"),
    ("examples/04_farm_management.orn",       "Farm Management"),
    ("examples/05_greenhouse_controller.orn", "Greenhouse Controller"),
    ("examples/06_tell_your_story.orn",       "Tell Your Story"),
    ("examples/07_master_builder_book.orn",   "Master Builder Book"),
    ("examples/adversarial/01_rain_composition.orn",  "Rain Composition"),
    ("examples/adversarial/02_assistive_arm.orn",     "Assistive Arm"),
    ("examples/adversarial/03_revenue_contract.orn",  "Revenue Contract"),
    ("examples/adversarial/04_lighthouse.orn",        "Lighthouse"),
    ("examples/adversarial/05_sign_bridge.orn",       "Sign Bridge"),
    ("examples/adversarial/06_still_water.orn",       "Still Water"),
]


class TestPreviewVariation:
    @pytest.fixture(scope="class")
    def all_tokens_and_hashes(self):
        """Run all examples once, cache tokens + CSS hashes."""
        results = []
        for src_path, label in ALL_EXAMPLES:
            result = _run_example(src_path)
            tokens = extract_design_tokens(result.graph)
            html_str = generate_preview(result.graph, artifacts=result.artifacts)
            css_h = _css_hash(html_str)
            results.append((label, tokens, css_h))
        return results

    def test_at_least_3_distinct_layouts(self, all_tokens_and_hashes):
        layouts = {t.layout_strategy for _, t, _ in all_tokens_and_hashes}
        assert len(layouts) >= 3, f"only {len(layouts)} layouts: {layouts}"

    def test_at_least_3_distinct_font_families(self, all_tokens_and_hashes):
        fonts = {_font_family(t) for _, t, _ in all_tokens_and_hashes}
        assert len(fonts) >= 3, f"only {len(fonts)} font families: {fonts}"

    def test_at_least_3_distinct_moods(self, all_tokens_and_hashes):
        moods = {t.mood for _, t, _ in all_tokens_and_hashes}
        assert len(moods) >= 3, f"only {len(moods)} moods: {moods}"

    def test_at_least_5_distinct_backgrounds(self, all_tokens_and_hashes):
        bgs = {t.bg for _, t, _ in all_tokens_and_hashes}
        assert len(bgs) >= 5, f"only {len(bgs)} distinct backgrounds"

    def test_at_least_10_distinct_css_hashes(self, all_tokens_and_hashes):
        """The CSS itself (not just colors) should vary substantially."""
        hashes = {h for _, _, h in all_tokens_and_hashes}
        assert len(hashes) >= 10, (
            f"only {len(hashes)} distinct CSS hashes — previews too similar"
        )

    def test_no_two_unrelated_apps_share_identical_identity(self, all_tokens_and_hashes):
        """No two apps should share the same (layout, font, mood, bg) combo."""
        seen = {}
        for label, tokens, _ in all_tokens_and_hashes:
            key = (tokens.layout_strategy, _font_family(tokens), tokens.mood, tokens.bg)
            if key in seen:
                pytest.fail(
                    f"{label} and {seen[key]} have IDENTICAL visual identity: {key}"
                )
            seen[key] = label


# ---------------------------------------------------------------------------
# Specific visual profile expectations
# ---------------------------------------------------------------------------


class TestSpecificVisualProfiles:
    def test_master_builder_book_uses_document_layout(self):
        result = _run_example("examples/07_master_builder_book.orn")
        tokens = extract_design_tokens(result.graph)
        assert tokens.layout_strategy == "document"
        assert _font_family(tokens) in ("serif", "literary_serif")

    def test_revenue_contract_uses_document_layout(self):
        result = _run_example("examples/adversarial/03_revenue_contract.orn")
        tokens = extract_design_tokens(result.graph)
        assert tokens.layout_strategy == "document"

    def test_revenue_contract_has_neutral_palette(self):
        """A financial contract should NOT use warm/playful colors."""
        result = _run_example("examples/adversarial/03_revenue_contract.orn")
        tokens = extract_design_tokens(result.graph)
        # Strict / serious mood
        assert tokens.mood == "serious"

    def test_still_water_has_breathing_animation(self):
        """A meditation app should breathe."""
        result = _run_example("examples/adversarial/06_still_water.orn")
        tokens = extract_design_tokens(result.graph)
        assert tokens.breathing_animation is True

    def test_still_water_uses_atmospheric_or_app_layout(self):
        result = _run_example("examples/adversarial/06_still_water.orn")
        tokens = extract_design_tokens(result.graph)
        assert tokens.layout_strategy in ("atmospheric", "app", "dashboard")

    def test_lighthouse_uses_atmospheric_layout(self):
        result = _run_example("examples/adversarial/04_lighthouse.orn")
        tokens = extract_design_tokens(result.graph)
        assert tokens.layout_strategy == "atmospheric"

    def test_lighthouse_uses_literary_serif(self):
        """An interactive fiction should use literary serif typography."""
        result = _run_example("examples/adversarial/04_lighthouse.orn")
        tokens = extract_design_tokens(result.graph)
        assert _font_family(tokens) == "literary_serif"

    def test_assistive_arm_uses_schematic_layout(self):
        """A robotic device should use the schematic (technical) layout."""
        result = _run_example("examples/adversarial/02_assistive_arm.orn")
        tokens = extract_design_tokens(result.graph)
        assert tokens.layout_strategy == "schematic"

    def test_greenhouse_controller_uses_schematic_layout(self):
        result = _run_example("examples/05_greenhouse_controller.orn")
        tokens = extract_design_tokens(result.graph)
        assert tokens.layout_strategy == "schematic"

    def test_farmer_dashboard_does_not_use_dark_theme(self):
        """A youthful african farmer dashboard should be warm/bright, not dark slate."""
        result = _run_example("examples/03_farmer_dashboard.orn")
        tokens = extract_design_tokens(result.graph)
        # Should NOT be the default dark slate.
        assert tokens.bg != "#0f172a", "Farmer dashboard still uses default dark theme"
        assert tokens.mood == "warm"

    def test_rain_composition_uses_atmospheric_layout(self):
        result = _run_example("examples/adversarial/01_rain_composition.orn")
        tokens = extract_design_tokens(result.graph)
        assert tokens.layout_strategy == "atmospheric"

    def test_sign_bridge_uses_humanist_or_rounded_font(self):
        """An accessibility tool should feel human, not clinical."""
        result = _run_example("examples/adversarial/05_sign_bridge.orn")
        tokens = extract_design_tokens(result.graph)
        font = _font_family(tokens)
        assert font in ("humanist_sans", "rounded_sans"), (
            f"Sign Bridge uses {font} — should be humanist or rounded"
        )


# ---------------------------------------------------------------------------
# CSS content variation
# ---------------------------------------------------------------------------


class TestCSSVariation:
    def test_document_layout_has_justify_text(self):
        """Document layouts should have justified body text."""
        result = _run_example("examples/07_master_builder_book.orn")
        html_str = generate_preview(result.graph, artifacts=result.artifacts)
        assert "text-align: justify" in html_str or "justify" in html_str

    def test_schematic_layout_has_mono_font(self):
        """Schematic (technical) layouts should use monospace for labels."""
        result = _run_example("examples/adversarial/02_assistive_arm.orn")
        html_str = generate_preview(result.graph, artifacts=result.artifacts)
        assert "mono-font" in html_str or "monospace" in html_str

    def test_atmospheric_layout_has_breathing_animation(self):
        result = _run_example("examples/adversarial/04_lighthouse.orn")
        html_str = generate_preview(result.graph, artifacts=result.artifacts)
        assert "breathe" in html_str or "breathing" in html_str

    def test_dashboard_layout_has_3_column_grid(self):
        result = _run_example("examples/02_news_researcher.orn")
        html_str = generate_preview(result.graph, artifacts=result.artifacts)
        assert "grid-template-columns" in html_str

    def test_document_layout_does_not_have_dashboard_grid(self):
        """A document should NOT use the dashboard's 3-column grid."""
        result = _run_example("examples/07_master_builder_book.orn")
        tokens = extract_design_tokens(result.graph)
        assert tokens.layout_strategy == "document"
        html_str = generate_preview(result.graph, artifacts=result.artifacts)
        # The dashboard grid template should not be in the document preview.
        assert "layout-dashboard" not in html_str


# ---------------------------------------------------------------------------
# Palette diversity
# ---------------------------------------------------------------------------


class TestPaletteDiversity:
    def test_at_least_one_warm_palette(self, ):
        """At least one preview should use a warm-toned palette."""
        warm_count = 0
        for src_path, _ in ALL_EXAMPLES:
            result = _run_example(src_path)
            tokens = extract_design_tokens(result.graph)
            if tokens.mood == "warm":
                warm_count += 1
        assert warm_count >= 2, f"only {warm_count} warm palettes"

    def test_at_least_one_serious_palette(self):
        serious_count = 0
        for src_path, _ in ALL_EXAMPLES:
            result = _run_example(src_path)
            tokens = extract_design_tokens(result.graph)
            if tokens.mood == "serious":
                serious_count += 1
        assert serious_count >= 2, f"only {serious_count} serious palettes"

    def test_at_least_one_atmospheric_palette(self):
        atmo_count = 0
        for src_path, _ in ALL_EXAMPLES:
            result = _run_example(src_path)
            tokens = extract_design_tokens(result.graph)
            if tokens.mood == "atmospheric":
                atmo_count += 1
        assert atmo_count >= 1, f"only {atmo_count} atmospheric palettes"

    def test_at_least_one_light_background(self):
        """At least one preview should use a light/cream background
        (not everything should be dark)."""
        light_count = 0
        for src_path, _ in ALL_EXAMPLES:
            result = _run_example(src_path)
            tokens = extract_design_tokens(result.graph)
            bg = tokens.bg.lower()
            # Light backgrounds start with #f or #ff or contain "cream"/"white"
            if bg.startswith("#f") or bg.startswith("#ff") or "cream" in bg or "white" in bg:
                light_count += 1
        assert light_count >= 2, f"only {light_count} light backgrounds"

    def test_at_least_one_dark_background(self):
        dark_count = 0
        for src_path, _ in ALL_EXAMPLES:
            result = _run_example(src_path)
            tokens = extract_design_tokens(result.graph)
            bg = tokens.bg.lower()
            if bg.startswith("#0") or bg.startswith("#1") or "linear-gradient(180deg, #0" in bg:
                dark_count += 1
        assert dark_count >= 3, f"only {dark_count} dark backgrounds"
