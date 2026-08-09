"""Inspect realization targets across all examples to identify what code types are needed."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orren_engine.parser import CoParser
from orren_engine.sir_builder import SIRBuilder
from orren_engine.realization_coordinator import RealizationCoordinator

EXAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "examples")

all_files = []
for root, _, files in os.walk(EXAMPLES_DIR):
    for f in files:
        if f.endswith('.orn'):
            all_files.append(os.path.join(root, f))

all_files.sort()

print(f"Found {len(all_files)} example .orn files\n")
all_targets = set()

for fpath in all_files:
    rel = os.path.relpath(fpath, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    with open(fpath) as f:
        src = f.read()
    exprs = CoParser().parse(src)
    graph = SIRBuilder().build(exprs)
    for tgt in graph.realization_targets:
        key = (tgt.language, tgt.name)
        if key not in all_targets:
            all_targets.add(key)
            print(f"  {rel}:")
            print(f"    target: {tgt.name}")
            print(f"    language: {tgt.language}")
            print(f"    capabilities: {tgt.capabilities}")
            print(f"    can_express: {tgt.can_express}")
            print(f"    cannot_express: {tgt.cannot_express}")
            print()

print(f"\n=== Unique target languages ===")
langs = set()
for lang, name in all_targets:
    langs.add(lang)
    print(f"  {lang:<25} (seen in: {[n for l,n in all_targets if l == lang]})")
print(f"\nTotal unique languages: {len(langs)}")
