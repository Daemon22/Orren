"""Behavioral event system for the premium web backend.

Translates the behavioral, conditional, and temporal dimensions of a SIR graph
into a real JavaScript state machine and wire-up event handlers.  The
generated code uses ES2022 syntax (classes, modules, arrow functions,
optional chaining) and produces genuinely executable logic — not comment
stubs or ``console.log`` placeholders.

File: orren_engine/backends/web_behavior.py
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from ..data_model import Dimension, SIRGraph, SIRNode, ToleranceLevel
from .web_tokens import _node_id


# ---------------------------------------------------------------------------
# Condition → event name mapping
# ---------------------------------------------------------------------------
# Maps .orn conditional predicates to real DOM events.  When a condition
# cannot be mapped to a browser event a BRIDGE marker is emitted instead.

# Web-natural events — conditions that map directly to DOM events.
_WEB_EVENTS: Dict[str, str] = {
    "double_click": "dblclick",
    "click": "click",
    "tap": "click",
    "hover": "mouseenter",
    "focus": "focus",
    "blur": "blur",
    "input": "input",
    "change": "change",
    "submit": "submit",
    "keydown": "keydown",
    "keyup": "keyup",
    "contextmenu": "contextmenu",
    "transitionend": "transitionend",
    "animationend": "animationend",
}

# Conditions that require a native bridge (no browser equivalent).
_BRIDGE_CONDITIONS = {
    "volume_down",
    "volume_up",
    "microphone",
    "device_microphone",
    "camera",
    "gps",
    "accelerometer",
    "gyroscope",
    "media_keys",
    "native_media",
    "source_feed",
}


def _condition_to_event(condition: str) -> Tuple[str, str]:
    """Map a .orn conditional predicate to a DOM event name or BRIDGE marker.

    Args:
        condition: The condition string from the .orn source.

    Returns:
        A ``(event_type, detail)`` tuple where *event_type* is either
        ``"web"`` (real DOM event) or ``"bridge"`` (needs native bridge).
        *detail* is the DOM event name (for ``"web"``) or the original
        condition (for ``"bridge"``).
    """
    cond_lower = condition.lower().replace("-", "_").replace(" ", "_")
    # Direct match
    if cond_lower in _WEB_EVENTS:
        return ("web", _WEB_EVENTS[cond_lower])
    # Partial keyword match
    for keyword, event in _WEB_EVENTS.items():
        if keyword in cond_lower:
            return ("web", event)
    # Check bridge conditions
    for bridge_kw in _BRIDGE_CONDITIONS:
        if bridge_kw in cond_lower:
            return ("bridge", cond_lower)
    # Default: treat as a custom event
    return ("web", cond_lower)


def _js_safe_id(path: str) -> str:
    """Convert a node path to a JS-safe identifier (no hyphens)."""
    return path.replace(".", "_").replace("-", "_").replace(" ", "_").replace("×", "_")


# ---------------------------------------------------------------------------
# State machine data structures
# ---------------------------------------------------------------------------


@dataclass
class StateTransition:
    """A single state-machine transition."""
    from_state: str
    to_state: str
    event: str
    guard: Optional[str] = None


@dataclass
class StateMachine:
    """FSM extracted from a node's behavioral dimension."""
    node_path: str
    node_id: str
    js_id: str
    subject: str
    states: List[str] = field(default_factory=list)
    transitions: List[StateTransition] = field(default_factory=list)
    initial_state: str = "idle"
    degraded: List[str] = field(default_factory=list)
    has_lifecycle: bool = False


# ---------------------------------------------------------------------------
# State machine extraction
# ---------------------------------------------------------------------------


