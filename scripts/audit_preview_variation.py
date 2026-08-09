"""Audit: confirm each of the 13 previews has a genuinely distinct visual identity."""
import os
import sys

sys.path.insert(0, "/home/z/my-project")

from orren_engine import Engine, extract_design_tokens

EXAMPLES = [
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

print(f"{'Example':<25} {'Layout':<14} {'Mood':<14} {'BG':<40} {'Font':<10}")
print("-" * 110)

results = []
for src_path, label in EXAMPLES:
    full_path = f"/home/z/my-project/{src_path}"
    with open(full_path) as f:
        src = f.read()
    engine = Engine()
    result = engine.run(src)
    tokens = extract_design_tokens(result.graph)
    bg_short = (tokens.bg_gradient or tokens.bg)[:38]
    font_lower = tokens.heading_font.lower()
    if "iowan" in font_lower or "palatino" in font_lower or "source serif" in font_lower:
        font = "literary_serif"
    elif "georgia" in font_lower or "times" in font_lower or "noto serif" in font_lower:
        font = "serif"
    elif "mono" in font_lower or "jetbrains" in font_lower or "menlo" in font_lower:
        font = "mono"
    elif "rounded" in font_lower or "nunito" in font_lower or "quicksand" in font_lower:
        font = "rounded_sans"
    elif "hiragino" in font_lower or "source sans" in font_lower or "inter" in font_lower:
        font = "humanist_sans"
    else:
        font = "sans"
    print(f"{label:<25} {tokens.layout_strategy:<14} {tokens.mood:<14} {bg_short:<40} {font:<10}")
    results.append((label, tokens.layout_strategy, tokens.mood, tokens.bg, font))

# Now check uniqueness
print()
bgs = [r[3] for r in results]
unique_bgs = set(bgs)
print(f"Unique background palettes: {len(unique_bgs)} / {len(bgs)}")

layouts = [r[1] for r in results]
unique_layouts = set(layouts)
print(f"Unique layout strategies: {len(unique_layouts)} / {len(layouts)}: {unique_layouts}")

moods = [r[2] for r in results]
unique_moods = set(moods)
print(f"Unique moods: {len(unique_moods)} / {len(moods)}: {unique_moods}")

fonts = [r[4] for r in results]
unique_fonts = set(fonts)
print(f"Unique font families: {len(unique_fonts)} / {len(fonts)}: {unique_fonts}")

# Identify duplicates
print()
print("DUPLICATE CHECKS:")
for i, (label, layout, mood, bg, font) in enumerate(results):
    for j, (label2, layout2, mood2, bg2, font2) in enumerate(results[i+1:], i+1):
        if bg == bg2 and layout == layout2 and font == font2:
            print(f"  WARNING: {label} and {label2} have IDENTICAL visual identity")
