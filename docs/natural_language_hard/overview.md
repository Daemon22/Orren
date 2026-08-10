# Architecture Testing: Genuinely Difficult Natural-Language Programs

## Purpose

This document records the results of testing the Orren Engine architecture
on **genuinely difficult natural-language programs** — programs written as
natural-language descriptions of realistic applications that were **not**
designed around or pre-optimized for the existing test suite.

The goal: verify whether the architecture behaves correctly when
non-expert users describe complex, real-world systems in natural English,
exercising every dimension of the 9-dimensional SIR model, equilibrium
conflicts, degradation specifications, lifecycle chains, lifecycle
transitions, multi-target realization, and code generation across 7
language targets.

## Tested Programs

All three programs live in `examples/natural_language_hard/`:

| # | File | Domain | Targets | SIR Nodes | Equilibrium Rules |
|---|------|--------|---------|-----------|-------------------|
| 01 | `01_distributed_voting.orn` | Distributed systems / cryptography | 5 | 23 | 5 |
| 02 | `02_hospital_monitor.orn` | Healthcare / medical devices | 5 | 30 | 6 |
| 03 | `03_trading_bot.orn` | Finance / algorithmic trading | 6 | 27 | 6 |

### Program Summaries

#### 01: Distributed Voting System (Byzantine Fault Tolerance)

A Byzantine fault-tolerant consensus system with:
- 5-phase voting lifecycle (pre-vote → pre-commit → commit → finalize → rotate)
- Validator clusters with primary and backup roles
- Byzantine detector with ML-based anomaly detection
- Anonymity mixer for vote privacy
- Replay protector for vote integrity
- Equilibrium rules: transparency vs. anonymity, liveness vs. safety,
  trust vs. complexity, accountability vs. privacy, rotation vs. stability

#### 02: Hospital Patient Monitor (Life-Critical ICU)

An ICU monitoring system with:
- 4 sensor types (ECG, pulse oximetry, blood pressure, respiratory, temperature)
- 3 parallel detectors (arrhythmia, sepsis, hypotension)
- 4-level escalation (nurse call → charge alert → code blue → PCR)
- Fail-safe behavior on sensor failure
- Immutable audit trail
- Equilibrium rules: sensitivity vs. noise, urgency vs. calm,
  trust vs. transparency, availability vs. privacy,
  escalation doesn't amplify, monitoring vs. battery

#### 03: Algorithmic Trading Bot (Real-Time Finance)

A high-frequency trading system with:
- 4 data feeds (order book, price oracle, liquidity scanner, news sentiment)
- 4 strategy components (alpha generator, risk model, position sizer, execution planner)
- 4 execution components (venue selector, order router, fill tracker, slippage guard)
- 4 risk guards (stop loss, max drawdown, concentration, position limit)
- Online ML model retraining
- Equilibrium rules: speed vs. accuracy, aggression vs. safety,
  signal vs. noise, transparency vs. edge, urgency vs. control,
  persistence vs. performance

## Pipeline Verification

Each program was run through the full Orren Engine pipeline:

```
.orn FILE → CoParser → SIRBuilder → EquilibriumResolver → RealizationCoordinator → [Codegen / Preview]
```

### Results: All 3 Programs Pass End-to-End

| Check | 01 Voting | 02 Hospital | 03 Trading | Status |
|-------|-----------|-------------|------------|--------|
| Parses without error | ✅ | ✅ | ✅ | PASS |
| SIR nodes created | 23 | 30 | 27 | PASS |
| All nodes carry 9 dimensions | ✅ | ✅ | ✅ | PASS |
| Equilibrium rules parsed | 5 | 6 | 6 | PASS |
| Equilibrium rules resolved (0 unresolved) | ✅ | ✅ | ✅ | PASS |
| Realization targets realized | 5/5 | 5/5 | 6/6 | PASS |
| Codegen for every target | ✅ | ✅ | ✅ | PASS |
| Python codegen compiles | ✅ | ✅ | ✅ | PASS |
| HTML preview well-formed | ✅ | ✅ | ✅ | PASS |
| Semantic editor round-trip | ✅ | ✅ | ✅ | PASS |

