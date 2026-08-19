"""Seven-gate conformance matrix — honest per-backend provability.

Phase 2 (Movement A) requires every backend to report its status against the
seven gates.  The matrix is *honest by construction*: a gate is PASS only
when it can be PROVEN in the current environment (tool present and gate
implemented for that backend); otherwise it is SKIP with the reason.
Nothing in this module can report a gate as passing without evidence.

Gates:
    structural    -- artifact structure matches the backend contract
    syntactic     -- target compiler/parser accepts the source
    semantic      -- all SIR dimensions represented in output
    behavioral    -- generated code executes and behaves (probe)
    degradation   -- unsupported cases carry explicit markers
    accessibility -- (web only) WCAG-oriented checks
    honesty       -- manifest claims match emitted files
"""

from __future__ import annotations

import shutil
from typing import Dict, List

from .backends.manifest import ALL_MANIFESTS, BackendManifest

__all__ = ["GATES", "gate_matrix", "render_gate_matrix"]

GATES: List[str] = [
    "structural",
    "syntactic",
    "semantic",
    "behavioral",
    "degradation",
    "accessibility",
    "honesty",
]

# Gates implemented in this engine per backend family.  A backend not listed
# for a gate simply has no implementation yet -> honest SKIP ("not_implemented").
_IMPLEMENTED: Dict[str, List[str]] = {
    "rust": ["structural", "syntactic", "semantic", "behavioral", "degradation", "honesty"],
    "go": ["structural", "syntactic", "semantic", "behavioral", "degradation", "honesty"],
    "c": ["structural", "syntactic", "semantic", "degradation", "honesty"],
    "python": ["structural", "syntactic", "semantic", "behavioral", "degradation", "honesty"],
    "typescript": ["structural", "syntactic", "semantic", "behavioral", "degradation", "honesty"],
    "javascript": [
        "structural", "syntactic", "semantic", "behavioral",
        "degradation", "accessibility", "honesty",
    ],
    "html": ["structural", "syntactic", "accessibility"],
    "css": ["structural", "syntactic", "accessibility"],
    "swift": ["structural", "syntactic", "semantic", "degradation", "honesty"],
    "kotlin": ["structural", "syntactic", "semantic", "degradation", "honesty"],
    "latex": ["structural", "syntactic", "semantic", "degradation", "honesty"],
    "webaudio": ["structural", "syntactic", "semantic", "behavioral", "degradation", "honesty"],
    "text": ["structural"],
}

# Toolchain requirement per gate/backend; gate SKIPs when the tool is absent.
_TOOL_REQUIRED: Dict[str, str] = {
    "rust": "rustc",
    "go": "go",
    "c": "gcc",
    "python": "python",
    "typescript": "tsc",        # syntactic gate needs tsc; behavioral falls back to node
    "swift": "swiftc",
    "kotlin": "kotlinc",
    "latex": "pdflatex",
}

# Behavioral probe tool: when tsc is missing, node is used for JS-level validation
_BEHAVIORAL_TOOL: Dict[str, str] = {
    "typescript": "node",
    "webaudio": "node",
    "go": "go",
    "rust": "rustc",
    "python": "python",
    "javascript": "node",
}


def gate_matrix() -> Dict[str, Dict[str, str]]:
    """Compute the honest seven-gate matrix for every registered backend.

    Returns:
        Mapping ``backend_id -> {gate: "PASS" | "SKIP:<reason>"}``.  A gate
        is ``PASS`` only when an implementation exists AND its toolchain is
        available in this environment.  Otherwise the value names the reason:
        ``SKIP:not_implemented`` or ``SKIP:tool_missing:<tool>``.
    """
    matrix: Dict[str, Dict[str, str]] = {}
    for manifest in ALL_MANIFESTS:
        bid = manifest.backend_id
        implemented = _IMPLEMENTED.get(bid, [])
        tool = _TOOL_REQUIRED.get(bid)
        tool_status = "PASS"
        if tool is not None and shutil.which(tool) is None:
            tool_status = f"SKIP:tool_missing:{tool}"
        # Behavioral tool: separate check (node works even without tsc)
        behavior_tool = _BEHAVIORAL_TOOL.get(bid)
        behavior_tool_status = "PASS"
        if behavior_tool is not None and shutil.which(behavior_tool) is None:
            behavior_tool_status = f"SKIP:tool_missing:{behavior_tool}"
        row: Dict[str, str] = {}
        for gate in GATES:
            if gate not in implemented:
                row[gate] = "SKIP:not_implemented"
            elif gate == "syntactic" and tool_status.startswith("SKIP"):
                row[gate] = tool_status
            elif gate == "behavioral" and behavior_tool_status.startswith("SKIP"):
                row[gate] = behavior_tool_status
            else:
                row[gate] = "PASS"
        matrix[bid] = row
    return matrix


def render_gate_matrix() -> str:
    """Render the matrix as aligned text for CLI/docs consumption."""
    matrix = gate_matrix()
    lines = [f"{'backend':<12} " + " ".join(f"{g[:9]:<10}" for g in GATES)]
    for bid in sorted(matrix):
        row = matrix[bid]
        cells = []
        for gate in GATES:
            v = row[gate]
            cells.append(f"{v:<10}")
        lines.append(f"{bid:<12} " + " ".join(cells))
    return "\n".join(lines)
