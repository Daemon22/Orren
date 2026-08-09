"""Generate HTML previews for all 13 examples (7 canonical + 6 adversarial)."""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from orren_engine import Engine, write_preview

EXAMPLES = [
    ("examples/01_irrigation.orn",            "01_irrigation"),
    ("examples/02_news_researcher.orn",       "02_news_researcher"),
    ("examples/03_farmer_dashboard.orn",      "03_farmer_dashboard"),
    ("examples/04_farm_management.orn",       "04_farm_management"),
    ("examples/05_greenhouse_controller.orn", "05_greenhouse_controller"),
    ("examples/06_tell_your_story.orn",       "06_tell_your_story"),
    ("examples/07_master_builder_book.orn",   "07_master_builder_book"),
    ("examples/adversarial/01_rain_composition.orn",  "adv_01_rain_composition"),
    ("examples/adversarial/02_assistive_arm.orn",     "adv_02_assistive_arm"),
    ("examples/adversarial/03_revenue_contract.orn",  "adv_03_revenue_contract"),
    ("examples/adversarial/04_lighthouse.orn",        "adv_04_lighthouse"),
    ("examples/adversarial/05_sign_bridge.orn",       "adv_05_sign_bridge"),
    ("examples/adversarial/06_still_water.orn",       "adv_06_still_water"),
]

OUT_DIR = os.path.join(PROJECT_ROOT, "download", "previews")
os.makedirs(OUT_DIR, exist_ok=True)

print(f"Generating {len(EXAMPLES)} previews into {OUT_DIR}/\n")
for src_path, label in EXAMPLES:
    full_src = os.path.join(PROJECT_ROOT, src_path)
    out_path = os.path.join(OUT_DIR, f"{label}.html")
    try:
        with open(full_src) as f:
            src = f.read()
        engine = Engine()
        result = engine.run(src)
        write_preview(result.graph, out_path, artifacts=result.artifacts)
        size_kb = os.path.getsize(out_path) / 1024
        print(f"  [OK] {label:<35} {size_kb:.1f} KB  ({result.sir_node_count} nodes, {len(result.artifacts)} targets)")
    except Exception as e:
        print(f"  [FAIL] {label:<35} {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

print(f"\nAll previews in: {OUT_DIR}/")
print(f"Open any in a browser, e.g.: file://{OUT_DIR}/adv_06_still_water.html")