**Result: 27/27 tests pass in `tests/test_15_natural_language_hard.py`.**

## Key Findings

### 1. Lifecycle Transition Dict Access (Known Bug Already Fixed)

Lifecycle and behavioral transitions are parsed as **dicts** with
`"from_state"` and `"to_state"` keys, not as `LifecycleTransition`
dataclass objects. All codegen generators must use `t.get("from_state", "")`
/ `t.get("to_state", "")` rather than attribute access. This was confirmed
during the codegen expansion phase and fixed in `_gen_c` and `_gen_rust`.

### 2. Custom Vibe Terms and Palette Fallback

The hard programs use custom vibe terms (e.g., `signal_green`, `emergency_red`,
`warning_amber`, `portfolio_gold`, `clinical_blue`, `calm_until_alert`)
that do **not** exist in the `PALETTES` dict in `design_tokens.py`.

The `_resolve_palette` function performs partial matching:
```
if "green" in "signal_green" → matches palette "green"
if "red" in "emergency_red"  → matches palette "red"
```

This works correctly — the engine gracefully falls back to palette entries
that share a color-word substring, so custom vibe terms still produce
sensible color schemes.

### 3. 9-Dimension Invariant Holds

Every SIRNode in all 3 programs has all 9 dimension keys present in its
`dimensions` dict (verified via `node.all_dimensions_present()`). Structural
grouping nodes (e.g., `network`, `monitoring_hub`) may have empty entries
for some dimensions (e.g., no VIBE or COGNITIVE content), but the key is
always present — this is the core structural guarantee of SIRBuilder.

### 4. Equilibrium Resolution Completes Without Conflicts

All equilibrium rules across all 3 programs were resolved with **zero
unresolved conflicts** (`result.unresolved_conflicts == 0`). The
6 preservation directives (`preserve both`, `preserve first`, etc.)
correctly map to resolution strategies.

### 5. Degradation Specifications Attach Correctly

The `degrade:` sections parse correctly and attach `DegradationEntry`
objects to nodes that have content in the named dimension. Each entry
carries a valid `ToleranceLevel` (Full, Faithful, Conventional, Proxy,
Documented, Optional) and a mode (`require` or `tolerate`).

### 6. Semantic Editor Round-Trip Works

The `Engine.editor()` → `modify()` → `undo()` → `re_coordinate()` workflow
works correctly on all 3 programs. After modifying a vibe term and undoing,
the graph is structurally unchanged and re-coordination produces artifacts
without errors.

### 7. Multi-Target Code Generation

All 16 realization targets across the 3 programs (5 + 5 + 6) produce
codegen output. Python targets produce syntactically valid code that
passes `py_compile`. Web targets produce MANIFEST.txt files (the HTML
preview is generated separately via `generate_preview`).

## Test File

`tests/test_15_natural_language_hard.py` contains 27 tests across 9 test
classes:

- `TestPipelineEndToEnd` (4 tests) — full pipeline execution per program
- `TestNineDimensionInvariant` (1 test) — all 9 dimensions present on every node
- `TestEquilibriumRules` (2 tests) — rules parsed, preserved, resolved
- `TestRealizationTargets` (4 tests) — preservation scores, degradation, no dupes
- `TestCodeGenerationFullPipeline` (3 tests) — codegen output, Python compiles, web manifests
- `TestPreviewGeneration` (3 tests) — DOCTYPE, entity rendering, eq + preservation shown
- `TestDesignTokenExtraction` (3 tests) — palette, layout strategy, typography
- `TestDegradationSpecifications` (1 test) — degrade entries attached with valid levels
- `TestSemanticEditorWorkflow` (1 test) — modify → undo → re_coordinate round-trip
- `TestPublicAPIConsistency` (2 tests) — generate_code alias, full artifact coverage

## Full Test Suite

```
724 passed in 49.38s
```

This includes:
- 634 existing tests (all passing, no regressions)
- 63 tests in `test_14_codegen_expansion.py` (all passing)
- 27 tests in `test_15_natural_language_hard.py` (all passing)
