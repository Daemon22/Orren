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
orren preview app.orn              # generates self-contained HTML preview
orren validate app.orn
orren validate-suite               # runs the canonical 48-test suite
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
pytest tests/ -v          # 634 tests across 13 phases
orren validate-suite      # canonical 48-test validation against bundled examples
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
| 8 | CLI + reproducible builds          | 21    |
| 9 | Integration tests                  | 30    |
| 10 | Validation suite (48 canonical)    | 18    |
| 11 | Adversarial natural-language       | 96    |
| 12 | Preview quality (layout-agnostic)  | 105   |
| 13 | Preview variation                  | 28    |

## Adversarial testing

6 adversarial `.orn` files in `examples/adversarial/` were written as
natural-language descriptions — not designed around the grammar. They
cover domains the engine had never seen:

1. **Rain Composition** — music + emotion detection
2. **Assistive Arm** — medical device + robotics
3. **Revenue Contract** — financial + legal
4. **Lighthouse** — interactive fiction + narrative (41 nodes, 5 endings)
5. **Sign Bridge** — accessibility + cross-modality
6. **Still Water** — meditation + vibe-dominant

These surfaced two real engine bugs (both fixed in v0.3.2):
- **SIR builder only built the first top-level structure node** —
  multi-root structures (e.g. `arm` + `control_unit` + `interface`)
  silently dropped all but the first subtree. Fixed: all top-level
  nodes are now built.
- **Conditional parser only accepted `activates|begins|deactivates on`** —
  natural-language conditionals like `intensifies when user_sad` or
  `never displays timer` were silently dropped. Fixed: the parser now
  accepts any verb + `on`/`when`, plus `never` and `blocked when` forms.

## Displayable previews

`orren preview FILE` generates a single self-contained HTML file with
inline CSS + JS — no external dependencies. Open it in any browser to
see a visual mockup of the described interface.

**Crucially, each preview looks genuinely different** — the vibe
dimensions drive the entire page aesthetic, not just badge colors.
The design system (`orren_engine/design_tokens.py`) maps vibes to:

- **Palette**: full background/foreground/accent/panel/muted scheme
- **Typography**: literary serif for narratives, humanist sans for
  accessibility tools, rounded sans for youth-focused apps, serif for
  documents, mono for technical schematics
- **Layout strategy**: 5 distinct strategies
  - `document` — single column, wide margins, justified text (books, contracts)
  - `dashboard` — 3-column grid (dashboards, information-dense)
  - `app` — focused centered canvas (single-purpose apps)
  - `atmospheric` — full-bleed, breathing animation, floating orbs
    (meditation, music, narrative)
  - `schematic` — component diagram with safety/sensor/actuator markers
    (devices, robotics)
- **Motion**: slow + breathing for calm apps, snappy for urgent,
  none for formal documents
- **Texture**: gradient for water/air, grain for paper/wood, vignette
  for atmospheric scenes
- **Shape**: organic curves for warm apps, sharp corners for strict,
  classic for documents

13 preview files are pre-generated in `download/previews/`. Audit
results across all 13:

| Dimension | Unique values |
|---|---|
| Layout strategies | 5 (document/dashboard/app/atmospheric/schematic) |
| Font families | 5 (literary_serif/serif/humanist_sans/rounded_sans/sans) |
| Moods | 5 (cool/warm/serious/neutral/atmospheric) |
| Background palettes | 10 unique |
| Identical visual identities | 0 (no two unrelated apps look the same) |

Open a few in tabs to see the difference:

```
file:///home/z/my-project/download/previews/07_master_builder_book.html   # cream paper document
file:///home/z/my-project/download/previews/adv_03_revenue_contract.html   # strict white document
file:///home/z/my-project/download/previews/adv_06_still_water.html        # breathing warm-blue atmospheric
file:///home/z/my-project/download/previews/adv_04_lighthouse.html         # deep navy with amber lamp glow
file:///home/z/my-project/download/previews/adv_02_assistive_arm.html      # warm-white technical schematic
file:///home/z/my-project/download/previews/03_farmer_dashboard.html       # warm earth-tone dashboard
```

## Validation suite

The `orren_engine.validate` module runs the canonical 48-test validation
suite referenced in `07_VALIDATION_v3.md`:

- **Phase 1**: 7 example .orn files × 6 tests = 42 tests
  - `parse`, `sir`, `equilibrium`, `realization`, `dimensions`, `preservation`
- **Phase 2**: 6 gap syntax tests
  - `gap1_calibration`, `gap2_behavioral`, `gap3_realization_schema`,
    `gap4_degradation_tolerance`, `gap5_subsystem_composition`,
    `gap6_semantic_editing`

The 7 example files live in `examples/`:

1. `01_irrigation.orn` — Agriculture, semantic condition overrides timing
2. `02_news_researcher.orn` — Information agent, rich vibe with conflict resolution
3. `03_farmer_dashboard.orn` — Web page, "youthful african professional symbolic"
4. `04_farm_management.orn` — Full application, multi-system hierarchical equilibrium
5. `05_greenhouse_controller.orn` — IoT/hardware, safety hierarchy + qualitative stress
6. `06_tell_your_story.orn` — Mobile app, all 8 dimensions simultaneously
7. `07_master_builder_book.orn` — PDF/document, conditional layout, semantic color
