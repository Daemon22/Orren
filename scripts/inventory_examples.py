"""Quick inventory: run each example and report actual SIR node count,
equilibrium rule count, realization target count, and section count."""
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from orren_engine import Engine, Dimension

EXAMPLES = [
    ("01_irrigation.orn", "Irrigation"),
    ("02_news_researcher.orn", "News Researcher"),
    ("03_farmer_dashboard.orn", "Farmer Dashboard"),
    ("04_farm_management.orn", "Farm Management"),
    ("05_greenhouse_controller.orn", "Greenhouse Controller"),
    ("06_tell_your_story.orn", "Tell Your Story"),
    ("07_master_builder_book.orn", "Master Builder Book"),
]

print(f"{'#':<3} {'Example':<25} {'Exprs':>5} {'Nodes':>6} {'Rules':>5} {'Tgts':>5} {'Sections':>8} {'All9Dim':>7}")
print("-" * 75)
for i, (fname, label) in enumerate(EXAMPLES, 1):
    path = os.path.join(PROJECT_ROOT, "examples", fname)
    with open(path) as f:
        src = f.read()
    engine = Engine()
    result = engine.run(src)
    # Count distinct section keywords across all expressions.
    section_kws = set()
    for expr in result.graph.expressions:
        section_kws.update(expr.raw_sections.keys())
        section_kws.add("context")  # always present
        if expr.structure:
            section_kws.add("structure")
    all_nine = all(n.all_dimensions_present() for n in result.graph.nodes)
    print(f"{i:<3} {label:<25} {result.expressions_count:>5} {result.sir_node_count:>6} "
          f"{len(result.graph.equilibrium_rules):>5} {len(result.graph.realization_targets):>5} "
          f"{len(section_kws):>8} {'YES' if all_nine else 'NO':>7}")