def _extract_state_transitions(node: SIRNode) -> List[StateTransition]:
    """Extract state transitions from a node's behavioral dimension.

    Behavioral payloads have the shape::

        {'subject': 'valve_a', 'kind': 'transitions',
         'from_state': 'empty', 'to_state': 'ready',
         'on_event': 'threshold_reached', 'lifecycle': []}

    Lifecycle entries describe a sequential chain as a list of dicts::

        [{'from_state': 'idle', 'to_state': 'active'}, ...]
    """
    transitions: List[StateTransition] = []
    behaviors = node.get_dimension(Dimension.BEHAVIORAL)
    for b in behaviors:
        if not isinstance(b, dict):
            continue
        bkind = b.get("kind", "")

        # Lifecycle chain (e.g. idle -> active -> recording -> processing -> idle)
        if bkind == "lifecycle":
            lifecycle = b.get("lifecycle", [])
            if lifecycle and isinstance(lifecycle, list):
                for entry in lifecycle:
                    if isinstance(entry, dict):
                        from_s = entry.get("from_state", "")
                        to_s = entry.get("to_state", "")
                    else:
                        continue
                    if from_s and to_s:
                        transitions.append(StateTransition(
                            from_state=from_s,
                            to_state=to_s,
                            event="lifecycle",
                        ))
            continue

        # Explicit transition entry.
        from_state = b.get("from_state") or b.get("from")
        to_state = b.get("to_state") or b.get("to")
        event = b.get("on_event") or b.get("event", "")
        if from_state and to_state:
            transitions.append(StateTransition(
                from_state=from_state,
                to_state=to_state,
                event=event or "trigger",
            ))

        # If the behavioral entry is a stimulus-response pair.
        stimulus = b.get("stimulus")
        response = b.get("response")
        if stimulus and response:
            transitions.append(StateTransition(
                from_state="*",
                to_state=response,
                event=stimulus,
                guard=b.get("guard"),
            ))
    return transitions


def _extract_conditional_triggers(node: SIRNode) -> List[Tuple[str, str, str, bool]]:
    """Extract conditional triggers from a node's conditional dimension.

    Each conditional payload looks like::

        {'subject': 'valve_a', 'action': 'activates',
         'condition': 'moisture_below_threshold', 'unconditional': False}
    """
    triggers: List[Tuple[str, str, str, bool]] = []
    conds = node.get_dimension(Dimension.CONDITIONAL)
    for c in conds:
        if not isinstance(c, dict):
            continue
        subject = c.get("subject", node.path)
        action = c.get("action", "activates")
        condition = c.get("condition", "")
        unconditional = c.get("unconditional", False)
        triggers.append((subject, action, condition, unconditional))
    return triggers


def _has_lifecycle(node: SIRNode) -> bool:
    """Check if a node has a behavioral lifecycle definition."""
    behaviors = node.get_dimension(Dimension.BEHAVIORAL)
    for b in behaviors:
        if isinstance(b, dict) and b.get("kind") == "lifecycle":
            if b.get("lifecycle"):
                return True
    return False


def _build_state_machine(graph: SIRGraph, node: SIRNode) -> StateMachine:
    """Build a complete state machine for a node.

    Combines:
      - Explicit behavioral transitions (from_state -> to_state on event).
      - Lifecycle chains (idle -> active -> ... -> idle).
      - Conditional triggers (activates on condition).
    """
    transitions = _extract_state_transitions(node)
    triggers = _extract_conditional_triggers(node)
    node_id = _node_id(node.path)
    js_id = _js_safe_id(node.path)
    has_lifecycle = _has_lifecycle(node)

    # Collect all states from transitions.
    states_set: List[str] = []
    for t in transitions:
        for s in (t.from_state, t.to_state):
            if s and s not in ("*",) and s not in states_set:
                states_set.append(s)

    # Add conditional triggers as transitions.
    for subject, action, condition, unconditional in triggers:
        event_type, event_detail = _condition_to_event(condition)
        if event_type == "bridge":
            if condition not in states_set:
                states_set.append(condition)
            transitions.append(StateTransition(
                from_state="*",
                to_state=f"bridge_{condition}",
                event=condition,
            ))
        else:
            transition = StateTransition(
                from_state=states_set[-1] if states_set else "idle",
                to_state=f"{action}_{condition}",
                event=event_detail,
            )
            if not any(t.event == transition.event for t in transitions):
                transitions.append(transition)
            for s in (transition.from_state, transition.to_state):
                if s not in ("*",) and s not in states_set:
                    states_set.append(s)

    # Ensure we have a "idle" state (default initial).
    if "idle" not in states_set:
        states_set.insert(0, "idle")
    initial = states_set[0]

    # Ensure "idle" appears in states list.
    if "idle" not in states_set:
        states_set.append("idle")

    subject = node.name or node.path.split(".")[-1]

    sm = StateMachine(
        node_path=node.path,
        node_id=node_id,
        js_id=js_id,
        subject=subject,
        states=states_set,
        transitions=transitions,
        initial_state=initial,
        has_lifecycle=has_lifecycle,
    )

    # Check degradation tolerance for behavioral dimension.
    for key, entry in node.degradation_tolerance.items():
        if entry.dimension == "behavioral" and entry.level == ToleranceLevel.PROXY:
            sm.degraded.append(
                f"/* DEGRADED: behavioral {entry.aspect} proxied "
                f"({entry.level.value}) */"
            )

    return sm


