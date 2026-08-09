"""
Orren Engine — Validation Suite
===============================

The canonical 48-test validation suite referenced in 07_VALIDATION_v3.md.

Structure:
    Phase 1: 7 example files × 6 tests = 42 tests
    Phase 2: 6 gap syntax tests = 6 tests
    Total:   48 tests

Each Phase 1 example is tested for:
    1. parse:           file parses to at least one Expression
    2. sir:             SIR builds with at least one node, all 9 dimensions present
    3. equilibrium:     equilibrium resolver runs; outcomes + unresolved reported
    4. realization:     coordinator produces at least one artifact with valid schema
    5. dimensions:      every node carries all 9 dimensions (the atomic invariant)
    6. preservation:    all artifact preservation scores are in [0.0, 1.0]

Each Phase 2 gap test verifies that a specific captured gap (calibration,
behavioral, realization schema, degradation tolerance, subsystem composition,
semantic editing) is correctly handled by the engine.

Run:
    python -m orren_engine.validate           # run all 48 tests, print summary
    python -m orren_engine.validate --examples-dir /path/to/examples
    python -m orren_engine.validate --verbose
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

from . import __version__
from .data_model import Dimension, SIRNode
from .engine import Engine
from .equilibrium_resolver import EquilibriumResolver
from .parser import CoParser
from .realization_coordinator import RealizationCoordinator
from .semantic_editor import SemanticEditor
from .sir_builder import SIRBuilder


# ---------------------------------------------------------------------------
# Test result types
# ---------------------------------------------------------------------------


@dataclass
class TestResult:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class SuiteReport:
    phase: str
    results: List[TestResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def all_passed(self) -> bool:
        return self.passed == self.total


# ---------------------------------------------------------------------------
# Phase 1: Example file tests (7 × 6 = 42)
# ---------------------------------------------------------------------------


# Each entry: (filename, label, claimed_node_count,claimed_rule_count,
# claimed_target_count) — the claimed_* values come from
# 07_VALIDATION_v3.md. They are reported but NOT asserted as exact
# matches; the engine's structural invariants are what we assert.
EXAMPLES: List[Tuple[str, str, int, int, int]] = [
    ("01_irrigation.orn",            "Irrigation",          7,  4, 3),
    ("02_news_researcher.orn",       "News Researcher",    12,  6, 5),
    ("03_farmer_dashboard.orn",      "Farmer Dashboard",    9,  8, 5),
    ("04_farm_management.orn",       "Farm Management",    22,  9, 7),
    ("05_greenhouse_controller.orn", "Greenhouse Controller", 20, 10, 6),
    ("06_tell_your_story.orn",       "Tell Your Story",    31, 12, 5),
    ("07_master_builder_book.orn",   "Master Builder Book", 28,  8, 1),
]


def _load_example(examples_dir: str, fname: str) -> str:
    path = os.path.join(examples_dir, fname)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _test_parse(source: str) -> TestResult:
    """Test 1 of 6: file parses to at least one Expression."""
    try:
        exprs = CoParser().parse(source)
        if len(exprs) >= 1:
            return TestResult("parse", True, f"{len(exprs)} expression(s)")
        return TestResult("parse", False, "no expressions parsed")
    except Exception as e:
        return TestResult("parse", False, f"exception: {e}")


def _test_sir(source: str) -> Tuple[TestResult, Optional[object]]:
    """Test 2 of 6: SIR builds with at least one node."""
    try:
        exprs = CoParser().parse(source)
        graph = SIRBuilder().build(exprs)
        if len(graph.nodes) >= 1:
            return (
                TestResult("sir", True, f"{len(graph.nodes)} nodes"),
                graph,
            )
        return (TestResult("sir", False, "no nodes built"), None)
    except Exception as e:
        return (TestResult("sir", False, f"exception: {e}"), None)


def _test_equilibrium(graph) -> TestResult:
    """Test 3 of 6: equilibrium resolver runs cleanly."""
    try:
        report = EquilibriumResolver().resolve(graph)
        detail = (
            f"{len(report.outcomes)} outcomes, "
            f"{len(report.unresolved_conflicts)} unresolved"
        )
        return TestResult("equilibrium", True, detail)
    except Exception as e:
        return TestResult("equilibrium", False, f"exception: {e}")


def _test_realization(graph) -> TestResult:
    """Test 4 of 6: coordinator produces at least one artifact."""
    try:
        artifacts = RealizationCoordinator().coordinate(graph)
        if not artifacts:
            return TestResult("realization", False, "no artifacts")
        # Verify schema: each artifact has required fields.
        for art in artifacts:
            d = art.to_dict()
            for key in ("target_name", "target_language", "capabilities",
                        "output_files", "degradation_report", "preservation_score"):
                if key not in d:
                    return TestResult("realization", False,
                                       f"artifact missing field: {key}")
        return TestResult("realization", True,
                          f"{len(artifacts)} artifact(s)")
    except Exception as e:
        return TestResult("realization", False, f"exception: {e}")


def _test_dimensions(graph) -> TestResult:
    """Test 5 of 6: every node carries all 9 dimensions."""
    try:
        bad = [n.path for n in graph.nodes if not n.all_dimensions_present()]
        if bad:
            return TestResult("dimensions", False,
                              f"nodes missing dimensions: {bad[:3]}")
        return TestResult("dimensions", True,
                          f"all {len(graph.nodes)} nodes carry 9 dimensions")
    except Exception as e:
        return TestResult("dimensions", False, f"exception: {e}")


def _test_preservation(graph) -> TestResult:
    """Test 6 of 6: all preservation scores are in [0.0, 1.0]."""
    try:
        artifacts = RealizationCoordinator().coordinate(graph)
        out_of_range = [
            (a.target_name, a.preservation_score)
            for a in artifacts
            if not (0.0 <= a.preservation_score <= 1.0)
        ]
        if out_of_range:
            return TestResult("preservation", False,
                              f"scores out of range: {out_of_range}")
        scores = [a.preservation_score for a in artifacts]
        return TestResult("preservation", True,
                          f"scores: {scores}")
    except Exception as e:
        return TestResult("preservation", False, f"exception: {e}")


def run_phase1(examples_dir: str, verbose: bool = False) -> SuiteReport:
    """Run all 42 Phase 1 tests."""
    report = SuiteReport(phase="Phase 1: Example File Tests (7 × 6 = 42)")
    for fname, label, claimed_nodes, claimed_rules, claimed_tgts in EXAMPLES:
        try:
            source = _load_example(examples_dir, fname)
        except FileNotFoundError:
            for test_name in ("parse", "sir", "equilibrium",
                              "realization", "dimensions", "preservation"):
                report.results.append(TestResult(
                    f"{label}.{test_name}", False, "file not found"
                ))
            continue

        # Test 1: parse
        r_parse = _test_parse(source)
        report.results.append(TestResult(
            f"{label}.parse", r_parse.passed, r_parse.detail
        ))

        # Test 2: sir
        r_sir, graph = _test_sir(source)
        report.results.append(TestResult(
            f"{label}.sir", r_sir.passed, r_sir.detail
        ))

        if graph is None:
            # Skip remaining tests for this example if SIR build failed.
            for test_name in ("equilibrium", "realization", "dimensions", "preservation"):
                report.results.append(TestResult(
                    f"{label}.{test_name}", False, "skipped: SIR build failed"
                ))
            continue

        # Test 3: equilibrium
        r_eq = _test_equilibrium(graph)
        report.results.append(TestResult(
            f"{label}.equilibrium", r_eq.passed, r_eq.detail
        ))

        # Test 4: realization
        r_rz = _test_realization(graph)
        report.results.append(TestResult(
            f"{label}.realization", r_rz.passed, r_rz.detail
        ))

        # Test 5: dimensions
        r_dim = _test_dimensions(graph)
        report.results.append(TestResult(
            f"{label}.dimensions", r_dim.passed, r_dim.detail
        ))

        # Test 6: preservation
        r_pv = _test_preservation(graph)
        report.results.append(TestResult(
            f"{label}.preservation", r_pv.passed, r_pv.detail
        ))

        if verbose:
            actual_nodes = len(graph.nodes)
            actual_rules = len(graph.equilibrium_rules)
            actual_tgts = len(graph.realization_targets)
            print(
                f"  {label}: nodes {actual_nodes} (claimed {claimed_nodes}), "
                f"rules {actual_rules} (claimed {claimed_rules}), "
                f"targets {actual_tgts} (claimed {claimed_tgts})"
            )
    return report


# ---------------------------------------------------------------------------
# Phase 2: Gap syntax tests (6)
# ---------------------------------------------------------------------------


def _gap1_calibration() -> TestResult:
    """Gap 1: calibrate: section with maps_to and threshold."""
    src = """create app : Application
    vibe:
        app.color_character = emerald
    calibrate:
        calibrate emerald for vibe:
            maps_to color_hue
            threshold: hue in [150, 170]
            signal: css_color_value
