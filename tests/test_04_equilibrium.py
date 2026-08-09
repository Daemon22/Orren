"""Equilibrium resolver — determinism + edge case tests.

Validates:
  - Determinism: same input → same resolution, every time.
  - Rule application order: rules fire in file order.
  - Conflict detection: known patterns are detected.
  - Preservation contracts: rule.preserve is honored in the outcome.
  - Resolution text stamped onto nodes as EQUILIBRIUM dimension payload.
  - Edge cases:
      * No rules → no outcomes, no unresolved conflicts.
      * Rules that don't fire → no outcomes.
      * Multiple rules on same node → all fire (in order).
      * Rule with no resolution text → still records outcome.
      * Rule with no preserve list → empty preserve in outcome.
      * Rule referencing unknown dimension → does not fire.

Run: pytest tests/test_04_equilibrium.py -v
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from orren_engine import (
    CoParser,
    Dimension,
    EquilibriumResolver,
    SIRBuilder,
)


# ---------------------------------------------------------------------------
# Source with a known conflict (calm vibe + activation cognitive)
# ---------------------------------------------------------------------------

SOURCE_WITH_CONFLICT = """create app : Application

    structure:
        control

    cognitive:
        control.activation = on_user_intent

    vibe:
        control.tone = calm

    equilibrium:
        calmness_preserves_urgency:
            when vibe.calm is active AND cognitive.activation is active
            preserve both
            resolution: express urgency as steady_glow
            rationale: calm does not mean no signal
"""


SOURCE_NO_CONFLICT = """create app : Application

    structure:
        control

    cognitive:
        control.activation = on_user_intent

    vibe:
        control.color_character = emerald
"""


SOURCE_MULTIPLE_RULES = """create app : Application

    structure:
        control

    cognitive:
        control.activation = on_user_intent
        control.recording = capture_audio

    vibe:
        control.tone = calm
        control.aesthetic = music

    equilibrium:
        calmness_preserves_urgency:
            when vibe.calm is active AND cognitive.activation is active
            preserve both
            resolution: express urgency as steady_glow

        aesthetic_preserves_function:
            when vibe.aesthetic is active AND cognitive.recording is active
            preserve both
            resolution: aesthetic affects surfaces only
"""


@pytest.fixture
def resolver():
    return EquilibriumResolver()


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_same_input_same_output(self, resolver):
        graph1 = SIRBuilder().build(CoParser().parse(SOURCE_WITH_CONFLICT))
        graph2 = SIRBuilder().build(CoParser().parse(SOURCE_WITH_CONFLICT))
        report1 = resolver.resolve(graph1)
        report2 = resolver.resolve(graph2)
        assert report1.signature() == report2.signature()

    def test_resolution_signature_stable_across_runs(self, resolver):
        sigs = []
        for _ in range(5):
            graph = SIRBuilder().build(CoParser().parse(SOURCE_WITH_CONFLICT))
            sigs.append(resolver.resolve(graph).signature())
        assert len(set(sigs)) == 1

    def test_rule_order_preserved(self, resolver):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_MULTIPLE_RULES))
        report = resolver.resolve(graph)
        # Both rules should fire, in file order.
        assert len(report.outcomes) == 2
        assert report.outcomes[0].rule_name == "calmness_preserves_urgency"
        assert report.outcomes[1].rule_name == "aesthetic_preserves_function"


# ---------------------------------------------------------------------------
# Conflict detection
# ---------------------------------------------------------------------------


class TestConflictDetection:
    def test_calm_vs_urgency_detected(self, resolver):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_WITH_CONFLICT))
        report = resolver.resolve(graph)
        # The conflict is resolved by the rule, so it should NOT appear
        # in unresolved_conflicts. But the rule outcome should be present.
        assert len(report.outcomes) == 1
        assert report.outcomes[0].rule_name == "calmness_preserves_urgency"

    def test_unresolved_conflict_when_no_rule(self, resolver):
        # SOURCE_NO_CONFLICT has activation cognitive but no calm vibe,
        # so no conflict. But let's add a conflict without a rule.
        src = """create app : Application
    structure:
        control
    cognitive:
        control.activation = on_user_intent
        control.recording = capture_audio
    vibe:
        control.tone = calm
        control.aesthetic = music
