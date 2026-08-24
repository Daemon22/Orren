"""
Orren Engine — Realization Coordinator
======================================

Maps a SIR graph to concrete realization artifacts for each declared target.

Per 07_VALIDATION_v3.md:
  - Target capability matching
  - Dimension → language mapping
  - Degradation analysis
  - Preservation scoring

Artifact schema (strict):
    RealizationArtifact {
        target_language: str
        capabilities: list[str]
        output_files: list[{path, language}]
        degradation_report: list[{dimension, aspect, severity, tolerance}]
        preservation_score: float
        target_name: str
    }
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .backends import backend_for_language
from .data_model import (
    DegradationEntry,
    Dimension,
    OutputFile,
    RealizationArtifact,
    RealizationTarget,
    SIRGraph,
    SIRNode,
    Severity,
    ToleranceLevel,
)
from .zaryel_validator import ZaryelReport


# ---------------------------------------------------------------------------
# Capability → dimension coverage map
# ---------------------------------------------------------------------------

# Each target capability can express certain dimensions exactly, and
# others approximately or not at all. This is the substrate-knowledge
# table the coordinator consults when scoring preservation.
CAPABILITY_DIMENSION_COVERAGE: Dict[str, Dict[str, Tuple[Severity, ToleranceLevel]]] = {
    "layout": {
        "spatial": (Severity.NONE, ToleranceLevel.FULL),
        "vibe": (Severity.LOW, ToleranceLevel.FAITHFUL),
    },
    "color": {
        "vibe": (Severity.NONE, ToleranceLevel.FULL),
    },
    "motion": {
        "vibe": (Severity.LOW, ToleranceLevel.FAITHFUL),
        "temporal": (Severity.NONE, ToleranceLevel.FULL),
    },
    "event_handling": {
        "conditional": (Severity.NONE, ToleranceLevel.FULL),
        "behavioral": (Severity.NONE, ToleranceLevel.FULL),
    },
    "device_microphone": {
        "cognitive": (Severity.NONE, ToleranceLevel.FULL),
    },
    "input_buttons": {
        "conditional": (Severity.NONE, ToleranceLevel.FULL),
        "relational": (Severity.NONE, ToleranceLevel.FULL),
    },
    "storage": {
        "cognitive": (Severity.NONE, ToleranceLevel.FULL),
    },
    "speech_to_text": {
        "cognitive": (Severity.NONE, ToleranceLevel.FULL),
    },
    "audio_input": {
        "cognitive": (Severity.NONE, ToleranceLevel.FULL),
    },
    "write": {
        "cognitive": (Severity.NONE, ToleranceLevel.FULL),
    },
    "retain": {
        "cognitive": (Severity.NONE, ToleranceLevel.FULL),
    },
    "retrieve": {
        "cognitive": (Severity.NONE, ToleranceLevel.FULL),
    },
    "detect_volume_down": {
        "conditional": (Severity.NONE, ToleranceLevel.FULL),
    },
    "detect_double_click": {
        "conditional": (Severity.NONE, ToleranceLevel.FULL),
    },
    "typography": {
        "vibe": (Severity.LOW, ToleranceLevel.FAITHFUL),
    },
}


class RealizationCoordinator:
    """Produce RealizationArtifacts from a SIR graph + declared targets."""

    def coordinate(
        self, graph: SIRGraph, zaryel_report: Optional[ZaryelReport] = None
    ) -> List[RealizationArtifact]:
        artifacts: List[RealizationArtifact] = []
        for target in graph.realization_targets:
            art = self._coordinate_target(target, graph, zaryel_report)
            artifacts.append(art)
        return artifacts

    # -----------------------------------------------------------------

    def _coordinate_target(
        self, target: RealizationTarget, graph: SIRGraph,
        zaryel_report: Optional[ZaryelReport] = None,
    ) -> RealizationArtifact:
        # Determine which dimensions this target can express via its
        # declared capabilities.
        expressed_dims: Set[str] = set()
        for cap in target.capabilities:
            coverage = CAPABILITY_DIMENSION_COVERAGE.get(cap, {})
            for dim_name, (sev, lvl) in coverage.items():
                if sev != Severity.OUT_OF_SCOPE:
                    expressed_dims.add(dim_name)

        # Build the degradation report by walking every dimension on
        # every node and checking whether the target can express it.
        degradation_report: List[Dict[str, str]] = []
        dimensions_seen: Set[Tuple[str, str]] = set()
        for node in graph.nodes:
            for dim in Dimension.semantic():
                payload = node.get_dimension(dim)
                if not payload:
                    continue
                # Per-aspect granularity: walk each payload entry to find
                # the aspect name (e.g. 'color_character', 'activation_logic').
                aspects = _extract_aspects(dim, payload)
                for aspect, severity_hint in aspects:
                    key = (dim.value, aspect)
                    if key in dimensions_seen:
                        continue
                    dimensions_seen.add(key)
                    sev, lvl, source = self._classify(
                        dim, aspect, target, expressed_dims, node
                    )
                    degradation_report.append(
                        {
                            "node": node.path,
                            "dimension": dim.value,
                            "aspect": aspect,
                            "severity": sev.value,
                            "tolerance": lvl.value,
                            "source": source,
                        }
                    )

        # Build output_files: one file per capability group.
        output_files = self._plan_output_files(target)

        # Fold ZARYEL Meta-realm issues into the degradation report so
        # downstream consumers (tests, CLI, gate matrix) see them.
        if zaryel_report is not None and graph.zaryel is not None:
            from .backends.manifest import manifest_for_language
            manifest = manifest_for_language(target.language)
            backend_supports_zaryel = (
                manifest is not None and getattr(manifest, "zaryel_support", False)
            )
            for issue in zaryel_report.issues:
                sev = Severity.HIGH if issue.severity == "error" else Severity.LOW
                if not backend_supports_zaryel:
                    sev = Severity.MEDIUM
                degradation_report.append({
                    "node": "zaryel",
                    "dimension": "zaryel",
                    "aspect": f"rule_{issue.rule}",
                    "severity": sev.value,
                    "tolerance": (
                        ToleranceLevel.OPTIONAL.value
                        if issue.severity == "warning"
                        else ToleranceLevel.DOCUMENTED.value
                    ),
                    "source": "meta_realm",
                    "message": issue.message,
                })

        # Compute preservation score.
        score = self._preservation_score(target, degradation_report)

        return RealizationArtifact(
            target_name=target.name,
            target_language=target.language,
            capabilities=list(target.capabilities),
            output_files=output_files,
            degradation_report=degradation_report,
            preservation_score=score,
        )

    # -----------------------------------------------------------------

    def _classify(
        self,
        dim: Dimension,
        aspect: str,
        target: RealizationTarget,
        expressed_dims: Set[str],
        node: SIRNode,
    ) -> Tuple[Severity, ToleranceLevel, str]:
        """Classify how well `target` can express one aspect of one dimension."""
        # 1. Is the aspect explicitly listed in cannot_express?
        for expr in target.cannot_express:
            if aspect in expr or dim.value in expr:
                return (
                    Severity.OUT_OF_SCOPE,
                    ToleranceLevel.OPTIONAL,
                    "cannot_express",
                )
        # 2. Is the aspect explicitly listed in needs_bridge?
        for expr in target.needs_bridge:
            if aspect in expr or dim.value in expr:
                return (
                    Severity.MEDIUM,
                    ToleranceLevel.PROXY,
                    "needs_bridge",
                )
        # 3. Is the dimension one this target can express via capabilities?
        if dim.value in expressed_dims:
            # Look up capability coverage for the aspect.
            for cap in target.capabilities:
                coverage = CAPABILITY_DIMENSION_COVERAGE.get(cap, {})
                dim_coverage = coverage.get(dim.value)
                if dim_coverage is not None:
                    sev, lvl = dim_coverage
                    # Check per-node tolerance override.
                    tol_key = f"{dim.value}.{aspect}"
                    override = node.degradation_tolerance.get(tol_key)
                    if override is not None:
                        # If the override requires a stronger level than
                        # the capability provides, escalate severity.
                        if override.level.strength() > lvl.strength():
                            return (
                                Severity.HIGH,
                                override.level,
                                "tolerance_override_unmet",
                            )
                        return (sev, override.level, "tolerance_override_met")
                    return (sev, lvl, "capability")
        # 4. Default: out of scope.
        return (Severity.OUT_OF_SCOPE, ToleranceLevel.OPTIONAL, "no_capability")

    # -----------------------------------------------------------------

    def _plan_output_files(self, target: RealizationTarget) -> List[OutputFile]:
        """Plan output files based on target language and capabilities."""
        lang = target.language.lower()
        files: List[OutputFile] = []
        if "html" in lang or "css" in lang or "js" in lang:
            # _gen_web emits the complete web bundle (plus the single-file
            # standalone variant usable from file://). The manifest must
            # describe every emitted file, even when a target lacks one
            # of the corresponding semantic capabilities.
            files.extend([
                OutputFile(path=f"{target.name}/index.html", language="html"),
                OutputFile(path=f"{target.name}/styles.css", language="css"),
                OutputFile(path=f"{target.name}/app.js", language="javascript"),
                OutputFile(path=f"{target.name}/living.js", language="javascript"),
                OutputFile(
                    path=f"{target.name}/index.standalone.html", language="html"
                ),
            ])
            if "bundler" in [c.lower() for c in target.capabilities]:
                files.extend([
                    OutputFile(
                        path=f"{target.name}/package.json", language="json"
                    ),
                    OutputFile(
                        path=f"{target.name}/vite.config.js",
                        language="javascript",
                    ),
                    OutputFile(
                        path=f"{target.name}/tests/smoke.spec.js",
                        language="javascript",
                    ),
                ])
        elif "python" in lang:
            if "storage" in target.name:
                filename = "storage.py"
            elif "transcription" in target.name:
                filename = "transcription.py"
            elif "input" in target.name or "button" in target.name:
                filename = "input_watcher.py"
            else:
                filename = "service.py"
            files.append(OutputFile(path=f"{target.name}/{filename}", language="python"))
        elif backend_for_language(lang) is not None:
            backend = backend_for_language(lang)
            assert backend is not None
            files.extend(
                OutputFile(path=f"{target.name}/{filename}", language=language)
                for filename, language in backend.native_files
            )
        else:
            files.append(
                OutputFile(path=f"{target.name}/MANIFEST.txt", language="text")
            )
        return files

    # -----------------------------------------------------------------

    def _preservation_score(
        self,
        target: RealizationTarget,
        degradation_report: List[Dict[str, str]],
    ) -> float:
        """Compute a 0..1 preservation score.

        Score = weighted average of tolerance strengths across the
        degradation report. Out-of-scope entries do not penalize the
        score (they reflect target scope, not lost meaning).
        """
        if not degradation_report:
            return 1.0
        total_weight = 0.0
        score_weight = 0.0
        for entry in degradation_report:
            if entry["severity"] == Severity.OUT_OF_SCOPE.value:
                continue
            try:
                lvl = ToleranceLevel(entry["tolerance"])
            except ValueError:
                continue
            w = 1.0
            # Required dimensions weigh more.
            if entry["dimension"] in ("cognitive", "conditional"):
                w = 2.0
            total_weight += w
            # Normalize: full=1.0, faithful=0.85, conventional=0.7,
            # proxy=0.5, documented=0.3, optional=0.1
            score_map = {
                ToleranceLevel.FULL: 1.0,
                ToleranceLevel.FAITHFUL: 0.85,
                ToleranceLevel.CONVENTIONAL: 0.7,
                ToleranceLevel.PROXY: 0.5,
                ToleranceLevel.DOCUMENTED: 0.3,
                ToleranceLevel.OPTIONAL: 0.1,
            }
            score_weight += w * score_map[lvl]
        if total_weight == 0:
            return 1.0
        return round(score_weight / total_weight, 4)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_aspects(dim: Dimension, payload: List) -> List[Tuple[str, Severity]]:
    """Extract (aspect_name, severity_hint) pairs from a dimension payload.

    For most dimensions, the aspect is the predicate or relation name.
    For vibe, it's the aspect field. For behavioral, it's the kind.
    """
    out: List[Tuple[str, Severity]] = []
    for item in payload:
        if isinstance(item, dict):
            if dim == Dimension.VIBE:
                aspect = item.get("aspect", "default")
            elif dim == Dimension.COGNITIVE:
                aspect = item.get("predicate", "value")
            elif dim == Dimension.SPATIAL:
                aspect = item.get("relation", "located_in")
            elif dim == Dimension.TEMPORAL:
                aspect = item.get("kind", "transition")
            elif dim == Dimension.RELATIONAL:
                aspect = item.get("relation", "feeds")
            elif dim == Dimension.CONDITIONAL:
                aspect = item.get("action", "activates")
            elif dim == Dimension.BEHAVIORAL:
                aspect = item.get("kind", "behaves_as")
            else:
                aspect = "default"
            out.append((aspect, Severity.NONE))
    return out


__all__ = ["RealizationCoordinator", "CAPABILITY_DIMENSION_COVERAGE"]
