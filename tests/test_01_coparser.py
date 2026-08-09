"""Co-parser unit tests.

Covers:
  - Lexer (lex)
  - Section splitter (split_expressions, split_sections)
  - All 9 dimension parsers (context, structure, cognitive, vibe, spatial,
    temporal, relational, conditional, behavior)
  - Auxiliary section parsers (calibrate, degrade, equilibrium, realize)
  - CoParser.parse() end-to-end coordination

Run: pytest tests/test_01_coparser.py -v
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from orren_engine.parser import (
    CoParser,
    SECTION_KEYWORDS,
    _parse_behavior,
    _parse_calibrate,
    _parse_cognitive,
    _parse_conditional,
    _parse_context,
    _parse_degrade,
    _parse_equilibrium,
    _parse_realize,
    _parse_relational,
    _parse_spatial,
    _parse_structure,
    _parse_temporal,
    _parse_vibe,
    lex,
    split_expressions,
    split_sections,
)
from orren_engine.data_model import (
    BehavioralStatement,
    CognitiveStatement,
    ConditionalStatement,
    ContextStatement,
    ExpressionType,
    SpatialStatement,
    StructureNode,
    ToleranceLevel,
    VibeStatement,
)


# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------


class TestLexer:
    def test_lex_basic(self):
        lines = lex("create app : Application\n    context:\n        purpose: x\n")
        assert len(lines) == 3
        assert lines[0].lineno == 1
        assert lines[0].stripped == "create app : Application"
        assert lines[0].indent == 0

    def test_lex_indent(self):
        lines = lex("    hello\n        world\n")
        assert lines[0].indent == 4
        assert lines[1].indent == 8

    def test_lex_blank_and_comment(self):
        lines = lex("# comment\n\nreal\n")
        assert lines[0].is_comment
        assert lines[1].is_blank
        assert not lines[2].is_blank and not lines[2].is_comment

    def test_lex_empty(self):
        assert lex("") == []

    def test_lex_no_trailing_newline(self):
        lines = lex("create app : Application")
        assert len(lines) == 1


# ---------------------------------------------------------------------------
# Section splitter — split_expressions
# ---------------------------------------------------------------------------


class TestSplitExpressions:
    def test_single_expression(self):
        src = "create app : Application\n    context:\n        purpose: x\n"
        chunks = split_expressions(lex(src))
        assert len(chunks) == 1

    def test_multiple_expressions(self):
        src = (
            "create app1 : Application\n    context:\n        purpose: a\n"
            "create app2 : Application\n    context:\n        purpose: b\n"
        )
        chunks = split_expressions(lex(src))
        assert len(chunks) == 2

    def test_no_create_returns_empty(self):
        # No `create` lines = no expressions.
        chunks = split_expressions(lex("# just a comment\n"))
        assert chunks == []

    def test_chunk_includes_header_line(self):
        src = "create app : Application\n    context:\n        purpose: x\n"
        chunks = split_expressions(lex(src))
        first_line = chunks[0][1][0]
        assert "create app" in first_line.text


# ---------------------------------------------------------------------------
# Section splitter — split_sections
# ---------------------------------------------------------------------------


class TestSplitSections:
    def test_recognizes_all_section_keywords(self):
        # All 13 raw keywords should be recognized.
        for kw in SECTION_KEYWORDS:
            src = f"create app : Application\n    {kw}:\n        content\n"
            sections = split_sections(split_expressions(lex(src))[0][1])
            keywords_seen = {s.keyword for s in sections if s.keyword == kw}
            assert keywords_seen == {kw}, f"keyword {kw} not recognized"

    def test_calibrate_subheader(self):
        src = (
            "create app : Application\n"
            "    calibrate:\n"
            "        calibrate emerald for vibe:\n"
            "            maps_to color_hue\n"
        )
        sections = split_sections(split_expressions(lex(src))[0][1])
        calibrate_sections = [s for s in sections if s.keyword == "calibrate"]
        assert len(calibrate_sections) == 1
        assert calibrate_sections[0].sub_name == "emerald"
        assert calibrate_sections[0].sub_dim == "vibe"

    def test_realize_target_subheader(self):
        src = (
            "create app : Application\n"
            "    realize:\n"
            "        target: web (HTML/CSS/JS)\n"
            "            capabilities: layout\n"
        )
        sections = split_sections(split_expressions(lex(src))[0][1])
        realize_sections = [s for s in sections if s.keyword == "realize"]
        assert len(realize_sections) == 1
        assert realize_sections[0].sub_name == "web"
        assert realize_sections[0].sub_dim == "HTML/CSS/JS"

    def test_blank_lines_ignored(self):
        src = (
            "create app : Application\n"
            "    context:\n"
            "\n"
            "        purpose: x\n"
            "\n"
        )
        sections = split_sections(split_expressions(lex(src))[0][1])
        ctx = [s for s in sections if s.keyword == "context"]
        assert len(ctx) == 1
        assert len(ctx[0].body) == 1


# ---------------------------------------------------------------------------
# Dimension parsers (9)
# ---------------------------------------------------------------------------


class TestContextParser:
    def test_basic_key_value(self):
        body = ["3:        purpose: a microphone control"]
        out = _parse_context(body)
        assert len(out) == 1
        assert out[0].key == "purpose"
        assert out[0].value == "a microphone control"

    def test_continuation_line(self):
        body = [
            "3:        purpose: a microphone control",
            "4:                 that is calm",
        ]
        out = _parse_context(body)
        assert len(out) == 1
        assert "calm" in out[0].value

    def test_equals_form(self):
        body = ["3:        audience = someone"]
        out = _parse_context(body)
        assert out[0].key == "audience"
        assert out[0].value == "someone"


class TestStructureParser:
    def test_flat(self):
        body = ["3:        home"]
        out = _parse_structure(body)
        assert len(out) == 1
        assert out[0].name == "home"
        assert out[0].parent is None

    def test_nested(self):
        body = [
            "3:        home",
            "4:            microphone_control",
            "5:                icon",
        ]
        out = _parse_structure(body)
        assert len(out) == 3
        assert out[0].name == "home"
        assert out[1].name == "microphone_control"
        assert out[2].name == "icon"
        assert out[1].parent is out[0]
        assert out[2].parent is out[1]
        # path
        assert out[2].path() == "home.microphone_control.icon"

    def test_sibling_nodes(self):
        body = [
            "3:        home",
            "4:            a",
            "5:            b",
        ]
        out = _parse_structure(body)
        assert out[1].parent is out[0]
        assert out[2].parent is out[0]


class TestCognitiveParser:
    def test_dotted_subject(self):
        body = ["3:        microphone_control.activation = on_user_intent"]
        out = _parse_cognitive(body)
        assert len(out) == 1
        assert out[0].subject == "microphone_control"
        assert out[0].predicate == "activation"
        assert out[0].value == "on_user_intent"

    def test_plain_subject(self):
        body = ["3:        total = 42"]
        out = _parse_cognitive(body)
        assert out[0].subject == "total"
        assert out[0].predicate == "value"


class TestVibeParser:
    def test_dotted_aspect(self):
        body = ["3:        microphone_control.color_character = emerald"]
        out = _parse_vibe(body)
        assert len(out) == 1
        assert out[0].subject == "microphone_control"
        assert out[0].aspect == "color_character"
        assert out[0].term == "emerald"

    def test_annotation_paren(self):
        body = [
            "3:        microphone_control.activation_signal = steady_glow",
            "4:            (not pulse, not flash)",
        ]
        out = _parse_vibe(body)
        assert out[0].annotation is not None
        assert "not pulse" in out[0].annotation

    def test_quoted_term(self):
        body = ['3:        microphone_control.aesthetic = "music for idealists"']
        out = _parse_vibe(body)
        assert out[0].term == "music for idealists"


class TestSpatialParser:
    def test_located_in(self):
        body = ["3:        microphone_control located_in home"]
        out = _parse_spatial(body)
        assert out[0].subject == "microphone_control"
        assert out[0].relation == "located_in"
        assert out[0].target == "home"

    def test_scoped_to(self):
        body = ["3:        microphone_control scoped_to home.primary_surface"]
        out = _parse_spatial(body)
        assert out[0].relation == "scoped_to"


class TestTemporalParser:
    def test_transition_with_trigger(self):
        body = ["3:        activation → recording on user_touch"]
        out = _parse_temporal(body)
        assert out[0].kind == "transition"
        assert out[0].source == "activation"
        assert out[0].target == "recording"
        assert out[0].trigger == "user_touch"

    def test_sequence_no_trigger(self):
        body = ["3:        stopping → transcription"]
        out = _parse_temporal(body)
        assert out[0].kind == "sequence"
        assert out[0].trigger is None

    def test_persistence(self):
        body = ["3:        original_audio persists beyond transcription"]
        out = _parse_temporal(body)
        assert out[0].kind == "persistence"
        assert out[0].source == "original_audio"


class TestRelationalParser:
    def test_feeds(self):
        body = ["3:        microphone_control feeds device_microphone"]
        out = _parse_relational(body)
        assert out[0].source == "microphone_control"
        assert out[0].relation == "feeds"
        assert out[0].target == "device_microphone"

    def test_qualifier(self):
        body = ["3:        volume_button feeds microphone_control (when pressed × 2)"]
        out = _parse_relational(body)
        assert out[0].qualifier == "when pressed × 2"


class TestConditionalParser:
    def test_activates_on(self):
        body = ["3:        microphone_control activates on double_click"]
        out = _parse_conditional(body)
        assert out[0].action == "activates"
        assert out[0].condition == "double_click"
        assert not out[0].unconditional

    def test_unconditional_preservation(self):
        body = ["3:        original_audio retained always (unconditional preservation)"]
        out = _parse_conditional(body)
        assert out[0].unconditional is True
        assert out[0].action == "retained"


class TestBehaviorParser:
    def test_behaves_as(self):
        body = ["3:        microphone_control behaves_as organic_toggle"]
        out = _parse_behavior(body)
        assert out[0].kind == "behaves_as"
        assert out[0].role == "organic_toggle"

    def test_responds_to(self):
        body = [
            "3:        microphone_control responds_to activation_intent with steady_glow_ramp"
        ]
        out = _parse_behavior(body)
        assert out[0].kind == "responds_to"
        assert out[0].stimulus == "activation_intent"
        assert out[0].response == "steady_glow_ramp"

    def test_transitions(self):
        body = [
            "3:        microphone_control transitions from idle to active on activation_intent"
        ]
        out = _parse_behavior(body)
        assert out[0].kind == "transitions"
        assert out[0].from_state == "idle"
        assert out[0].to_state == "active"
        assert out[0].on_event == "activation_intent"

    def test_lifecycle_ascii_arrow(self):
        body = ["3:        microphone_control lifecycle: idle -> active -> recording -> processing -> idle"]
        out = _parse_behavior(body)
        assert out[0].kind == "lifecycle"
        assert len(out[0].lifecycle) == 4
        assert out[0].lifecycle[0].from_state == "idle"
        assert out[0].lifecycle[0].to_state == "active"
        assert out[0].lifecycle[-1].to_state == "idle"

    def test_lifecycle_unicode_arrow(self):
        body = ["3:        mic lifecycle: idle → active → recording"]
        out = _parse_behavior(body)
        assert len(out[0].lifecycle) == 2


# ---------------------------------------------------------------------------
# Auxiliary section parsers
# ---------------------------------------------------------------------------


class TestCalibrateParser:
    def test_basic_entry(self):
        # Build fake _Section list
        from orren_engine.parser import _Section

        sec = _Section(
            keyword="calibrate",
            header_line=3,
            sub_name="emerald",
            sub_dim="vibe",
            body=[
                "4:            maps_to color_hue",
                "5:            threshold: hue in [150°, 170°]",
                "6:            signal: css_color_value",
            ],
        )
        out = _parse_calibrate([sec])
        assert len(out) == 1
        assert out[0].term == "emerald"
        assert out[0].dimension == "vibe"
        assert len(out[0].targets) == 1
        assert out[0].targets[0].maps_to == "color_hue"
        assert "150" in out[0].targets[0].threshold
        assert out[0].targets[0].signal == "css_color_value"


class TestDegradeParser:
    def test_tolerate(self):
        body = ["3:        tolerate faithful for vibe on color_character"]
        out = _parse_degrade(body)
        assert out[0].level == ToleranceLevel.FAITHFUL
        assert out[0].dimension == "vibe"
        assert out[0].aspect == "color_character"
        assert out[0].mode == "tolerate"

    def test_require(self):
        body = ["3:        require full for cognitive on activation_logic"]
        out = _parse_degrade(body)
        assert out[0].level == ToleranceLevel.FULL
        assert out[0].mode == "require"


class TestEquilibriumParser:
    def test_full_rule(self):
        from orren_engine.parser import _Section

        sec = _Section(
            keyword="equilibrium",
            header_line=3,
            sub_name="calmness_preserves_urgency",
            body=[
                "4:            when vibe.calm is active AND cognitive.activation is active",
                "5:            preserve both",
                "6:            resolution: express urgency as steady_glow",
                "7:            rationale: calm does not mean no signal",
            ],
        )
        out = _parse_equilibrium([sec])
        assert len(out) == 1
        assert out[0].name == "calmness_preserves_urgency"
        assert len(out[0].conditions) == 2
        assert out[0].conditions[0].dimension == "vibe"
        assert out[0].conditions[0].predicate == "calm is active"
        assert "both" in out[0].preserve
        assert "steady_glow" in out[0].resolution.text


class TestRealizeParser:
    def test_full_target(self):
        from orren_engine.parser import _Section

        sec = _Section(
            keyword="realize",
            header_line=3,
            sub_name="web_interface",
            sub_dim="HTML/CSS/JS",
            body=[
                "4:            capabilities: layout, color, motion",
                "5:            can_express: spatial, vibe",
                "6:            needs_bridge: device_microphone",
                "7:            cannot_express: aesthetic",
                "8:            preservation_score: 0.83",
            ],
        )
        out = _parse_realize([sec])
        assert len(out) == 1
        assert out[0].name == "web_interface"
        assert out[0].language == "HTML/CSS/JS"
        assert "layout" in out[0].capabilities
        assert "spatial" in out[0].can_express
        assert "device_microphone" in out[0].needs_bridge
        assert "aesthetic" in out[0].cannot_express
        assert out[0].preservation_score == 0.83


# ---------------------------------------------------------------------------
# CoParser end-to-end
# ---------------------------------------------------------------------------


class TestCoParserEndToEnd:
    def test_parse_single_expression(self):
        src = (
            "create app : Application\n"
            "    context:\n"
            "        purpose: test\n"
            "    cognitive:\n"
            "        app.value = 42\n"
        )
        parser = CoParser()
        exprs = parser.parse(src)
        assert len(exprs) == 1
        assert exprs[0].name == "app"
        assert exprs[0].type == ExpressionType.APPLICATION
        assert len(exprs[0].context) == 1
        assert "cognitive" in exprs[0].raw_sections

    def test_parse_multiple_expressions(self):
        src = (
            "create app1 : Application\n"
            "    context:\n"
            "        purpose: a\n"
            "create app2 : Subsystem\n"
            "    context:\n"
            "        purpose: b\n"
        )
        parser = CoParser()
        exprs = parser.parse(src)
        assert len(exprs) == 2
        assert exprs[0].name == "app1"
        assert exprs[1].name == "app2"
        assert exprs[1].type == ExpressionType.SUBSYSTEM

    def test_parse_empty_file(self):
        parser = CoParser()
        assert parser.parse("") == []

    def test_parse_preserves_line_numbers(self):
        src = (
            "create app : Application\n"
            "    context:\n"
            "        purpose: test\n"
        )
        parser = CoParser()
        exprs = parser.parse(src)
        assert exprs[0].context[0].line == 3

    def test_parse_unknown_type_falls_back(self):
        src = "create app : SomeUnknownType\n    context:\n        purpose: x\n"
        parser = CoParser()
        exprs = parser.parse(src)
        assert exprs[0].type == ExpressionType.UNSPECIFIED