"""
    try:
        exprs = CoParser().parse(src)
        graph = SIRBuilder().build(exprs)
        # The calibration entry should be present.
        all_calibrations = []
        for n in graph.nodes:
            all_calibrations.extend(n.calibration)
        if not all_calibrations:
            return TestResult("gap1_calibration", False, "no calibration entries")
        cal = all_calibrations[0]
        if cal.term != "emerald":
            return TestResult("gap1_calibration", False, f"wrong term: {cal.term}")
        if not cal.targets:
            return TestResult("gap1_calibration", False, "no targets")
        if cal.targets[0].maps_to != "color_hue":
            return TestResult("gap1_calibration", False, "wrong maps_to")
        if "150" not in cal.targets[0].threshold:
            return TestResult("gap1_calibration", False, "wrong threshold")
        return TestResult("gap1_calibration", True,
                          f"term={cal.term}, maps_to={cal.targets[0].maps_to}")
    except Exception as e:
        return TestResult("gap1_calibration", False, f"exception: {e}")


def _gap2_behavioral() -> TestResult:
    """Gap 2: behavior: section with lifecycle and transitions."""
    src = """create app : Application
    structure:
        control
    behavior:
        control behaves_as toggle
        control responds_to tap with bounce
        control transitions from idle to active on user_tap
        control lifecycle: idle -> active -> busy -> idle
