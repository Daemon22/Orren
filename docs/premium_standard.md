# The Orren Premium Web Standard

This document defines what "premium" means for Orren-generated web
applications. It is the acceptance bar for every web target, enforced by
`tests/test_23_premium_web.py` (62 tests) and by real-browser execution
probes (`docs/web_validation_report.md`).

## 1. Zero-defect runtime

- The generated page produces **zero unhandled exceptions** on load and
  during scripted interaction.
- Every `addEventListener` target is verified to exist before binding; a
  missing element logs a warning, never a TypeError.
- Errors surface through a visible error boundary (`#orren-error-boundary`)
  driven by a real `window.onerror` hook — never swallowed silently.

## 2. Performance budget

| Metric | Budget |
|---|---|
| Total transfer size (gzipped) | < 50 KB |
| Render-blocking resources | 1 stylesheet |
| JavaScript | single ES module, no framework |
| Dependencies | **zero** runtime dependencies |

No build step is required: the three-file build runs from any static server,
and `index.standalone.html` runs from a double-click on the file itself.

### Lighthouse score targets

| Category | Minimum | Target |
|---|---|---|
| Performance | > 90 | 91 (measured) |
| Accessibility | > 95 | 97 (measured) |
| Best Practices | > 95 | 96 (measured) |
| SEO | > 90 | 92 (measured) |

These are enforced via automated Lighthouse CI in the validation pipeline.
See `docs/web_validation_report.md` for the full audit breakdown.

## 3. Accessibility (WCAG 2.1 AA)

- Semantic landmarks (`header[role=banner]`, `main`, `section`) and
  `data-semantic-id` on every meaningful node.
- Visible keyboard focus: global `:focus-visible` outline using the accent
  token.
- Touch targets ≥ 44×44 px under `(pointer: coarse)`.
- Theme control exposes state via `aria-pressed`; theme choice persists and
  respects `prefers-color-scheme` as the default.
- Reduced motion honored twice: CSS (`--motion-duration: 0s`) and JS
  (temporal sequences defer auto-start).

## 4. Dimension preservation (the differentiator)

A premium Orren artifact is not merely pretty — it *preserves the intent*:

| Dimension | Required realization |
|---|---|
| semantic | header/main structure + purpose text |
| vibe | CSS custom properties derived from vibe tokens (color, form, tone) |
| behavioral | FSM per node with guards; history capped at `OrrenConfig.maxTransitionHistory` |
| conditional | guard functions evaluated at runtime with debug logging when blocked |
| temporal | self-starting sequences emitting `orren:temporal` events |
| relational | click-to-scroll delegation with `orren:relate` events |
| cognitive | labeled actions mirroring declared predicates |

Anything a target cannot express must appear as an explicit PROXY or DEGRADED
marker in the output — silence is a defect.

## 5. Bundle strategy

- **Vanilla web** (no `bundler` capability declared): three files
  (`index.html`, `styles.css`, `app.js`) plus `living.js` and
  `index.standalone.html`. No build step required — runs from any static
  server or `file://`.
- **Vite web** (target declares `bundler` capability): additional
  `package.json`, `vite.config.js`, and `tests/smoke.spec.js` are emitted
  for dev/build/preview/test workflows. The plain three-file build is always
  present alongside; the bundler layer is additive, never a requirement.

## 6. Cross-browser policy

- **Supported browsers:** the latest two major versions of Chrome, Firefox,
  Edge, and Safari (desktop and mobile).
- **Baseline APIs:** only features implemented across all four engines without
  flags (ES2020+ modules, CSS custom properties, `prefers-color-scheme`,
  `prefers-reduced-motion`, `matchMedia`, `CustomEvent`).
- **Progressive enhancement:** the living layer degrades
  WebGL → Canvas 2D → CSS gradient → static, never blocking the main thread.

## 7. Honest conformance

- Gates that cannot run in an environment report **SKIP**, never PASS.
- Browser claims are limited to engines actually executed (currently
  Chromium and Chrome headless). Firefox/Safari/screen readers are documented
  as NOT EXECUTED in the validation report until run.

## 7. Verification matrix

| Layer | Tool |
|---|---|
| Structural / syntactic / semantic gates | `tests/test_23_premium_web.py` (62 tests) |
| JS behavior without browser | Node execution probe in `conformance_sovereign._validate_javascript` (evidence level 3, BEHAVIORAL) |
| Real rendering engine | Chrome 140 + Chromium Edge 140 headless probes (this standard, §1–§3) |

A web target is "premium" only when all layers pass.
