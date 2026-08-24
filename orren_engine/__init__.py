"""Orren Engine — semantic interpretation + realization pipeline.

Public API:
    CoParser            — file → expressions
    SIRBuilder          — expressions → SIR graph
    EquilibriumResolver — conflict detection + resolution
    RealizationCoordinator — SIR → realization artifacts
    SemanticEditor      — path-based editing with undo/redo
    Engine              — orchestrates the whole pipeline
"""

__version__ = "0.3.3"

from .data_model import (
    BehavioralStatement,
    CalibrationEntry,
    CalibrationTarget,
    CognitiveStatement,
    ConditionalStatement,
    ContextStatement,
    DegradationEntry,
    Dimension,
    EditOp,
    EditOperation,
    EquilibriumCondition,
    EquilibriumResolution,
    EquilibriumRule,
    Expression,
    ExpressionType,
    LifecycleTransition,
    OutputFile,
    RealizationArtifact,
    RealizationTarget,
    RelationalStatement,
    SIRGraph,
    SIRNode,
    ZaryelNode,
    ZaryelRegion,
    SpatialStatement,
    StructureNode,
    TemporalStatement,
    ToleranceLevel,
    Severity,
    VibeStatement,
)
from .parser import CoParser
from .sir_builder import SIRBuilder
from .equilibrium_resolver import EquilibriumResolver
from .realization_coordinator import RealizationCoordinator
from .semantic_editor import SemanticEditor
from .codegen import generate as generate_code
from .design_tokens import DesignTokens, extract_design_tokens
from .preview import generate_preview, write_preview
from .engine import Engine
from .realization_ir import IR_VERSION, IRNode, IRTarget, RealizationIR, lower_graph
from .backends import BackendSpec, BACKENDS, backend_for_language, backend_for_target
from .backends.manifest import BackendManifest, manifest_for_language, ALL_MANIFESTS
from .platforms import PlatformStatus, inspect_platform, load_capabilities
from .zaryel_validator import ZaryelIssue, ZaryelReport, validate_zaryel, validate_zaryel_graph
from .errors import (
    ErrorCategory,
    ErrorCode,
    ErrorCollector,
    OrrenError,
    OrrenSyntaxError,
    OrrenIncompleteError,
    OrrenAmbiguityError,
    OrrenUnknownConceptError,
    OrrenConflictError,
    OrrenUnsupportedTarget,
    OrrenRecoverableWarning,
    OrrenUnrecoverableError,
)

__all__ = [
    "CoParser",
    "SIRBuilder",
    "EquilibriumResolver",
    "RealizationCoordinator",
    "SemanticEditor",
    "Engine",
    "IR_VERSION",
    "IRNode",
    "IRTarget",
    "RealizationIR",
    "lower_graph",
    "BackendSpec",
    "BACKENDS",
    "backend_for_language",
    "backend_for_target",
    "BackendManifest",
    "manifest_for_language",
    "ALL_MANIFESTS",
    "PlatformStatus",
    "inspect_platform",
    "load_capabilities",
    "Dimension",
    "ToleranceLevel",
    "Severity",
    "ExpressionType",
    "EditOp",
    "ContextStatement",
    "StructureNode",
    "Expression",
    "CognitiveStatement",
    "VibeStatement",
    "SpatialStatement",
    "TemporalStatement",
    "RelationalStatement",
    "ConditionalStatement",
    "LifecycleTransition",
    "BehavioralStatement",
    "CalibrationTarget",
    "CalibrationEntry",
    "EquilibriumCondition",
    "EquilibriumResolution",
    "EquilibriumRule",
    "DegradationEntry",
    "OutputFile",
    "RealizationTarget",
    "RealizationArtifact",
    "SIRNode",
    "SIRGraph",
    "ZaryelNode",
    "ZaryelRegion",
    "ZaryelReport",
    "ZaryelIssue",
    "validate_zaryel",
    "validate_zaryel_graph",
    "EditOperation",
    "ErrorCategory",
    "ErrorCode",
    "ErrorCollector",
    "OrrenError",
    "OrrenSyntaxError",
    "OrrenIncompleteError",
    "OrrenAmbiguityError",
    "OrrenUnknownConceptError",
    "OrrenConflictError",
    "OrrenUnsupportedTarget",
    "OrrenRecoverableWarning",
    "OrrenUnrecoverableError",
    "__version__",
]