"""
    try:
        exprs = CoParser().parse(src)
        graph = SIRBuilder().build(exprs)
        node = graph.find("app.control")
        if node is None:
            return TestResult("gap2_behavioral", False, "node not found")
        beh = node.get_dimension(Dimension.BEHAVIORAL)
        if len(beh) < 4:
            return TestResult("gap2_behavioral", False,
                              f"only {len(beh)} behavioral statements")
        # Find the lifecycle entry.
        lifecycle = next(
            (b for b in beh if isinstance(b, dict) and b.get("kind") == "lifecycle"),
            None,
        )
        if lifecycle is None:
            return TestResult("gap2_behavioral", False, "no lifecycle entry")
        if len(lifecycle.get("lifecycle", [])) < 3:
            return TestResult("gap2_behavioral", False, "lifecycle too short")
        return TestResult("gap2_behavioral", True,
                          f"{len(beh)} behavioral statements, "
                          f"{len(lifecycle['lifecycle'])} lifecycle hops")
    except Exception as e:
        return TestResult("gap2_behavioral", False, f"exception: {e}")


def _gap3_realization_schema() -> TestResult:
    """Gap 3: realize: section with multi-target planning."""
    src = """create app : Application
    structure:
        control
    cognitive:
        control.value = 42
    realize:
        target: web (HTML/CSS/JS)
            capabilities: layout, color
            preservation_score: 0.85
        target: native (Swift)
            capabilities: device
            preservation_score: 0.92
        target: backend (Python)
            capabilities: write, retrieve
            preservation_score: 1.0