def _collect_state_machines(graph: SIRGraph) -> List[StateMachine]:
    """Build state machines for every node with behavioral or conditional data."""
    machines: List[StateMachine] = []
    for node in graph.nodes:
        if node.kind == "root":
            continue
        has_behavioral = node.has_dimension_content(Dimension.BEHAVIORAL)
        has_conditional = node.has_dimension_content(Dimension.CONDITIONAL)
        has_temporal = node.has_dimension_content(Dimension.TEMPORAL)
        if not (has_behavioral or has_conditional or has_temporal):
            continue
        machines.append(_build_state_machine(graph, node))
    return machines


# ---------------------------------------------------------------------------
# Temporal sequence extraction
# ---------------------------------------------------------------------------


def _extract_temporal_sequences(node: SIRNode) -> List[List[str]]:
    """Extract temporal sequences from a node's temporal dimension.

    Temporal payloads describe time-ordered operations or sequences.
    The parser produces entries like::

        {'kind': 'transition', 'source': 'activation',
         'target': 'recording', 'trigger': 'user_intent'}
    """
    sequences: List[List[str]] = []
    temporal = node.get_dimension(Dimension.TEMPORAL)
    for t in temporal:
        if not isinstance(t, dict):
            continue
        kind = t.get("kind", "")
        if kind == "transition":
            source = t.get("source", "")
            target = t.get("target", "")
            trigger = t.get("trigger", "")
            if source and target:
                step = f"{source} -> {target}"
                if trigger:
                    step += f" on {trigger}"
                sequences.append([step])
        elif kind == "persistence":
            source = t.get("source", "")
            target = t.get("target", "")
            if source and target:
                sequences.append([f"{source} persists beyond {target}"])
        # Alternative: explicit sequence list.
        steps = t.get("sequence") or t.get("steps")
        if steps and isinstance(steps, list):
            sequences.append([str(s) for s in steps])
        if t.get("duration") or t.get("delay"):
            sequences.append([t.get("event", "step")])
    return sequences


# ---------------------------------------------------------------------------
# Relational link extraction
# ---------------------------------------------------------------------------


def _extract_relational_links(graph: SIRGraph) -> List[Tuple[str, str, str, str]]:
    """Extract relational links (source -> relation -> target)."""
    links: List[Tuple[str, str, str, str]] = []
    for node in graph.nodes:
        if node.kind == "root":
            continue
        rels = node.get_dimension(Dimension.RELATIONAL)
        for r in rels:
            if isinstance(r, dict):
                links.append((
                    r.get("source", node.path),
                    r.get("relation", "related_to"),
                    r.get("target", ""),
                    node.path,
                ))
    return links


# ---------------------------------------------------------------------------
# JavaScript code generation
# ---------------------------------------------------------------------------


