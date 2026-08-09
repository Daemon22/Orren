"""Adversarial input tests.

Validates that the engine handles genuinely difficult natural-language
programs — written the way a real user would write them, with messiness,
contradictions, ambiguous subjects, and vibe-heavy language — without
crashing and with sensible structural output.

The 6 adversarial programs live in examples/adversarial/ and cover
domains the engine has never seen:
  1. Rain Composition      — music + emotion detection
  2. Assistive Arm         — medical device + robotics
  3. Revenue Contract      — financial + legal
  4. Lighthouse            — interactive fiction + narrative
  5. Sign Bridge           — accessibility + cross-modality
  6. Still Water           — meditation + vibe-dominant

These were NOT designed around the test suite. They were written as
natural-language descriptions of real applications.

Run: pytest tests/test_11_adversarial.py -v
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from orren_engine import Engine, Dimension, generate_code, generate_preview

ADVERSARIAL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "examples", "adversarial")
)

ADVERSARIAL_FILES = [
    "01_rain_composition.orn",
    "02_assistive_arm.orn",
    "03_revenue_contract.orn",
    "04_lighthouse.orn",
    "05_sign_bridge.orn",
    "06_still_water.orn",
]


@pytest.fixture(scope="module")
def adversarial_results():
    """Parse and run all 6 adversarial programs once, cache results."""
    results = {}
    for fname in ADVERSARIAL_FILES:
        path = os.path.join(ADVERSARIAL_DIR, fname)
        with open(path) as f:
            src = f.read()
        engine = Engine()
        result = engine.run(src)
        results[fname] = result
    return results


# ---------------------------------------------------------------------------
# Engine doesn't crash on adversarial input
# ---------------------------------------------------------------------------


class TestNoCrash:
    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_engine_runs_without_exception(self, adversarial_results, fname):
        result = adversarial_results[fname]
        assert result is not None
        assert result.expressions_count >= 1

    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_sir_built(self, adversarial_results, fname):
        result = adversarial_results[fname]
        assert result.sir_node_count >= 5, f"{fname}: only {result.sir_node_count} nodes"

    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_artifacts_produced(self, adversarial_results, fname):
        result = adversarial_results[fname]
        assert len(result.artifacts) >= 3, f"{fname}: only {len(result.artifacts)} artifacts"


# ---------------------------------------------------------------------------
# Structural invariants hold on adversarial input
# ---------------------------------------------------------------------------


class TestStructuralInvariants:
    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_all_nodes_carry_9_dimensions(self, adversarial_results, fname):
        result = adversarial_results[fname]
        for node in result.graph.nodes:
            assert node.all_dimensions_present(), (
                f"{fname}: node {node.path} missing dimensions"
            )

    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_paths_unique(self, adversarial_results, fname):
        result = adversarial_results[fname]
        paths = [n.path for n in result.graph.nodes]
        assert len(paths) == len(set(paths)), f"{fname}: duplicate paths"

    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_preservation_scores_in_range(self, adversarial_results, fname):
        result = adversarial_results[fname]
        for art in result.artifacts:
            assert 0.0 <= art.preservation_score <= 1.0, (
                f"{fname}: {art.target_name} score {art.preservation_score} out of range"
            )

    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_artifact_schema_valid(self, adversarial_results, fname):
        result = adversarial_results[fname]
        for art in result.artifacts:
            d = art.to_dict()
            for key in ("target_name", "target_language", "capabilities",
                        "output_files", "degradation_report", "preservation_score"):
                assert key in d, f"{fname}: artifact missing {key}"


# ---------------------------------------------------------------------------
# Equilibrium handles complex rule sets
# ---------------------------------------------------------------------------


class TestEquilibriumOnAdversarial:
    def test_rain_composition_has_equilibrium_rules(self, adversarial_results):
        result = adversarial_results["01_rain_composition.orn"]
        assert len(result.graph.equilibrium_rules) >= 5

    def test_assistive_arm_safety_rules_present(self, adversarial_results):
        result = adversarial_results["02_assistive_arm.orn"]
        rule_names = {r.name for r in result.graph.equilibrium_rules}
        assert any("safety" in name for name in rule_names)

    def test_revenue_contract_has_many_rules(self, adversarial_results):
        result = adversarial_results["03_revenue_contract.orn"]
        # The revenue contract has 9 equilibrium rules.
        assert len(result.graph.equilibrium_rules) >= 8

    def test_lighthouse_has_ending_dignity_rule(self, adversarial_results):
        result = adversarial_results["04_lighthouse.orn"]
        rule_names = {r.name for r in result.graph.equilibrium_rules}
        assert any("ending" in name or "dignity" in name for name in rule_names)

    def test_sign_bridge_has_privacy_rule(self, adversarial_results):
        result = adversarial_results["05_sign_bridge.orn"]
        rule_names = {r.name for r in result.graph.equilibrium_rules}
        assert any("privacy" in name for name in rule_names)

    def test_still_water_has_never_startle_rule(self, adversarial_results):
        result = adversarial_results["06_still_water.orn"]
        rule_names = {r.name for r in result.graph.equilibrium_rules}
        assert any("startle" in name or "gentle" in name for name in rule_names)

    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_equilibrium_resolver_runs_cleanly(self, adversarial_results, fname):
        result = adversarial_results[fname]
        # The resolver should not leave crashes; unresolved conflicts are OK.
        assert result.equilibrium_report is not None


# ---------------------------------------------------------------------------
# Code generation works on adversarial input
# ---------------------------------------------------------------------------


class TestCodegenOnAdversarial:
    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_codegen_runs_for_all_targets(self, adversarial_results, fname):
        result = adversarial_results[fname]
        for tgt in result.graph.realization_targets:
            files = generate_code(result.graph, tgt)
            assert len(files) > 0, f"{fname}: no files for {tgt.name}"
            for code in files.values():
                assert len(code) > 0

    def test_python_files_are_parseable(self, adversarial_results):
        """All generated Python must be syntactically valid."""
        for fname, result in adversarial_results.items():
            for tgt in result.graph.realization_targets:
                files = generate_code(result.graph, tgt)
                for fpath, code in files.items():
                    if fpath.endswith(".py"):
                        try:
                            compile(code, fpath, "exec")
                        except SyntaxError as e:
                            pytest.fail(f"{fname} {fpath}: {e}")

    def test_html_files_have_doctype(self, adversarial_results):
        for fname, result in adversarial_results.items():
            for tgt in result.graph.realization_targets:
                if "html" not in tgt.language.lower():
                    continue
                files = generate_code(result.graph, tgt)
                for fpath, code in files.items():
                    if fpath.endswith(".html"):
                        assert code.startswith("<!DOCTYPE html>"), (
                            f"{fname} {fpath}: missing DOCTYPE"
                        )


# ---------------------------------------------------------------------------
# Preview generation works on adversarial input
# ---------------------------------------------------------------------------


class TestPreviewOnAdversarial:
    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_preview_html_generated(self, adversarial_results, fname):
        result = adversarial_results[fname]
        html_str = generate_preview(result.graph, artifacts=result.artifacts)
        assert "<!DOCTYPE html>" in html_str
        assert "<html" in html_str
        assert "</html>" in html_str

    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_preview_contains_entity_cards(self, adversarial_results, fname):
        result = adversarial_results[fname]
        html_str = generate_preview(result.graph, artifacts=result.artifacts)
        # At least some entities should render as cards.
        assert "entity-card" in html_str

    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_preview_contains_equilibrium_panel(self, adversarial_results, fname):
        result = adversarial_results[fname]
        html_str = generate_preview(result.graph, artifacts=result.artifacts)
        assert "equilibrium" in html_str.lower()

    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_preview_contains_realization_panel(self, adversarial_results, fname):
        """Each realization target should be mentioned somewhere in the preview,
        regardless of which layout strategy is used."""
        result = adversarial_results[fname]
        html_str = generate_preview(result.graph, artifacts=result.artifacts)
        # At least one target name should appear.
        assert any(tgt.name in html_str for tgt in result.graph.realization_targets)
        # The word "preservation" or the scores should appear.
        assert "preservation" in html_str.lower() or any(
            f"{a.preservation_score:.2f}" in html_str for a in result.artifacts
        )

    @pytest.mark.parametrize("fname", ADVERSARIAL_FILES)
    def test_preview_contains_degradation_markers(self, adversarial_results, fname):
        result = adversarial_results[fname]
        html_str = generate_preview(result.graph, artifacts=result.artifacts)
        # PROXY / BRIDGE / degradation should appear somewhere.
        assert "proxy" in html_str.lower() or "degradation" in html_str.lower()


# ---------------------------------------------------------------------------
# Specific adversarial expectations
# ---------------------------------------------------------------------------


class TestAdversarialSpecifics:
    def test_lighthouse_has_five_endings(self, adversarial_results):
        result = adversarial_results["04_lighthouse.orn"]
        ending_nodes = [
            n for n in result.graph.nodes
            if n.name.startswith("ending_")
        ]
        assert len(ending_nodes) >= 5

    def test_assistive_arm_has_safety_monitor(self, adversarial_results):
        result = adversarial_results["02_assistive_arm.orn"]
        safety_nodes = [
            n for n in result.graph.nodes
            if "safety" in n.name or "emergency" in n.name
        ]
        assert len(safety_nodes) >= 2

    def test_revenue_contract_has_dedup_clause(self, adversarial_results):
        result = adversarial_results["03_revenue_contract.orn"]
        # The dedup clause must be present as a node.
        dedup_nodes = [n for n in result.graph.nodes if "dedup" in n.name]
        assert len(dedup_nodes) >= 1

    def test_sign_bridge_has_visual_and_haptic_outputs(self, adversarial_results):
        result = adversarial_results["05_sign_bridge.orn"]
        names = {n.name for n in result.graph.nodes}
        assert "visual_panel" in names
        assert "haptic_unit" in names

    def test_still_water_never_displays_score(self, adversarial_results):
        """The meditation app must have a conditional forbidding score display."""
        result = adversarial_results["06_still_water.orn"]
        found_forbidden = False
        for node in result.graph.nodes:
            for cond in node.get_dimension(Dimension.CONDITIONAL):
                if isinstance(cond, dict):
                    action = str(cond.get("action", "")).lower()
                    condition = str(cond.get("condition", "")).lower()
                    # The parser puts "never" as the action and "displays timer"
                    # as the condition. Either way, we should find a forbidden
                    # display rule.
                    if action == "never" and any(
                        word in condition
                        for word in ("score", "timer", "streak")
                    ):
                        found_forbidden = True
        assert found_forbidden, "still_water must forbid score/timer/streak display"

    def test_rain_composition_has_emotion_to_density_mapping(self, adversarial_results):
        result = adversarial_results["01_rain_composition.orn"]
        # The conditional dimension should mention user_sad and user_happy.
        all_conditions = []
        for node in result.graph.nodes:
            for cond in node.get_dimension(Dimension.CONDITIONAL):
                if isinstance(cond, dict):
                    all_conditions.append(str(cond.get("condition", "")).lower())
        joined = " ".join(all_conditions)
        assert "sad" in joined
        assert "happy" in joined
