"""Living layer generator for premium web targets.

Emits a self-contained ES module implementing the "Living" visual dimension:
an ambient animated backdrop driven by ``requestAnimationFrame`` with an
honest capability fallback chain:

    WebGL  ->  Canvas2D  ->  CSS gradient  ->  static nothing

Every downgrade is reported through ``console.info`` so the running artifact
always tells the truth about what it could express.

Modes:
    - ``living``   animated atmosphere (default)
    - ``clear``    flat surface, no ambience
    - ``symbolic`` static generative pattern (no animation)

Reduced motion: when ``(prefers-reduced-motion: reduce)`` matches, the
module renders exactly one static frame regardless of mode.
"""

from ..data_model import RealizationTarget, SIRGraph

_LIVING_JS = """// === Orren Living Layer ===
// Honest-capability ambient backdrop: WebGL -> Canvas2D -> CSS -> none.
export const MODES = ['living', 'clear', 'symbolic'];

function detectRenderer(canvas) {
  let gl = null;
  try { gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl'); } catch (e) { gl = null; }
  if (gl) return { kind: 'webgl', ctx: gl };
  let ctx2d = null;
  try { ctx2d = canvas.getContext('2d'); } catch (e) { ctx2d = null; }
  if (ctx2d) return { kind: 'canvas2d', ctx: ctx2d };
  return { kind: 'css', ctx: null };
}

export function createLivingLayer(canvas, options = {}) {
  if (!canvas || canvas.tagName !== 'CANVAS') {
    console.info('[Orren][living] no canvas element; layer disabled');
    return null;
  }
  const renderer = detectRenderer(canvas);
  console.info(`[Orren][living] renderer: ${renderer.kind}`);
  const reduceMotion = typeof matchMedia === 'function' &&
    matchMedia('(prefers-reduced-motion: reduce)').matches;

  const state = {
    mode: options.mode && MODES.includes(options.mode) ? options.mode : 'living',
    raf: 0,
    running: false,
    t0: performance.now(),
  };

  function paintFrame(now) {
    const t = (now - state.t0) / 1000;
    if (renderer.kind === 'webgl') paintWebGL(renderer.ctx, canvas, state.mode, t);
    else if (renderer.kind === 'canvas2d') paint2D(renderer.ctx, canvas, state.mode, t);
    // css renderer needs no frames; gradient applied once below.
  }

  function applyStatic() {
    if (renderer.kind === 'css') {
      canvas.style.background =
        'radial-gradient(ellipse at 50% 0%, rgba(255,255,255,0.06), transparent 70%)';
      canvas.style.opacity = '0.7';
    } else {
      paintFrame(state.t0);
    }
  }

  function loop(now) {
    if (!state.running) return;
    paintFrame(now);
    state.raf = requestAnimationFrame(loop);
  }

  function start() {
    if (state.running || renderer.kind === 'css') return;
    if (reduceMotion) { applyStatic(); return; }
    state.running = true;
    state.t0 = performance.now();
    state.raf = requestAnimationFrame(loop);
  }

  function stop() {
    state.running = false;
    if (state.raf) cancelAnimationFrame(state.raf);
    state.raf = 0;
  }

  function setMode(mode) {
    if (!MODES.includes(mode)) {
      console.warn(`[Orren][living] unknown mode '${mode}'; keeping '${state.mode}'`);
      return state.mode;
    }
    state.mode = mode;
    if (mode === 'clear') stop();
    else if (mode === 'symbolic') { stop(); applyStatic(); }
    else start();
    canvas.dispatchEvent(new CustomEvent('orren:living-mode', {
      detail: { mode: state.mode, renderer: renderer.kind },
    }));
    return state.mode;
  }

  function onVisibility() {
    if (document.hidden) stop();
    else if (state.mode === 'living') start();
  }
  document.addEventListener('visibilitychange', onVisibility);

  setMode(state.mode);

  return {
    get mode() { return state.mode; },
    renderer: renderer.kind,
    setMode,
    destroy() {
      document.removeEventListener('visibilitychange', onVisibility);
      stop();
      canvas.width = 0;
    },
  };
}

function paintWebGL(gl, canvas, mode, t) {
  const w = canvas.width, h = canvas.height;
  gl.viewport(0, 0, w, h);
  const wave = mode === 'living' ? 0.5 + 0.5 * Math.sin(t * 0.8) : 0.35;
  gl.clearColor(0.06 * wave + 0.02, 0.09 * wave + 0.03, 0.16 * wave + 0.05, 1.0);
  gl.clear(gl.COLOR_BUFFER_BIT);
}

function paint2D(ctx, canvas, mode, t) {
  const w = canvas.width, h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  if (mode === 'clear') return;
  const grad = ctx.createLinearGradient(0, 0, w * 0.4, h);
  const shift = mode === 'living' ? Math.sin(t * 0.6) * 40 : 0;
  grad.addColorStop(0, `rgba(46, 204, 113, ${mode === 'symbolic' ? 0.10 : 0.14})`);
  grad.addColorStop(1, 'rgba(15, 23, 42, 0)');
  ctx.fillStyle = grad;
  for (let i = 0; i < 3; i++) {
    const y = h * (0.25 + i * 0.25) + shift * (i + 1) * 0.3;
    ctx.fillRect(0, y - 40, w, 80);
  }
}

// Auto-wire: attaches to #orren-living-canvas when present.
export function autoWireLivingLayer() {
  const canvas = document.getElementById('orren-living-canvas');
  if (!canvas) return null;
  const layer = createLivingLayer(canvas);
  if (layer) window.OrrenApp = Object.assign(window.OrrenApp || {}, { living: layer });
  return layer;
}
"""


def generate_living_js(graph: SIRGraph, target: RealizationTarget) -> str:
    """Return the Living-layer ES module source for this target."""
    return _LIVING_JS


def generate_web_gl(graph: SIRGraph, target: RealizationTarget) -> str:
    """Alias kept for symmetry with the other backend entry points."""
    return generate_living_js(graph, target)


LIVING_CANVAS_HTML = (
    '  <canvas id="orren-living-canvas" aria-hidden="true" '
    'data-semantic-id="orren.living_backdrop"></canvas>'
)

__all__ = ["generate_web_gl", "generate_living_js", "LIVING_CANVAS_HTML"]