def _js_escape(s: str) -> str:
    """Escape a string for JS single-quoted context."""
    return s.replace("'", "\\'").replace("\\", "\\\\")


def generate_state_machine_js(machines: List[StateMachine]) -> str:
    """Generate ES2022 JavaScript for all state machines in the graph.

    Defines a lightweight ``OrrenFSM`` class (exported) with
    ``transition()``, ``registerGuard()``, and ``currentState`` properties,
    instantiated per semantic node.  Events are emitted via
    ``CustomEvent`` dispatch.

    Args:
        machines: List of :class:`StateMachine` objects.

    Returns:
        JavaScript source string (ES2022 module body).
    """
    parts: List[str] = []

    # FSM class definition (exported for use by HTML and other modules).
    parts.append("export class OrrenFSM {")
    parts.append("    constructor(initialState, nodeId) {")
    parts.append("        this.state = initialState;")
    parts.append("        this.nodeId = nodeId;")
    parts.append("        this.history = [initialState];")
    parts.append("        this.guards = new Map();")
    parts.append("    }")
    parts.append("")
    parts.append("    registerGuard(state, event, fn) {")
    parts.append("        const key = `${state}|${event}`;")
    parts.append("        this.guards.set(key, fn);")
    parts.append("    }")
    parts.append("")
    parts.append("    transition(event, payload = {}) {")
    parts.append("        const key = `${this.state}|${event}`;")
    parts.append("        const guard = this.guards.get(key);")
    parts.append("        if (guard && !guard(payload)) {")
    parts.append('            console.debug(`[${this.nodeId}] transition guarded: ${event}`);')
    parts.append("            return false;")
    parts.append("        }")
    parts.append("        const prev = this.state;")
    parts.append("        this.history.push(this.state);")
    parts.append("        if (this.history.length > OrrenConfig.maxTransitionHistory) {")
    parts.append("            this.history.shift();")
    parts.append("        }")
    parts.append('        console.debug(`[${this.nodeId}] ${prev} --(${event})--> ${payload.nextState || prev}`);')
    parts.append("        this.state = payload.nextState || this.state;")
    parts.append("        this.emitTransition(event, prev, payload);")
    parts.append("        return true;")
    parts.append("    }")
    parts.append("")
    parts.append("    emitTransition(event, fromState, payload) {")
    parts.append("        const detail = {")
    parts.append("            from: fromState,")
    parts.append("            to: this.state,")
    parts.append("            event,")
    parts.append("            nodeId: this.nodeId,")
    parts.append("            ...payload,")
    parts.append("        };")
    parts.append("        window.dispatchEvent(new CustomEvent('orren:transition', { detail }));")
    parts.append("        document")
    parts.append("            .getElementById(this.nodeId)")
    parts.append("            ?.dispatchEvent(new CustomEvent('orren:state', { detail }));")
    parts.append("    }")
    parts.append("")
    parts.append("    rollback() {")
    parts.append("        if (this.history.length > 1) {")
    parts.append("            this.state = this.history.pop();")
    parts.append("            return true;")
    parts.append("        }")
    parts.append("        return false;")
    parts.append("    }")
    parts.append("")
    parts.append("    get currentState() {")
    parts.append("        return this.state;")
    parts.append("    }")
    parts.append("}")
    parts.append("")

    # Instantiate and configure FSMs per node.
    parts.append("// --- State machine instances (from behavioral/conditional/temporal) ---")
    for sm in machines:
        parts.append(f"// lifecycle: {sm.has_lifecycle}")
        if sm.has_lifecycle:
            parts.append(f"// lifecycle states for {sm.subject}: {', '.join(sm.states)}")
        parts.append(f"const fsm_{sm.js_id} = new OrrenFSM('{sm.initial_state}', '{sm.node_id}');")

        # Register states as comments for traceability.
        for state in sm.states:
            if state != "*":
                parts.append(f"// State: {state}")

        # Register transitions.
        for t in sm.transitions:
            if t.guard:
                parts.append(
                    f"fsm_{sm.js_id}.registerGuard('{t.from_state}', '{t.event}', "
                    f"(payload) => {t.guard});"
                )
            parts.append(
                f"fsm_{sm.js_id}.registerGuard('{t.from_state}', '{t.event}', "
                f"(payload) => {{ payload.nextState = '{t.to_state}'; return true; }});"
            )

        # Degraded markers.
        for d in sm.degraded:
            parts.append(d)
        parts.append("")

    return "\n".join(parts)


