/**
 * Orren-generated ES2022 JavaScript module
 * Target: web_interface (HTML/CSS/JS)
 * Preservation score: 0.83
 */

'use strict';

const OrrenConfig = {
  maxTransitionHistory: 100,
  maxEventListeners: 50,
  persistenceKey: 'orren:app_state',
  debug: true,
};

export { OrrenConfig };

/* --- State Machines (from behavioral/conditional/temporal) --- */
export class OrrenFSM {
    constructor(initialState, nodeId) {
        this.state = initialState;
        this.nodeId = nodeId;
        this.history = [initialState];
        this.guards = new Map();
    }

    registerGuard(state, event, fn) {
        const key = `${state}|${event}`;
        this.guards.set(key, fn);
    }

    transition(event, payload = {}) {
        const key = `${this.state}|${event}`;
        const guard = this.guards.get(key);
        if (guard && !guard(payload)) {
            console.debug(`[${this.nodeId}] transition guarded: ${event}`);
            return false;
        }
        const prev = this.state;
        this.history.push(this.state);
        console.debug(`[${this.nodeId}] ${prev} --(${event})--> ${payload.nextState || prev}`);
        this.state = payload.nextState || this.state;
        this.emitTransition(event, prev, payload);
        return true;
    }

    emitTransition(event, fromState, payload) {
        const detail = {
            from: fromState,
            to: this.state,
            event,
            nodeId: this.nodeId,
            ...payload,
        };
        window.dispatchEvent(new CustomEvent('orren:transition', { detail }));
        document
            .getElementById(this.nodeId)
            ?.dispatchEvent(new CustomEvent('orren:state', { detail }));
    }

    rollback() {
        if (this.history.length > 1) {
            this.state = this.history.pop();
            return true;
        }
        return false;
    }

    get currentState() {
        return this.state;
    }
}

// --- State machine instances (from behavioral/conditional/temporal) ---
// lifecycle: True
// lifecycle states for microphone_control: idle, active, recording, processing, activates_double_click, volume_down × 2
const fsm_microphone_application_home_microphone_control = new OrrenFSM('idle', 'microphone-application-home-microphone-control');
// State: idle
// State: active
// State: recording
// State: processing
// State: activates_double_click
// State: volume_down × 2
fsm_microphone_application_home_microphone_control.registerGuard('idle', 'activation_intent', (payload) => { payload.nextState = 'active'; return true; });
fsm_microphone_application_home_microphone_control.registerGuard('recording', 'user_stop_signal', (payload) => { payload.nextState = 'processing'; return true; });
fsm_microphone_application_home_microphone_control.registerGuard('idle', 'lifecycle', (payload) => { payload.nextState = 'active'; return true; });
fsm_microphone_application_home_microphone_control.registerGuard('active', 'lifecycle', (payload) => { payload.nextState = 'recording'; return true; });
fsm_microphone_application_home_microphone_control.registerGuard('recording', 'lifecycle', (payload) => { payload.nextState = 'processing'; return true; });
fsm_microphone_application_home_microphone_control.registerGuard('processing', 'lifecycle', (payload) => { payload.nextState = 'idle'; return true; });
fsm_microphone_application_home_microphone_control.registerGuard('processing', 'dblclick', (payload) => { payload.nextState = 'activates_double_click'; return true; });
fsm_microphone_application_home_microphone_control.registerGuard('*', 'volume_down × 2', (payload) => { payload.nextState = 'bridge_volume_down × 2'; return true; });


/* --- Event Handlers (from conditional dimension) --- */
export function wireUpEvents() {
    // --- microphone_application.home.microphone_control ---
    const el_microphone_application_home_microphone_control = document.getElementById('microphone-application-home-microphone-control');
    if (!el_microphone_application_home_microphone_control) {
        console.warn('Element not found: microphone-application-home-microphone-control');
    }
    // microphone_control activates on double_click -> dblclick
    el_microphone_application_home_microphone_control?.addEventListener('dblclick', (evt) => { fsm_microphone_application_home_microphone_control?.transition('dblclick', { nextState: 'activates_double_click'.replace(/[^a-zA-Z0-9_]/g, '_') }); console.log('microphone_control activates via dblclick'); });
    // BRIDGE: 'volume_down × 2' requires native bridge (e.g. media keys / device API).
    el_microphone_application_home_microphone_control?.addEventListener('volume_down_×_2', () => { fsm_microphone_application_home_microphone_control?.transition('volume_down_×_2'); console.warn('BRIDGE: volume_down × 2 not available in browser'); });

}
export default wireUpEvents;

