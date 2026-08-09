"""Validation suite regression test.

Wraps orren_engine.validate so the 48-test validation suite runs as
part of the regular pytest suite. If any of the 48 tests fails, this
file fails.

This is the canonical validation referenced in 07_VALIDATION_v3.md:
    Phase 1: 7 example files × 6 tests = 42
    Phase 2: 6 gap syntax tests
    Total:   48

Run: pytest tests/test_10_validation_suite.py -v
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from orren_engine.validate import run_all, print_report


EXAMPLES_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "examples")
)


def test_examples_directory_exists():
    assert os.path.isdir(EXAMPLES_DIR), f"examples dir missing: {EXAMPLES_DIR}"
    # All 7 canonical example files should be present.
    expected = [
        "01_irrigation.orn",
        "02_news_researcher.orn",
        "03_farmer_dashboard.orn",
        "04_farm_management.orn",
        "05_greenhouse_controller.orn",
        "06_tell_your_story.orn",
        "07_master_builder_book.orn",
    ]
    for fname in expected:
        path = os.path.join(EXAMPLES_DIR, fname)
        assert os.path.isfile(path), f"missing example: {fname}"


def test_validation_suite_48_pass():
    """The canonical 48-test validation suite must pass."""
    p1, p2, all_passed = run_all(EXAMPLES_DIR, verbose=False)
    if not all_passed:
        # Print the report so the failure is visible.
        print_report(p1, p2, verbose=True)
    assert all_passed, (
        f"validation suite failed: phase1={p1.passed}/{p1.total}, "
        f"phase2={p2.passed}/{p2.total}"
    )


def test_phase1_has_42_tests():
    p1, _, _ = run_all(EXAMPLES_DIR, verbose=False)
    assert p1.total == 42, f"phase1 expected 42 tests, got {p1.total}"


def test_phase2_has_6_tests():
    _, p2, _ = run_all(EXAMPLES_DIR, verbose=False)
    assert p2.total == 6, f"phase2 expected 6 tests, got {p2.total}"


def test_total_is_48_tests():
    p1, p2, _ = run_all(EXAMPLES_DIR, verbose=False)
    assert p1.total + p2.total == 48


# ---------------------------------------------------------------------------
# Per-example smoke tests — one assertion per example, so a single
# example failure is easy to spot in the pytest output.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("example_file,expected_targets", [
    ("01_irrigation.orn", 3),
    ("02_news_researcher.orn", 5),
    ("03_farmer_dashboard.orn", 5),
    ("04_farm_management.orn", 7),
    ("05_greenhouse_controller.orn", 6),
    ("06_tell_your_story.orn", 5),
    ("07_master_builder_book.orn", 1),
])
def test_example_target_count_matches_validation_report(example_file, expected_targets):
    """The realization target count for each example must match the
    count claimed in 07_VALIDATION_v3.md exactly. This is the most
    stable claim in the validation report — target parsing is purely
    syntactic and should be reproducible byte-for-byte."""
    from orren_engine import Engine
    path = os.path.join(EXAMPLES_DIR, example_file)
    with open(path) as f:
        src = f.read()
    result = Engine().run(src)
    assert len(result.artifacts) == expected_targets, (
        f"{example_file}: expected {expected_targets} targets, "
        f"got {len(result.artifacts)}"
    )


# ---------------------------------------------------------------------------
# Per-gap tests — one assertion per gap, so a regression in any single
# gap is easy to isolate.
# ---------------------------------------------------------------------------


def test_gap1_calibration_captures_maps_to_and_threshold():
    from orren_engine.validate import _gap1_calibration
    r = _gap1_calibration()
    assert r.passed, r.detail


def test_gap2_behavioral_captures_lifecycle_and_transitions():
    from orren_engine.validate import _gap2_behavioral
    r = _gap2_behavioral()
    assert r.passed, r.detail


def test_gap3_realization_artifact_schema_valid():
    from orren_engine.validate import _gap3_realization_schema
    r = _gap3_realization_schema()
    assert r.passed, r.detail


def test_gap4_degradation_tolerance_six_levels():
    from orren_engine.validate import _gap4_degradation_tolerance
    r = _gap4_degradation_tolerance()
    assert r.passed, r.detail


def test_gap5_subsystem_composition_multiple_create_blocks():
    from orren_engine.validate import _gap5_subsystem_composition
    r = _gap5_subsystem_composition()
    assert r.passed, r.detail


def test_gap6_semantic_editing_path_search_modify_undo_redo():
    from orren_engine.validate import _gap6_semantic_editing
    r = _gap6_semantic_editing()
    assert r.passed, r.detail
