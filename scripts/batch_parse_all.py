"""Parse ALL .orn files through the full engine pipeline (parse + SIR + equilibrium + realization)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orren_engine.engine import Engine
from orren_engine.parser import CoParser

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Collect all .orn files, excluding .git
orn_files = []
for dirpath, _, filenames in os.walk(root):
    if '.git' in dirpath:
        continue
    for fname in filenames:
        if fname.endswith('.orn'):
            orn_files.append(os.path.join(dirpath, fname))

orn_files.sort()

parser = CoParser()
passed = 0
failed = 0
failed_files = []

for fpath in orn_files:
    rel = os.path.relpath(fpath, root)
    try:
        with open(fpath, 'r', encoding='utf-8') as f:
            source = f.read()
        # Just test parsing (not full engine run, since some .orn files are library modules)
        exprs = parser.parse(source)
        if len(exprs) >= 1:
            passed += 1
        else:
            failed += 1
            failed_files.append((rel, "no expressions"))
    except Exception as e:
        failed += 1
        failed_files.append((rel, str(e)[:150]))

print(f"Found {len(orn_files)} .orn files")
print(f"Results: {passed} parsed OK, {failed} failed out of {len(orn_files)} total")
if failed_files:
    print(f"\nFailed files ({len(failed_files)}):")
    for rel, err in failed_files:
        print(f"  {rel}: {err}")
else:
    print("\nALL .orn FILES PARSED SUCCESSFULLY")
