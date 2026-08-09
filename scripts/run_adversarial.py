"""Run all adversarial example .orn files through the engine and report
exactly what happens — crashes, warnings, missing dimensions, anything
that suggests the engine doesn't handle natural-language input cleanly."""
import os
import sys
import traceback

sys.path.insert(0, "/home/z/my-project")

from orren_engine import Engine, Dimension, generate_code

ADVERSARIAL = [
    "01_rain_composition.orn",
    "02_assistive_arm.orn",
    "03_revenue_contract.orn",
    "04_lighthouse.orn",
    "05_sign_bridge.orn",
    "06_still_water.orn",
]

results = []

for fname in ADVERSARIAL:
    path = f"/home/z/my-project/examples/adversarial/{fname}"
    label = fname.replace(".orn", "").replace("_", " ").title()
    print(f"\n=== {label} ===")
    try:
        with open(path) as f:
            src = f.read()
        engine = Engine()
        result = engine.run(src)

        # Check 1: did it parse?
        print(f"  parsed: {result.expressions_count} expression(s)")

        # Check 2: did SIR build?
        print(f"  SIR: {result.sir_node_count} nodes")

        # Check 3: all nodes carry 9 dimensions?
        bad = [n.path for n in result.graph.nodes if not n.all_dimensions_present()]
        if bad:
            print(f"  FAIL: {len(bad)} nodes missing dimensions: {bad[:3]}")
        else:
            print(f"  dimensions: all {result.sir_node_count} nodes carry 9 dimensions")

        # Check 4: equilibrium
        print(f"  equilibrium: {result.equilibrium_outcomes} outcomes, "
              f"{result.unresolved_conflicts} unresolved")

        # Check 5: realization artifacts
        print(f"  artifacts: {len(result.artifacts)}")
        for a in result.artifacts:
            print(f"    - {a.target_name} ({a.target_language}) score={a.preservation_score}")

        # Check 6: codegen runs for each target?
        for tgt in result.graph.realization_targets:
            try:
                files = generate_code(result.graph, tgt)
                total_bytes = sum(len(c) for c in files.values())
                print(f"    codegen {tgt.name}: {len(files)} files, {total_bytes} bytes")
            except Exception as e:
                print(f"    codegen {tgt.name}: FAILED — {e}")
                traceback.print_exc()

        results.append((label, "PASS", ""))
    except Exception as e:
        print(f"  CRASH: {type(e).__name__}: {e}")
        traceback.print_exc()
        results.append((label, "CRASH", f"{type(e).__name__}: {e}"))

print("\n" + "=" * 70)
print("ADVERSARIAL SUMMARY")
print("=" * 70)
for label, status, err in results:
    marker = "PASS" if status == "PASS" else "FAIL"
    print(f"  [{marker}] {label:<30} {err}")