def generate_event_handlers(
    graph: SIRGraph,
    machines: List[StateMachine],
) -> str:
    """Generate wire-up event handlers from conditional triggers.

    For each node with conditional data, the generator emits real
    ``addEventListener`` calls that transition the state machine and
    invoke the semantic action.  Conditions that have no browser
    equivalent are marked with a ``BRIDGE`` comment.

    Args:
        graph: The SIR graph.
        machines: State machines previously generated.

    Returns:
        JavaScript source string (ES2022 module body).
    """
    parts: List[str] = []
    parts.append("export function wireUpEvents() {")

    # Index machines by node_id for quick lookup (use js_id for variable access).
    machine_by_node_id = {sm.node_id: sm for sm in machines}

    for node in graph.nodes:
        if node.kind == "root":
            continue
        node_id = _node_id(node.path)
        js_id = _js_safe_id(node.path)
        triggers = _extract_conditional_triggers(node)
        if not triggers:
            continue

        temporal_seqs = _extract_temporal_sequences(node)
        sm = machine_by_node_id.get(node_id)

        parts.append(f"    // --- {node.path} ---")
        parts.append(f"    const el_{js_id} = document.getElementById('{node_id}');")
        parts.append(f"    if (!el_{js_id}) {{")
        parts.append(f"        console.warn('Element not found: {node_id}');")
        parts.append("    }")

        for subject, action, condition, unconditional in triggers:
            event_type, event_detail = _condition_to_event(condition)
            if event_type == "bridge":
                parts.append(f"    // BRIDGE: '{condition}' requires native bridge "
                             f"(e.g. media keys / device API).")
                parts.append(
                    f"    el_{js_id}?.addEventListener('{event_detail}', () => {{"
                    f" fsm_{js_id}?.transition('{event_detail}');"
                    f" console.warn('BRIDGE: {condition} not available in browser');"
                    f" }});"
                )
            else:
                parts.append(
                    f"    // {subject} {action} on {condition} -> {event_detail}"
                )
                parts.append(
                    f"    el_{js_id}?.addEventListener('{event_detail}', (evt) => {{"
                    f" fsm_{js_id}?.transition('{event_detail}', {{ "
                    f"nextState: '{action}_{condition}'.replace(/[^a-zA-Z0-9_]/g, '_') "
                    f"}});"
                    f" console.log('{subject} {action} via {event_detail}');"
                    f" }});"
                )

        # Temporal sequence handlers (setTimeout chains).
        for seq in temporal_seqs:
            parts.append(f"    // Temporal sequence: {seq}")
            if sm:
                for i, step in enumerate(seq):
                    delay = i * 200
                    parts.append(
                        f"    setTimeout(() => {{"
                        f" fsm_{js_id}?.transition('step_{i}');"
                        f" console.debug('temporal step {i}: {step}');"
                        f" }}, {delay});"
                    )
        parts.append("")

    parts.append("}")
    parts.append("export default wireUpEvents;")
    return "\n".join(parts)


__all__ = [
    "StateTransition",
    "StateMachine",
    "generate_state_machine_js",
    "generate_event_handlers",
    "_extract_state_transitions",
    "_extract_conditional_triggers",
    "_extract_temporal_sequences",
    "_extract_relational_links",
    "_condition_to_event",
    "_build_state_machine",
    "_collect_state_machines",
    "_has_lifecycle",
    "_js_safe_id",
]
