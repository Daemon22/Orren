"""Runtime validation for Orren's ZARYEL form-and-layout blueprint.

The parser checks source syntax and values as a source program is read.  This
module repeats the blueprint invariants at the SIR boundary so graphs created
or edited programmatically receive the same checks before realization.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

from .data_model import SIRGraph, ZaryelNode
from .parser import (
    ZARYEL_CANVASES,
    ZARYEL_FLOWS,
    ZARYEL_INPUTS,
    ZARYEL_LAYOUTS,
    ZARYEL_OUTPUTS,
    ZARYEL_POSITIONS,
    ZARYEL_VIEWPORTS,
)


@dataclass(frozen=True)
class ZaryelIssue:
    """One actionable violation found in a ZARYEL blueprint."""

    rule: str
    message: str
    severity: str = "error"
    location: Optional[str] = None

    def to_dict(self) -> dict[str, str]:
        result = {"rule": self.rule, "message": self.message, "severity": self.severity}
        if self.location:
            result["location"] = self.location
        return result


@dataclass
class ZaryelReport:
    """Validation result consumed by the runtime and realization coordinator."""

    issues: list[ZaryelIssue] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def is_valid(self) -> bool:
        return self.valid

    @property
    def errors(self) -> list[ZaryelIssue]:
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ZaryelIssue]:
        return [issue for issue in self.issues if issue.severity == "warning"]

    def to_dict(self) -> dict[str, Any]:
        return {"valid": self.valid, "issues": [issue.to_dict() for issue in self.issues]}


def _issue(rule: str, message: str, location: Optional[str] = None) -> ZaryelIssue:
    return ZaryelIssue(rule=rule, message=message, location=location)


def _mentioned_names(blueprint: ZaryelNode) -> tuple[set[str], set[str]]:
    regions = {region.name for region in blueprint.regions}
    layers = set(blueprint.layers)
    layer_regions = {name for names in blueprint.layers.values() for name in names}
    return regions, layers | layer_regions


def validate_zaryel(blueprint: Optional[ZaryelNode]) -> ZaryelReport:
    """Validate a blueprint using the same value vocabulary as the parser.

    An absent blueprint is not an error: ZARYEL is an optional meta-realm.
    """
    report = ZaryelReport()
    if blueprint is None:
        return report

    if not blueprint.canvas:
        report.issues.append(_issue("Z001", "ZARYEL blueprint is missing required 'canvas' field"))
    elif blueprint.canvas not in ZARYEL_CANVASES:
        report.issues.append(_issue("Z002", f"Invalid canvas '{blueprint.canvas}'"))

    if blueprint.viewport and blueprint.viewport not in ZARYEL_VIEWPORTS:
        report.issues.append(_issue("Z003", f"Invalid viewport '{blueprint.viewport}'"))
    if blueprint.layout and blueprint.layout not in ZARYEL_LAYOUTS:
        report.issues.append(_issue("Z004", f"Invalid layout '{blueprint.layout}'"))
    if blueprint.flow and blueprint.flow not in ZARYEL_FLOWS:
        report.issues.append(_issue("Z005", f"Invalid flow '{blueprint.flow}'"))

    region_names: set[str] = set()
    for region in blueprint.regions:
        location = f"regions.{region.name}"
        region_names.add(region.name)
        if not region.position:
            report.issues.append(_issue("Z006", f"Region '{region.name}' is missing required 'position'", location))
        elif region.position not in ZARYEL_POSITIONS:
            report.issues.append(_issue("Z007", f"Region '{region.name}' has invalid position '{region.position}'", location))
        if region.fixed and not region.height and not region.width:
            report.issues.append(_issue("Z008", f"Fixed region '{region.name}' must declare height or width", location))

    for name, value in blueprint.breakpoints.items():
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            report.issues.append(_issue("Z009", f"Breakpoint '{name}' must be a positive integer"))

    declared_regions, layer_names = _mentioned_names(blueprint)
    if blueprint.focus and blueprint.focus not in declared_regions:
        report.issues.append(_issue("Z010", f"Focus '{blueprint.focus}' does not reference a declared region"))
    if blueprint.entry and blueprint.entry not in declared_regions and blueprint.entry not in layer_names:
        report.issues.append(_issue("Z011", f"Entry '{blueprint.entry}' does not reference a declared region or layer"))

    for input_name in blueprint.inputs:
        if input_name not in ZARYEL_INPUTS:
            report.issues.append(_issue("Z012", f"Invalid input '{input_name}'"))
    for output_name in blueprint.outputs:
        if output_name not in ZARYEL_OUTPUTS:
            report.issues.append(_issue("Z013", f"Invalid output '{output_name}'"))

    return report


def validate_zaryel_graph(graph: SIRGraph) -> ZaryelReport:
    """Validate the graph's optional ZARYEL blueprint before realization."""
    return validate_zaryel(graph.zaryel)


__all__ = ["ZaryelIssue", "ZaryelReport", "validate_zaryel", "validate_zaryel_graph"]