// --- Temporal sequences (from temporal dimension) ---
// Temporal sequence for microphone_application: ['activation -> recording on user_intent']
export function temporalSequence_microphone_application_0() {
  let delay = 0;
  setTimeout(() => {
    console.debug('temporal step 0: activation -> recording on user_intent');
    window.dispatchEvent(new CustomEvent('orren:temporal', {
      detail: { nodeId: 'microphone-application', step: 0, event: 'activation -> recording on user_intent' }
    }));
  }, delay);
  delay += 200;
}

// Temporal sequence for microphone_application: ['recording -> stops on user_stop_signal']
export function temporalSequence_microphone_application_1() {
  let delay = 0;
  setTimeout(() => {
    console.debug('temporal step 0: recording -> stops on user_stop_signal');
    window.dispatchEvent(new CustomEvent('orren:temporal', {
      detail: { nodeId: 'microphone-application', step: 0, event: 'recording -> stops on user_stop_signal' }
    }));
  }, delay);
  delay += 200;
}

// Temporal sequence for microphone_application: ['original_audio persists beyond transcription']
export function temporalSequence_microphone_application_2() {
  let delay = 0;
  setTimeout(() => {
    console.debug('temporal step 0: original_audio persists beyond transcription');
    window.dispatchEvent(new CustomEvent('orren:temporal', {
      detail: { nodeId: 'microphone-application', step: 0, event: 'original_audio persists beyond transcription' }
    }));
  }, delay);
  delay += 200;
}

// --- Temporal bootstrap (self-starting sequences) ---
export function startTemporalSequences() {
  const sequenceFns = [temporalSequence_microphone_application_0, temporalSequence_microphone_application_1, temporalSequence_microphone_application_2];
  for (const fn of sequenceFns) {
    try { fn(); } catch (e) {
      console.warn('[Orren] temporal sequence failed:', e);
    }
  }
}

// --- Relational links (from relational dimension) ---
export function wireUpRelationalLinks() {
  // microphone_control --feeds--> device_microphone
  const srcEl_microphone_control = document.getElementById('microphone-control');
  const tgtEl_device_microphone = document.getElementById('device-microphone');
  if (srcEl_microphone_control && tgtEl_device_microphone) {
    srcEl_microphone_control.setAttribute('data-relates-to', 'device_microphone');
    tgtEl_device_microphone.setAttribute('data-related-from', 'microphone_control');
    srcEl_microphone_control.addEventListener('click', () => {
      tgtEl_device_microphone.scrollIntoView({ behavior: 'smooth' });
      tgtEl_device_microphone.dispatchEvent(new CustomEvent('orren:relate', {
        detail: { relation: 'feeds', source: 'microphone_control', target: 'device_microphone' }
      }));
    });
  }

}
// --- State persistence to localStorage ---
export function saveAppState(state) {
  try {
    localStorage.setItem(OrrenConfig.persistenceKey, JSON.stringify(state));
  } catch (e) {
    console.warn('[Orren] Persistence failed:', e);
  }
}

export function loadAppState() {
  try {
    const saved = localStorage.getItem(OrrenConfig.persistenceKey);
    return saved ? JSON.parse(saved) : null;
  } catch (e) {
    console.warn('[Orren] State recovery failed:', e);
    return null;
  }
}

// --- Error handling ---
window.addEventListener('error', (evt) => {
  const boundary = document.getElementById('orren-error-boundary');
  if (boundary) { boundary.hidden = false; }
  console.error('[Orren] Unhandled error:', evt.error);
});

// --- Bridge markers (native capabilities not available in browser) ---
// BRIDGE: device_microphone - requires native bridge, not available in browser.
// BRIDGE: audio_storage - requires native bridge, not available in browser.
// BRIDGE: vibe.aesthetic - requires native bridge, not available in browser.
// BRIDGE: device_microphone - requires native bridge, not available in browser.
// BRIDGE: audio_storage - requires native bridge, not available in browser.

