# Orren Engine

A multidimensional semantic interpretation + realization pipeline.

## Architecture

```
.orn FILE
    │
    ▼
CoParser             — 1 file → N expressions
    │
    ▼
SIRBuilder           — expressions → SIR graph (every node carries all 9 dimensions)
    │
    ▼
EquilibriumResolver  — conflict detection + resolution
    │
    ▼
RealizationCoordinator — SIR → realization artifacts
    │
    ▼
Codegen              — artifacts → target-language source code
    │
    ▼
SemanticEditor       — path-based edits with undo/redo
```

## The 9 dimensions

Every SIR node carries all 9 dimensions simultaneously — no dimension
can be silently dropped during realization:

1. Expression (context + structure)
2. Cognitive
3. Vibe
4. Spatial
5. Temporal
6. Relational
7. Conditional
8. Behavioral
9. Equilibrium (cross-cutting, applied during resolution)

## Installation

```bash
pip install -e .
```

## CLI usage

```bash
orren parse app.orn
orren sir app.orn
orren resolve app.orn
orren realize app.orn --out ./out
orren validate app.orn
orren hash app.orn
```

## Python API

```python
from orren_engine import Engine, Dimension
from orren_engine.codegen import generate as generate_code

engine = Engine()
result = engine.run(source)

# Inspect the SIR
for node in result.graph.nodes:
    print(node.path, node.get_dimension(Dimension.VIBE))

# Generate code for each realization target
for tgt in result.graph.realization_targets:
    files = generate_code(result.graph, tgt)
    for fname, code in files.items():
        print(fname, len(code), "bytes")

# Semantic editing
editor = engine.editor()
editor.modify("mic_app.home.microphone_control", Dimension.VIBE, "color_character", "calmer emerald")
editor.undo()
```

## Reproducibility

The same `.orn` source produces the same SIR hash and the same generated
artifacts, byte-for-byte, on every run.

```bash
orren hash app.orn   # SHA-256 of the SIR signature
```

## Test suite

```bash
pytest tests/ -v
```

| # | Suite                              | Tests |
|---|------------------------------------|-------|
| 1 | Co-parser unit tests               | 48    |
| 2 | Semantic Editor Protocol contract  | 38    |
| 3 | Semantic object graph invariants   | 32    |
| 4 | Equilibrium resolver determinism   | 18    |
| 5 | SIR builder output stability       | 18    |
| 6 | Code generator correctness         | 35    |
| 7 | Benchmarks + memory profiling      | 14    |
| 8 | CLI + reproducible builds          | (this file) |
| 9 | Integration tests                  | (this file) |