"""
    try:
        exprs = CoParser().parse(src)
        graph = SIRBuilder().build(exprs)
        if len(graph.realization_targets) != 3:
            return TestResult("gap3_realization_schema", False,
                              f"expected 3 targets, got {len(graph.realization_targets)}")
        artifacts = RealizationCoordinator().coordinate(graph)
        if len(artifacts) != 3:
            return TestResult("gap3_realization_schema", False,
                              f"expected 3 artifacts, got {len(artifacts)}")
        for art in artifacts:
            d = art.to_dict()
            for key in ("target_name", "target_language", "capabilities",
                        "output_files", "degradation_report", "preservation_score"):
                if key not in d:
                    return TestResult("gap3_realization_schema", False,
                                      f"artifact missing field: {key}")
        return TestResult("gap3_realization_schema", True,
                          f"{len(artifacts)} targets, schema valid")
    except Exception as e:
        return TestResult("gap3_realization_schema", False, f"exception: {e}")


def _gap4_degradation_tolerance() -> TestResult:
    """Gap 4: degrade: section with tolerate/require levels."""
    src = """create app : Application
    structure:
        control
    cognitive:
        control.value = 42
    vibe:
        control.color_character = emerald
    degrade:
        require full for cognitive on activation_logic
        tolerate faithful for vibe on color_character
        tolerate proxy for vibe on aesthetic
        require full for cognitive on preservation
        tolerate documented for vibe on motion_quality
        tolerate optional for vibe on transition_effects
"""
    try:
        exprs = CoParser().parse(src)
        graph = SIRBuilder().build(exprs)
        # All six tolerance levels should be representable.
        all_entries = []
        for n in graph.nodes:
            all_entries.extend(n.degradation_tolerance.values())
        if len(all_entries) < 4:
            return TestResult("gap4_degradation_tolerance", False,
                              f"only {len(all_entries)} tolerance entries attached")
        levels_seen = {e.level.value for e in all_entries}
        # At least three of the six levels should be present.
        if len(levels_seen) < 3:
            return TestResult("gap4_degradation_tolerance", False,
                              f"only {len(levels_seen)} levels seen: {levels_seen}")
        return TestResult("gap4_degradation_tolerance", True,
                          f"{len(all_entries)} entries, levels: {sorted(levels_seen)}")
    except Exception as e:
        return TestResult("gap4_degradation_tolerance", False, f"exception: {e}")


def _gap5_subsystem_composition() -> TestResult:
    """Gap 5: multiple create: blocks in one file."""
    src = """create farm_system : Application
    context:
        purpose: a farm
    structure:
        dashboard
            panel_a

create crop_planner : Subsystem
    cognitive:
        crop_planner.scheduling = seasonal

create irrigation : Subsystem
    cognitive:
        irrigation.flow = regulated

create market : Subsystem
    cognitive:
        market.prices = daily

create system_eq : Equilibrium
    equilibrium:
        water_vs_crops:
            when cognitive.flow is active AND cognitive.scheduling is active
            preserve both
            resolution: schedule around crop windows
"""
    try:
        exprs = CoParser().parse(src)
        if len(exprs) != 5:
            return TestResult("gap5_subsystem_composition", False,
                              f"expected 5 expressions, got {len(exprs)}")
        graph = SIRBuilder().build(exprs)
        # Each subsystem should be reachable as its own root.
        roots = [n for n in graph.nodes if n.parent is None]
        if len(roots) != 5:
            return TestResult("gap5_subsystem_composition", False,
                              f"expected 5 roots, got {len(roots)}")
        # The system_eq expression should contribute equilibrium rules.
        if len(graph.equilibrium_rules) < 1:
            return TestResult("gap5_subsystem_composition", False,
                              "no equilibrium rules from system_eq")
        return TestResult("gap5_subsystem_composition", True,
                          f"{len(exprs)} expressions, {len(roots)} roots, "
                          f"{len(graph.equilibrium_rules)} rules")
    except Exception as e:
        return TestResult("gap5_subsystem_composition", False, f"exception: {e}")


def _gap6_semantic_editing() -> TestResult:
    """Gap 6: path resolution + search + modify + history."""
    src = """create app : Application
    structure:
        home
            control
    cognitive:
        control.value = 42
    vibe:
        control.color_character = emerald
        control.tone = calm
