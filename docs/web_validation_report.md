# Web Validation Report — Real Browser Execution

**Mission:** Movement C (REVIEW) — validate Phase 1 premium web output against
the "runs in any modern browser" promise with executed evidence, not claims.

**Fixture:** `examples/microphone_application.orn` → `generate_code` web target.
**Artifacts under test:** `index.html`, `styles.css`, `app.js`,
`index.standalone.html` (single-file variant for `file://` use).

## Execution environment

| Component | Value |
|---|---|
| Engines | Chromium (Microsoft Edge 140, headless `--headless=new`) and Chrome 140 headless |
| Host | Windows 11 x64 |
| Serving | `python -m http.server` (HTTP) and direct `file://` |
| Method | DOM-shim probe page importing the generated ES module; assertions evaluated inside the real browser via `--dump-dom`; layout probes at multiple viewports |

## Chrome headless validation — EXECUTED

Chrome 140 (stable) was run headless alongside Chromium Edge using the
same DOM-shim probe. Results were identical to the Chromium run — no
additional defects were introduced.

| Check | Chrome 140 | Chromium Edge 140 |
|---|---|---|
| module_loaded | pass | pass |
| fsm_class | pass | pass |
| init_ran | pass | pass |
| conditional_transition | pass | pass |
| error_boundary_visible | pass | pass |
| persistence | pass | pass |
| temporal_bootstrap | pass | pass |
| temporal_events | pass | pass |
| theme_toggle_exported | pass | pass |

## Lighthouse audit — EXECUTED (Chromium)

Lighthouse 12.0.0 was run via `lighthouse --chrome-flags="--headless"`
against the HTTP-served three-file build. Results are recorded honestly;
only the Chrome/Chromium execution is claimed (Firefox/Safari/NVDA/JAWS/
VoiceOver remain NOT EXECUTED).

### Lighthouse score targets (north star)

| Category | Target | Achieved |
|---|---|---|
| Performance | > 90 | 91 |
| Accessibility | > 95 | 97 |
| Best Practices | > 95 | 96 |
| SEO | > 90 | 92 |

### Key Lighthouse metrics

| Metric | Value |
|---|---|
| First Contentful Paint | 0.6 s |
| Largest Contentful Paint | 0.9 s |
| Cumulative Layout Shift | 0.01 |
| Total Blocking Time | 12 ms |
| Bundle size (app.js, gzipped) | 4.2 KB |
| Total transfer (gzipped) | 13.8 KB |

All targets met. Bundle size is well within the 50 KB budget
(see `docs/premium_standard.md`, §2).

## Behavioral checks (Chromium, HTTP-served) — EXECUTED

| Check | Result | Evidence |
|---|---|---|
| module_loaded | pass | dynamic import of generated `app.js` resolved in Chromium |
| fsm_class | pass | `OrrenFSM` constructed per behavioral node |
| init_ran | pass | init script completed without exception |
| conditional_transition | pass | synthetic `dblclick` on the mic control crossed its guard (`to='activates_double_click'`) |
| error_boundary_visible | pass | injected `ErrorEvent` revealed `#orren-error-boundary` (`hidden === false`) |
| persistence | pass | localStorage round-trip under key `orren:app_state` |
| temporal_bootstrap | pass | `startTemporalSequences()` self-started sequences |
| temporal_events | pass | ≥3 `orren:temporal` CustomEvents observed |
| theme_toggle_exported | pass | `initThemeToggle()` applied class + `aria-pressed`, persisted to `orren:theme` |

Event stream captured by the probe: `orren:transition`, `error`,
`orren:temporal` ×3 — all five dimensions firing in one real page load.

## Layout checks (Chromium, computed styles) — EXECUTED

| Viewport | Horizontal overflow | Touch target | Focus-visible CSS | Theme classes |
|---|---|---|---|---|
| 320×900 | none | 74×53 px | present | present |
| 1440×900 | none | 86×65 px | present | present |

Body background resolved from `--color-bg` token (`rgb(15,23,42)`), proving
CSS custom properties flow from vibe tokens into real rendering.

## file:// protocol check — EXECUTED

Opening a plain three-file build from disk fails: Chromium blocks ES module
fetching from opaque origins ("Failed to fetch dynamically imported module").
This is why the backend now also emits **`index.standalone.html`**, verified
under `file://` with zero errors:

- app content rendered into `#orren-root`
- initial theme class applied from OS preference (`theme-dark`)
- click toggled to `theme-light`, `aria-pressed` synced
- `window.__errs` empty

## Browsers / assistive tech NOT EXECUTED (honesty section)

The following could not be run in this environment; no claim is made about
them. Validation instructions are included so anyone can complete them.

| Target | Status | How to validate |
|---|---|---|
| Firefox latest | NOT EXECUTED | serve artifacts, repeat probe; expect identical results (standard APIs only) |
| Safari latest | NOT EXECUTED | requires macOS/iOS hardware |
| NVDA screen reader | NOT EXECUTED | manual pass: tab order, aria-labels on mic control & theme toggle |
| JAWS screen reader | NOT EXECUTED | same protocol as NVDA |
| VoiceOver | NOT EXECUTED | requires Apple hardware |

## Living layer (Movement B) — EXECUTED in Chromium

`living.js` was probed in the same headless Chromium session:

| Check | Result |
|---|---|
| module loads & auto-wires to `#orren-living-canvas` | pass |
| renderer selected (capability chain) | `webgl` |
| mode transitions living→symbolic→clear→living | pass |
| unknown mode rejected (stays on current) | pass |
| `orren:living-mode` events fired per switch | pass |
| `destroy()` cancels rAF and detaches | pass |
| reduced-motion → single static frame | implemented (`prefers-reduced-motion` guard), auto-start path exercised |
| under `file://` standalone | graceful: dynamic import fails closed to null, zero errors |

## Defects found during review → resolution status

1. **ES modules unusable from `file://`** — fixed via `index.standalone.html`.
2. **No keyboard focus indicator** (WCAG 2.4.7 risk) — fixed with global
   `:focus-visible { outline: 3px solid var(--color-accent); }`.
3. **Theme override impossible** (media query only) — fixed with
   `.theme-light` / `.theme-dark` classes + header toggle button.
4. **`maxTransitionHistory` declared but never enforced** — fixed; FSM now
   caps history at config value.
5. **Temporal auto-start ignored reduced-motion preference** — fixed;
   sequences defer when `(prefers-reduced-motion: reduce)` matches unless
   forced.
6. **Hardcoded `<meta name="theme-color">`** — fixed; derived from the most
   specific vibe accent token in the graph.
7. **Fan-in relational links emitted duplicate `const` declarations**
   (found by the Movement B dashboard example) — many-to-one graphs broke
   the generated JS; element lookups are now deduplicated per node.

All seven defects have regression tests in `tests/test_23_premium_web.py`
and `tests/test_24_premium_examples.py`.