"""
        graph = SIRBuilder().build(CoParser().parse(src))
        report = resolver.resolve(graph)
        # No equilibrium section → no rules fire.
        assert len(report.outcomes) == 0
        # But the calm-vs-urgency conflict should be detected as unresolved.
        conflict_names = {c["name"] for c in report.unresolved_conflicts}
        assert "calm_vs_urgency" in conflict_names
        assert "aesthetic_vs_function" in conflict_names

    def test_no_conflict_no_unresolved(self, resolver):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_NO_CONFLICT))
        report = resolver.resolve(graph)
        assert report.unresolved_conflicts == []


# ---------------------------------------------------------------------------
# Preservation contracts
# ---------------------------------------------------------------------------


class TestPreservation:
    def test_preserve_list_recorded(self, resolver):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_WITH_CONFLICT))
        report = resolver.resolve(graph)
        assert "both" in report.outcomes[0].preserve

    def test_resolution_text_recorded(self, resolver):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_WITH_CONFLICT))
        report = resolver.resolve(graph)
        assert "steady_glow" in report.outcomes[0].resolution_text

    def test_rationale_recorded(self, resolver):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_WITH_CONFLICT))
        report = resolver.resolve(graph)
        assert "calm does not mean no signal" in report.outcomes[0].rationale

    def test_resolution_stamped_on_node(self, resolver):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_WITH_CONFLICT))
        resolver.resolve(graph)
        node = graph.find("app.control")
        eq_payload = node.get_dimension(Dimension.EQUILIBRIUM)
        assert len(eq_payload) == 1
        assert eq_payload[0]["rule"] == "calmness_preserves_urgency"
        assert "steady_glow" in eq_payload[0]["resolution"]


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_no_rules_no_outcomes(self, resolver):
        src = """create app : Application
    structure:
        control
    cognitive:
        control.activation = on_user_intent
"""
        graph = SIRBuilder().build(CoParser().parse(src))
        report = resolver.resolve(graph)
        assert report.outcomes == []

    def test_rule_doesnt_fire_when_condition_missing(self, resolver):
        src = """create app : Application
    structure:
        control
    cognitive:
        control.recording = capture_audio
    vibe:
        control.color_character = emerald
    equilibrium:
        calmness_preserves_urgency:
            when vibe.calm is active AND cognitive.activation is active
            preserve both
            resolution: x
"""
        graph = SIRBuilder().build(CoParser().parse(src))
        report = resolver.resolve(graph)
        assert report.outcomes == []

    def test_rule_with_no_resolution(self, resolver):
        src = """create app : Application
    structure:
        control
    cognitive:
        control.activation = on_user_intent
    vibe:
        control.tone = calm
    equilibrium:
        bare_rule:
            when vibe.calm is active AND cognitive.activation is active
            preserve both
"""
        graph = SIRBuilder().build(CoParser().parse(src))
        report = resolver.resolve(graph)
        assert len(report.outcomes) == 1
        assert report.outcomes[0].resolution_text is None

    def test_rule_with_empty_preserve(self, resolver):
        src = """create app : Application
    structure:
        control
    cognitive:
        control.activation = on_user_intent
    vibe:
        control.tone = calm
    equilibrium:
        no_preserve:
            when vibe.calm is active AND cognitive.activation is active
            resolution: x
"""
        graph = SIRBuilder().build(CoParser().parse(src))
        report = resolver.resolve(graph)
        assert report.outcomes[0].preserve == []

    def test_rule_with_unknown_dimension_doesnt_fire(self, resolver):
        src = """create app : Application
    structure:
        control
    cognitive:
        control.activation = on_user_intent
    vibe:
        control.tone = calm
    equilibrium:
        unknown_dim_rule:
            when nonsense.foo is active AND cognitive.activation is active
            preserve both
            resolution: x
"""
        graph = SIRBuilder().build(CoParser().parse(src))
        report = resolver.resolve(graph)
        assert report.outcomes == []

    def test_multiple_rules_same_node_all_fire(self, resolver):
        graph = SIRBuilder().build(CoParser().parse(SOURCE_MULTIPLE_RULES))
        report = resolver.resolve(graph)
        # Both rules fire on the same node (app.control).
        assert len(report.outcomes) == 2
        assert all(o.node_path == "app.control" for o in report.outcomes)

    def test_empty_graph(self, resolver):
        from orren_engine.data_model import SIRGraph

        graph = SIRGraph()
        report = resolver.resolve(graph)
        assert report.outcomes == []
        assert report.unresolved_conflicts == []

    def test_report_signature_stable(self, resolver):
        graph1 = SIRBuilder().build(CoParser().parse(SOURCE_MULTIPLE_RULES))
        graph2 = SIRBuilder().build(CoParser().parse(SOURCE_MULTIPLE_RULES))
        sig1 = resolver.resolve(graph1).signature()
        sig2 = resolver.resolve(graph2).signature()
        assert sig1 == sig2