"""
    try:
        exprs = CoParser().parse(src)
        graph = SIRBuilder().build(exprs)
        editor = SemanticEditor(graph)

        # Path resolution: exact
        node = editor.resolve("app.home.control")
        if node is None:
            return TestResult("gap6_semantic_editing", False,
                              "path resolution failed")

        # Path resolution: suffix
        node2 = editor.resolve("control")
        if node2 is None or node2.path != "app.home.control":
            return TestResult("gap6_semantic_editing", False,
                              "suffix resolution failed")

        # Search by dimension
        results = editor.search(dimension=Dimension.VIBE)
        if len(results) != 1:
            return TestResult("gap6_semantic_editing", False,
                              f"search returned {len(results)} results")

        # Modify
        op = editor.modify("control", Dimension.VIBE, "color_character", "sapphire",
                           rationale="test edit")
        if op.old_value != "emerald":
            return TestResult("gap6_semantic_editing", False,
                              f"old_value wrong: {op.old_value}")

        # History
        if len(editor.history) != 1:
            return TestResult("gap6_semantic_editing", False,
                              f"history length {len(editor.history)}")

        # Undo
        editor.undo()
        node = editor.resolve("control")
        for entry in node.get_dimension(Dimension.VIBE):
            if isinstance(entry, dict) and entry.get("aspect") == "color_character":
                if entry.get("term") != "emerald":
                    return TestResult("gap6_semantic_editing", False,
                                      "undo did not restore value")

        # Redo
        editor.redo()
        for entry in node.get_dimension(Dimension.VIBE):
            if isinstance(entry, dict) and entry.get("aspect") == "color_character":
                if entry.get("term") != "sapphire":
                    return TestResult("gap6_semantic_editing", False,
                                      "redo did not reapply value")

        return TestResult("gap6_semantic_editing", True,
                          "path, search, modify, undo, redo all verified")
    except Exception as e:
        return TestResult("gap6_semantic_editing", False, f"exception: {e}")


def run_phase2() -> SuiteReport:
    """Run all 6 Phase 2 gap tests."""
    report = SuiteReport(phase="Phase 2: Gap Syntax Tests (6)")
    report.results.append(_gap1_calibration())
    report.results.append(_gap2_behavioral())
    report.results.append(_gap3_realization_schema())
    report.results.append(_gap4_degradation_tolerance())
    report.results.append(_gap5_subsystem_composition())
    report.results.append(_gap6_semantic_editing())
    return report


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------


def run_all(examples_dir: str, verbose: bool = False) -> Tuple[SuiteReport, SuiteReport, bool]:
    """Run both phases. Returns (phase1_report, phase2_report, all_passed)."""
    p1 = run_phase1(examples_dir, verbose=verbose)
    p2 = run_phase2()
    all_passed = p1.all_passed and p2.all_passed
    return p1, p2, all_passed


def print_report(p1: SuiteReport, p2: SuiteReport, verbose: bool = False) -> None:
    print(f"\nOrren Engine v{__version__} — Validation Suite")
    print("=" * 70)
    print(f"\n{p1.phase}")
    print("-" * 70)
    for r in p1.results:
        marker = "PASS" if r.passed else "FAIL"
        print(f"  [{marker}] {r.name:<50} {r.detail}")
    print(f"\n  Phase 1: {p1.passed}/{p1.total} passed")
    print()
    print(f"{p2.phase}")
    print("-" * 70)
    for r in p2.results:
        marker = "PASS" if r.passed else "FAIL"
        print(f"  [{marker}] {r.name:<50} {r.detail}")
    print(f"\n  Phase 2: {p2.passed}/{p2.total} passed")
    total_passed = p1.passed + p2.passed
    total = p1.total + p2.total
    print()
    print("=" * 70)
    print(f"Overall: {total_passed}/{total} passed")
    if total_passed == total:
        print("STATUS: ALL TESTS GREEN")
    else:
        print("STATUS: SOME TESTS FAILED")
    print()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="orren-validate",
        description="Run the Orren 48-test validation suite.",
    )
    parser.add_argument(
        "--examples-dir",
        default=os.path.join(os.path.dirname(__file__), "..", "examples"),
        help="directory containing the 7 example .orn files",
    )
    parser.add_argument("--verbose", action="store_true", help="print claimed vs actual counts")
    args = parser.parse_args(argv)
    examples_dir = os.path.abspath(args.examples_dir)
    if not os.path.isdir(examples_dir):
        print(f"ERROR: examples directory not found: {examples_dir}", file=sys.stderr)
        return 2
    p1, p2, all_passed = run_all(examples_dir, verbose=args.verbose)
    print_report(p1, p2, verbose=args.verbose)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())


__all__ = [
    "TestResult",
    "SuiteReport",
    "run_phase1",
    "run_phase2",
    "run_all",
    "print_report",
    "main",
]
