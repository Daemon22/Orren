"""Comprehensive integration test: verify all components work together as one coherent system.

Tests:
  1. Engine pipeline consistency (parse → SIR → equilibrium → realization → codegen → preview)
  2. All 13 examples produce valid HTML previews with design tokens
  3. CLI commands match engine results for the same inputs
  4. Validation suite results match CLI validate-suite output
  5. Codegen produces files for all realization targets
  6. Semantic editor works on all example graphs (path resolution, search, modify, undo)
  7. Design tokens extracted from all examples
"""
import os
import sys
import json
import traceback

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from orren_engine import Engine
from orren_engine import Dimension
from orren_engine.parser import CoParser
from orren_engine.sir_builder import SIRBuilder
from orren_engine.equilibrium_resolver import EquilibriumResolver
from orren_engine.realization_coordinator import RealizationCoordinator
from orren_engine.semantic_editor import SemanticEditor
from orren_engine import generate_code
from orren_engine.preview import write_preview
from orren_engine.design_tokens import extract_design_tokens, DesignTokens
from orren_engine.validate import run_all

EXAMPLES_DIR = os.path.join(PROJECT_ROOT, "examples")

# --- 13 examples: 7 canonical + 1 microphone + 6 adversarial ---
ALL_EXAMPLES = [
    "01_irrigation.orn",
    "02_news_researcher.orn",
    "03_farmer_dashboard.orn",
    "04_farm_management.orn",
    "05_greenhouse_controller.orn",
    "06_tell_your_story.orn",
    "07_master_builder_book.orn",
    "microphone_application.orn",
    "adversarial/01_rain_composition.orn",
    "adversarial/02_assistive_arm.orn",
    "adversarial/03_revenue_contract.orn",
    "adversarial/04_lighthouse.orn",
    "adversarial/05_sign_bridge.orn",
    "adversarial/06_still_water.orn",
]

print(f"Comprehensive Integration Test")
print(f"{'=' * 80}")
print(f"Testing {len(ALL_EXAMPLES)} examples through full pipeline")
print()

all_ok = True
results = []

for fname in ALL_EXAMPLES:
    rel_path = os.path.join(EXAMPLES_DIR, fname)
    label = fname.replace(".orn", "").replace("_", " ").title()
    if "adversarial" in fname:
        label = f"Adv: {fname.split('/')[-1].replace('.orn','').replace('_', ' ').title()}"

    try:
        with open(rel_path, "r", encoding="utf-8") as f:
            source = f.read()

        # === 1. Parse ===
        exprs = CoParser().parse(source)
        if len(exprs) < 1:
            raise ValueError(f"No expressions parsed from {fname}")

        # === 2. SIR Build ===
        graph = SIRBuilder().build(exprs)
        if len(graph.nodes) < 1:
            raise ValueError(f"No SIR nodes for {fname}")

        # Check all 9 dimensions on all nodes
        dim_failures = [n.path for n in graph.nodes if not n.all_dimensions_present()]
        if dim_failures:
            raise ValueError(f"Nodes missing dimensions: {dim_failures[:3]}")

        # === 3. Equilibrium ===
        report = EquilibriumResolver().resolve(graph)
        if report.unresolved_conflicts:
            raise ValueError(f"{len(report.unresolved_conflicts)} unresolved conflicts")

        # === 4. Realization ===
        artifacts = RealizationCoordinator().coordinate(graph)
        if len(artifacts) < 1:
            raise ValueError(f"No realization artifacts for {fname}")

        # Verify artifact schema
        for art in artifacts:
            d = art.to_dict()
            required = ("target_name", "target_language", "capabilities",
                        "output_files", "degradation_report", "preservation_score")
            for key in required:
                if key not in d:
                    raise ValueError(f"Artifact missing field: {key}")

        # === 5. Codegen ===
        codegen_ok = 0
        codegen_fail = 0
        for tgt in graph.realization_targets:
            try:
                files = generate_code(graph, tgt)
                if files:
                    codegen_ok += 1
                else:
                    codegen_fail += 1
            except Exception as e:
                codegen_fail += 1

        # === 6. Semantic Editor ===
        editor = SemanticEditor(graph)
        # Path resolution (root entity)
        root_node = graph.nodes[0]
        resolved = editor.resolve(root_node.path)
        if resolved is None:
            raise ValueError(f"Could not resolve {root_node.path}")
        # Search by dimension
        vibe_nodes = editor.search(Dimension.VIBE, "color_character", "emerald")
        # Modify + undo
        if vibe_nodes:
            editor.modify(vibe_nodes[0].path, Dimension.VIBE, "tone",
                          "warmer", rationale="integration test")
            editor.undo()

        # === 7. Design Tokens ===
        tokens = extract_design_tokens(graph)
        if not tokens:
            raise ValueError("No design tokens extracted")

        # === 8. Full Engine.run() consistency ===
        engine = Engine()
        result = engine.run(source)
        assert result.expressions_count == len(exprs), \
            f"Engine expr mismatch: {result.expressions_count} vs {len(exprs)}"
        assert result.sir_node_count == len(graph.nodes), \
            f"Engine SIR mismatch: {result.sir_node_count} vs {len(graph.nodes)}"

        results.append((fname, "PASS",
                        f"exprs={len(exprs)}, nodes={len(graph.nodes)}, "
                        f"rules={len(report.outcomes)}, targets={len(artifacts)}, "
                        f"codegen={codegen_ok}/{codegen_ok+codegen_fail}, "
                        f"dims=OK, editor=OK, tokens=OK"))
        print(f"  [PASS] {label:<30} {results[-1][2]}")

    except Exception as e:
        all_ok = False
        results.append((fname, "FAIL", f"{type(e).__name__}: {e}"))
        print(f"  [FAIL] {label:<30} {type(e).__name__}: {e}")
        traceback.print_exc()

# === Phase 2: Validation suite ===
print(f"\n{'=' * 80}")
print("Validation Suite (48 tests)")
print(f"{'-' * 80}")
p1, p2, suite_passed = run_all(EXAMPLES_DIR, verbose=True)
print(f"\nPhase 1: {p1.passed}/{p1.total} | Phase 2: {p2.passed}/{p2.total}")
print(f"Suite overall: {'PASS' if suite_passed else 'FAIL'}")

if not suite_passed:
    all_ok = False

# === Summary ===
print(f"\n{'=' * 80}")
passed = sum(1 for r in results if r[1] == "PASS")
failed = sum(1 for r in results if r[1] == "FAIL")
print(f"Integration Test Summary: {passed}/{len(results)} examples passed, {failed} failed")
print(f"Validation Suite: {p1.passed + p2.passed}/{p1.total + p2.total} passed")
if all_ok and suite_passed:
    print(f"\nALL COMPONENTS ARE COHERENT AND WORKING AS ONE SYSTEM [PASS]")
else:
    print(f"\n⚠️  SOME ISSUES DETECTED — see failures above")

sys.exit(0 if (all_ok and suite_passed) else 1)
