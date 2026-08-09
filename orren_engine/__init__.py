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
from .validate import run_all as run_validation_suite

__all__ = [
    "CoParser",
    "SIRBuilder",
    "EquilibriumResolver",
    "RealizationCoordinator",
    "SemanticEditor",
    "Engine",
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
    "EditOperation",
    "__version__",
]
