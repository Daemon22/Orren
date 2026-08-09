"""Check all orren_engine modules for import errors."""
import importlib
import pkgutil
import sys
import os

sys.path.insert(0, os.getcwd())
import orren_engine

failed = []
total = 0
for mod in pkgutil.walk_packages(orren_engine.__path__, 'orren_engine.'):
    total += 1
    name = mod.name
    try:
        importlib.import_module(name)
    except Exception as e:
        failed.append((name, str(e)[:200]))

print(f"Checked {total} modules")
if failed:
    print(f"FAILED ({len(failed)}):")
    for name, err in failed:
        print(f"  {name}: {err}")
    sys.exit(1)
else:
    print("All modules import OK")
