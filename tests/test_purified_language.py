from orren_engine import PurifiedParser, PurifiedSyntaxError


SOURCE = '''
entity sensor: device = "soil moisture sensor" {
    intent "measure soil moisture"
    behavior "emit measurement"
    temporal "active while the controller is running"
}

entity controller: process = "irrigation controller" {
    intent "maintain irrigation conditions"
}

relation sensor -> controller: dependency when controller.active
constraint sensor.value > 0

scope irrigation {
    entity valve: device = "water valve"
}
'''


def test_purified_program_has_only_canonical_constructs():
    program = PurifiedParser().parse_program(SOURCE)
    assert [e.name for e in program.entities] == ["sensor", "controller", "valve"]
    assert program.entities[0].meaning == "soil moisture sensor"
    assert program.entities[0].intent == "measure soil moisture"
    assert program.entities[0].behavior == "emit measurement"
    assert program.entities[0].temporal == "active while the controller is running"
    assert len(program.relations) == 1
    assert program.relations[0].relation_type == "dependency"
    assert len(program.constraints) == 1
    assert program.scopes == ["irrigation"]


def test_purified_parser_lowers_to_existing_expression_model():
    expressions = PurifiedParser().parse(SOURCE)
    assert len(expressions) == 1
    expr = expressions[0]
    assert expr.name == "sensor"
    assert expr.structure
    assert expr.structure[0].name == "sensor"
    assert "relational" in expr.raw_sections
    assert "conditional" in expr.raw_sections
    assert "intent" in expr.raw_sections
    assert "behavior" in expr.raw_sections
    assert "temporal" in expr.raw_sections


def test_old_dimensions_are_not_part_of_purified_syntax():
    for source in (
        "vibe:\n    sensor.tone = calm",
        "cognitive:\n    sensor reason = test",
        "equilibrium:\n    conflict:",
        "realize:\n    target: python (Python)",
    ):
        try:
            PurifiedParser().parse_program(source)
        except PurifiedSyntaxError:
            pass
        else:
            raise AssertionError("legacy dimension syntax must not be accepted by purified parser")
