"""Backend capability manifests — declaring what each language can express.

A :class:`BackendManifest` is the *realization contract* for a language: it
lists the semantic operations the backend genuinely supports, the type
mappings between Orren's type system and the target, the runtime
dependencies, and — critically — the cases that are *unsupported* (which
degrade to PROXY/BRIDGE markers rather than a false PASS).

The conformance harness consults the manifest **before** validating an
artifact.  If a required IR operation is absent from
``supported_operations`` the harness **fails closed** rather than emitting a
placeholder.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

__all__ = ["BackendManifest", "manifest_for_language", "ALL_MANIFESTS"]


@dataclass(frozen=True)
class BackendManifest:
    """Declaration of what a realization backend can genuinely express.

    Attributes:
        backend_id: Stable identifier matching the language label used in
            ``.orn`` ``realize:`` blocks (e.g. ``"rust"``, ``"python"``).
        supported_operations: Names of Realization IR operations the backend
            handles natively without degradation (e.g. ``"state_machine"``,
            ``"event_handling"``).
        type_mappings: Map from Orren semantic type names to target-language
            type names (e.g. ``{"boolean": "bool"}`` for Rust).
        runtime_dependencies: External packages or libraries the generated
            code depends on at runtime.
        platform_constraints: Arbitrary platform-specific metadata (e.g.
            ``{"min_memory_mb": 64}`` for embedded C).
        unsupported_cases: Semantic aspects that **cannot** be expressed and
            will degrade to PROXY/BRIDGE.  Each is a short descriptor.
        validation_command: Shell command template used to validate generated
            source for this backend (empty list means "no compiler check").
        preservation_score: Float in [0, 1] expressing how faithfully the
            backend preserves the full SIR semantics.  ``1.0`` = lossless,
            ``0.0`` = proxy-only.
    """

    backend_id: str
    supported_operations: List[str] = field(default_factory=list)
    type_mappings: Dict[str, str] = field(default_factory=dict)
    runtime_dependencies: List[str] = field(default_factory=list)
    platform_constraints: Dict[str, Any] = field(default_factory=dict)
    unsupported_cases: List[str] = field(default_factory=list)
    validation_command: List[str] = field(default_factory=list)
    preservation_score: float = 1.0
    zaryel_support: bool = False
    supported_canvases: List[str] = field(default_factory=list)
    supported_layouts: List[str] = field(default_factory=list)
    supported_inputs: List[str] = field(default_factory=list)
    supported_outputs: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Language normalisation
# ---------------------------------------------------------------------------

# Map various ``.orn`` language labels (and their lower-cased forms) to the
# canonical manifest ``backend_id``.  Compound labels like "HTML/CSS/JS" are
# resolved to the dominant web target language used by the conformance
# harness.
_LANGUAGE_ALIASES: Dict[str, str] = {
    "rust": "rust",
    "go": "go",
    "golang": "go",
    "c": "c",
    "c++": "c",
    "cpp": "c",
    "typescript": "typescript",
    "ts": "typescript",
    "javascript": "javascript",
    "js": "javascript",
    "html/css/js": "javascript",
    "html/css/js (browser)": "javascript",
    "html/css/js": "javascript",
    "web": "javascript",
    "html": "html",
    "css": "css",
    "webaudio": "webaudio",
    "webaudio api": "webaudio",
    "swift": "swift",
    "kotlin": "kotlin",
    "kotlin/mobile": "kotlin",
    "latex": "latex",
    "tex": "latex",
    "python": "python",
    "conformance specification": "text",
}


def _normalize_language(language: str) -> str:
    """Map a target language label to a canonical backend id.

    Args:
        language: The raw language string from a RealizationTarget (e.g.
            ``"HTML/CSS/JS"``, ``"C"``, ``"WebAudio API"``).

    Returns:
        A canonical, lower-case backend identifier, or the lower-cased input
        when no alias matches.
    """
    normalized = language.lower().strip()
    return _LANGUAGE_ALIASES.get(normalized, normalized)


# ---------------------------------------------------------------------------
# Manifest registry — one per language
# ---------------------------------------------------------------------------

_MANIFESTS: Dict[str, BackendManifest] = {
    "rust": BackendManifest(
        backend_id="rust",
        supported_operations=[
            "state_machine", "event_handling", "data_persistence",
            "deterministic_runtime", "memory_safety", "error_propagation",
            "process_dict_contract",
        ],
        type_mappings={
            "boolean": "bool",
            "integer": "i64",
            "float": "f64",
            "string": "String",
            "array": "Vec",
            "map": "HashMap",
        },
        runtime_dependencies=[],
        platform_constraints={"platforms": ["linux", "windows", "android"]},
        unsupported_cases=[
            "garbage_collection",
            "runtime_reflection",
            "dynamic_typing",
            "live_code_reload",
        ],
        validation_command=["rustc", "--edition", "2021", "--crate-type", "lib", "{file}"],
        preservation_score=1.0,
        zaryel_support=True,
        supported_canvases=["web_page", "server_api"],
        supported_layouts=["stack", "grid", "tabs", "masonry"],
        supported_inputs=["keyboard", "mouse", "gesture"],
        supported_outputs=["display", "audio"],
    ),
    "go": BackendManifest(
        backend_id="go",
        supported_operations=[
            "concurrent_state_machine", "event_handling", "channel_communication",
            "data_persistence", "garbage_collection", "error_propagation",
        ],
        type_mappings={
            "boolean": "bool",
            "integer": "int64",
            "float": "float64",
            "string": "string",
            "array": "[]",
            "map": "map",
        },
        runtime_dependencies=[],
        platform_constraints={"platforms": ["linux", "windows"]},
        unsupported_cases=[
            "zero_cost_abstractions",
            "manual_memory_management",
        ],
        validation_command=["go", "build", "-o", "/dev/null", "{file}"],
        preservation_score=0.95,
        zaryel_support=True,
        supported_canvases=["web_page", "server_api"],
        supported_layouts=["stack", "grid", "tabs"],
        supported_inputs=["keyboard", "mouse", "gesture"],
        supported_outputs=["display", "projection"],
    ),
    "c": BackendManifest(
        backend_id="c",
        supported_operations=[
            "state_machine", "hardware_io", "deterministic_runtime",
            "manual_memory_management", "fixed_time_allocation",
        ],
        type_mappings={
            "boolean": "_Bool",
            "integer": "int64_t",
            "float": "double",
            "string": "char*",
            "array": "[]",
            "map": "struct",
        },
        runtime_dependencies=["libc"],
        platform_constraints={
            "platforms": ["linux", "windows", "android"],
            "min_memory_mb": 64,
        },
        unsupported_cases=[
            "garbage_collection",
            "dynamic_typing",
            "exception_handling",
            "runtime_reflection",
        ],
        validation_command=["gcc", "-std=c11", "-fsyntax-only", "-Wall", "-Wextra", "{file}"],
        preservation_score=0.85,
        zaryel_support=True,
        supported_canvases=["embedded_display"],
        supported_layouts=["stack", "split"],
        supported_inputs=["touch", "sensor", "button"],
        supported_outputs=["display", "haptic", "led", "projection"],
    ),
    "python": BackendManifest(
        backend_id="python",
        supported_operations=[
            "state_machine", "event_handling", "data_persistence",
            "dynamic_typing", "garbage_collection", "runtime_reflection",
            "process_dict_contract", "retain_retrieve_contract",
        ],
        type_mappings={
            "boolean": "bool",
            "integer": "int",
            "float": "float",
            "string": "str",
            "array": "list",
            "map": "dict",
        },
        runtime_dependencies=["orren-engine-runtime"],
        platform_constraints={"platforms": ["linux", "windows", "android"]},
        unsupported_cases=[
            "manual_memory_management",
            "zero_cost_abstractions",
        ],
        validation_command=["python3", "-c", "import py_compile; py_compile.compile('{file}', doraise=True)"],
        preservation_score=0.97,
        zaryel_support=True,
        supported_canvases=["web_page", "desktop_app", "document"],
        supported_layouts=["stack", "grid", "split", "float", "tabs", "carousel", "masonry"],
        supported_inputs=["keyboard", "mouse", "touch", "gesture", "pen", "camera", "biometric", "button"],
        supported_outputs=["display", "audio", "print", "projection"],
    ),
    "typescript": BackendManifest(
        backend_id="typescript",
        supported_operations=[
            "state_machine", "event_handling", "typed_runtime",
            "data_persistence", "async_await",
        ],
        type_mappings={
            "boolean": "boolean",
            "integer": "number",
            "float": "number",
            "string": "string",
            "array": "Array<T>",
            "map": "Record<K, V>",
        },
        runtime_dependencies=[],
        platform_constraints={"platforms": ["linux", "windows", "android"]},
        unsupported_cases=[
            "manual_memory_management",
            "zero_cost_abstractions",
            "runtime_reflection",
        ],
        validation_command=["tsc", "--noEmit", "--strict", "{file}"],
        preservation_score=0.88,
        zaryel_support=True,
        supported_canvases=["web_page", "mobile_app"],
        supported_layouts=["stack", "grid", "split", "float", "tabs", "carousel", "masonry"],
        supported_inputs=["touch", "keyboard", "mouse", "voice", "gesture", "pen", "camera"],
        supported_outputs=["display", "audio", "haptic", "projection"],
    ),
    "javascript": BackendManifest(
        backend_id="javascript",
        supported_operations=[
            "event_handling", "async_await", "dynamic_typing",
            "dom_manipulation",
        ],
        type_mappings={
            "boolean": "boolean",
            "integer": "number",
            "float": "number",
            "string": "string",
            "array": "[]",
            "map": "Object",
        },
        runtime_dependencies=[],
        platform_constraints={"platforms": ["linux", "windows", "android"]},
        unsupported_cases=[
            "static_type_safety",
            "manual_memory_management",
            "zero_cost_abstractions",
            "runtime_reflection",
        ],
        validation_command=["node", "--check", "{file}"],
        preservation_score=0.75,
        zaryel_support=True,
        supported_canvases=["web_page", "mobile_app", "document"],
        supported_layouts=["stack", "grid", "split", "float", "tabs", "carousel", "masonry"],
        supported_inputs=["touch", "keyboard", "mouse", "voice", "gesture", "pen", "camera"],
        supported_outputs=["display", "audio", "haptic", "projection"],
    ),
    "html": BackendManifest(
        backend_id="html",
        supported_operations=["static_markup", "semantic_structure"],
        type_mappings={},
        runtime_dependencies=[],
        platform_constraints={"platforms": ["linux", "windows", "android"]},
        unsupported_cases=[
            "behavioral_execution",
            "state_management",
            "dynamic_content",
            "layout_computation",
        ],
        validation_command=[],
        preservation_score=0.60,
        zaryel_support=True,
        supported_canvases=["document"],
        supported_layouts=["stack", "grid", "split", "float", "tabs", "carousel", "masonry"],
        supported_inputs=["touch", "keyboard", "mouse", "voice", "gesture", "pen", "camera", "biometric"],
        supported_outputs=["display", "print", "projection"],
    ),
    "css": BackendManifest(
        backend_id="css",
        supported_operations=["static_styling", "layout_grid"],
        type_mappings={},
        runtime_dependencies=[],
        platform_constraints={"platforms": ["linux", "windows", "android"]},
        unsupported_cases=[
            "behavioral_execution",
            "dynamic_styling",
            "animation_logic",
            "form_architecture_only",
        ],
        validation_command=[],
        preservation_score=0.55,
        zaryel_support=True,
        supported_canvases=["web_page", "document"],
        supported_layouts=["stack", "grid", "split", "float", "tabs", "carousel", "masonry"],
        supported_inputs=[],
        supported_outputs=["display"],
    ),
    "swift": BackendManifest(
        backend_id="swift",
        supported_operations=[
            "state_machine", "event_handling", "ui_rendering",
            "data_persistence", "garbage_collection",
        ],
        type_mappings={
            "boolean": "Bool",
            "integer": "Int",
            "float": "Double",
            "string": "String",
            "array": "Array",
            "map": "Dictionary",
        },
        runtime_dependencies=[],
        platform_constraints={"platforms": ["linux", "windows"]},
        unsupported_cases=[
            "manual_memory_management",
            "zero_cost_abstractions",
        ],
        validation_command=["swiftc", "-typecheck", "{file}"],
        preservation_score=0.82,
        zaryel_support=True,
        supported_canvases=["mobile_app", "desktop_app"],
        supported_layouts=["stack", "split", "grid", "tabs"],
        supported_inputs=["touch", "keyboard", "voice", "gesture", "pen", "camera", "biometric"],
        supported_outputs=["display", "haptic", "audio"],
    ),
    "kotlin": BackendManifest(
        backend_id="kotlin",
        supported_operations=[
            "state_machine", "event_handling", "android_ui",
            "data_persistence", "managed_runtime",
        ],
        type_mappings={
            "boolean": "Boolean",
            "integer": "Long",
            "float": "Double",
            "string": "String",
            "array": "List",
            "map": "Map",
        },
        runtime_dependencies=["androidx.core"],
        platform_constraints={"platforms": ["linux", "windows", "android"]},
        unsupported_cases=[
            "manual_memory_management",
            "zero_cost_abstractions",
        ],
        validation_command=["kotlinc", "-script", "{file}"],
        preservation_score=0.80,
        zaryel_support=True,
        supported_canvases=["mobile_app"],
        supported_layouts=["stack", "split", "grid", "tabs"],
        supported_inputs=["touch", "keyboard", "gesture", "pen", "camera", "biometric"],
        supported_outputs=["display", "haptic", "audio"],
    ),
    "latex": BackendManifest(
        backend_id="latex",
        supported_operations=["document_rendering", "semantic_marking"],
        type_mappings={},
        runtime_dependencies=["pdflatex"],
        platform_constraints={"platforms": ["linux", "windows"]},
        unsupported_cases=[
            "behavioral_execution",
            "state_management",
            "dynamic_content",
            "layout_computation",
            "input_output_events",
        ],
        validation_command=["pdflatex", "--interaction=nonstopmode", "{file}"],
        preservation_score=0.70,
        zaryel_support=True,
        supported_canvases=["document"],
        supported_layouts=["stack"],
        supported_inputs=["keyboard"],
        supported_outputs=["print", "projection"],
    ),
    "webaudio": BackendManifest(
        backend_id="webaudio",
        supported_operations=[
            "audio_context", "realtime_processing", "event_scheduling",
        ],
        type_mappings={
            "boolean": "boolean",
            "integer": "number",
            "float": "number",
            "string": "string",
            "array": "Float32Array",
            "map": "AudioParamMap",
        },
        runtime_dependencies=[],
        platform_constraints={"platforms": ["linux", "windows", "android"]},
        unsupported_cases=[
            "low_level_hardware_access",
            "manual_memory_management",
            "zero_cost_abstractions",
            "form_architecture_layout",
        ],
        validation_command=["node", "--check", "{file}"],
        preservation_score=0.65,
        zaryel_support=False,
        supported_canvases=[],
        supported_layouts=[],
        supported_inputs=[],
        supported_outputs=["audio"],
    ),
    "text": BackendManifest(
        backend_id="text",
        supported_operations=["static_documentation"],
        type_mappings={},
        runtime_dependencies=[],
        platform_constraints={},
        unsupported_cases=[
            "behavioral_execution",
            "state_management",
            "type_safety",
            "dynamic_content",
            "form_architecture_layout",
        ],
        validation_command=[],
        preservation_score=0.10,
        zaryel_support=False,
        supported_canvases=[],
        supported_layouts=[],
        supported_inputs=[],
        supported_outputs=[],
    ),
}

# Public, sorted list for introspection / CLI display.
ALL_MANIFESTS: List[BackendManifest] = sorted(
    _MANIFESTS.values(), key=lambda m: m.backend_id
)


def manifest_for_language(language: str) -> Optional[BackendManifest]:
    """Look up the capability manifest for a realization target's language.

    The input is matched case-insensitively against known language aliases
    (e.g. ``"HTML/CSS/JS"`` → ``"javascript"``, ``"WebAudio API"`` →
    ``"webaudio"``).

    Args:
        language: The raw language label from a
            :class:`~orren_engine.data_model.RealizationTarget`.

    Returns:
        The matching :class:`BackendManifest`, or ``None`` when the language
        is not a registered backend.
    """
    canonical = _normalize_language(language)
    return _MANIFESTS.get(canonical)
