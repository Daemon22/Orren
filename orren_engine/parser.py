"""
Orren Engine — Co-Parser
========================

Architecture (per 07_VALIDATION_v3.md):

    PARSER  =  Lexer  +  Section splitter  +  Dimension parsers
    1 file  →  N expressions

The validation report calls this coordinated multi-parser the "Parser".
In the production test plan it is referred to as the "Co-parser" because
the lexer, the section splitter, and the nine dimension parsers cooperate
under a single coordination layer rather than running as a monolithic
grammar.

Sections handled (13 raw section keywords → 9 dimension builders):
    context, structure, cognitive, vibe, spatial, temporal,
    relational, conditional, behavior, calibrate, degrade,
    equilibrium, realize

Public API:
    CoParser().parse(source: str) -> List[Expression]
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple

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
    EquilibriumCondition,
    EquilibriumResolution,
    EquilibriumRule,
    Expression,
    ExpressionType,
    LifecycleTransition,
    RealizationTarget,
    RelationalStatement,
    SpatialStatement,
    StructureNode,
    TemporalStatement,
    ToleranceLevel,
    VibeStatement,
)

# ---------------------------------------------------------------------------
# Lexer
# ---------------------------------------------------------------------------

SECTION_KEYWORDS: Tuple[str, ...] = (
    "context",
    "structure",
    "cognitive",
    "vibe",
    "spatial",
    "temporal",
    "relational",
    "conditional",
    "behavior",
    "calibrate",
    "degrade",
    "equilibrium",
    "realize",
)

CREATE_RE = re.compile(
    r"""^\s*create\s+
        (?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*
        (?P<type>[A-Za-z_][A-Za-z0-9_]*)\s*$""",
    re.VERBOSE,
)

SECTION_HEADER_RE = re.compile(
    r"""^\s*(?P<keyword>"""
    + "|".join(SECTION_KEYWORDS)
    + r""")\s*:\s*$"""
)

# Calibration sub-header:  calibrate TERM for DIM:
CALIBRATE_SUB_RE = re.compile(
    r"""^\s*calibrate\s+
        (?P<term>[\"\w\s]+?)\s+for\s+
        (?P<dim>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*$""",
    re.VERBOSE,
)

# Realization target sub-header:  target: NAME (LANG)
REALIZE_TARGET_RE = re.compile(
    r"""^\s*target:\s*
        (?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\(
        (?P<lang>[^)]+)\)\s*$""",
    re.VERBOSE,
)

# Equilibrium rule header:  name:
EQUILIBRIUM_RULE_RE = re.compile(
    r"""^\s*(?P<name>[a-z][a-z0-9_]*)\s*:\s*$"""
)


class LexedLine:
    """A single lexed line with metadata."""

    __slots__ = ("text", "stripped", "indent", "lineno", "is_blank", "is_comment")

    def __init__(self, text: str, lineno: int) -> None:
        self.text = text.rstrip("\n")
        self.stripped = self.text.strip()
        self.indent = len(self.text) - len(self.text.lstrip(" "))
        self.lineno = lineno
        self.is_blank = (self.stripped == "")
        self.is_comment = self.stripped.startswith("#")


def lex(source: str) -> List[LexedLine]:
    """Tokenize source into LexedLines. Comments and blank lines preserved
    (downstream filters them where appropriate)."""
    return [LexedLine(line, i + 1) for i, line in enumerate(source.splitlines())]


# ---------------------------------------------------------------------------
# Section splitter
# ---------------------------------------------------------------------------


@dataclass
class _Section:
    """A contiguous run of lines belonging to one section keyword."""

    keyword: str = ""
    header_line: int = 0
    body: List[str] = field(default_factory=list)
    sub_name: Optional[str] = None
    sub_dim: Optional[str] = None


def split_expressions(lines: List[LexedLine]) -> List[Tuple[int, List[LexedLine]]]:
    """Split lexed lines into one chunk per `create` block.

    Returns a list of (start_line, chunk_lines) pairs. Lines before the
    first `create` (e.g. comments) are attached to the first block.
    """
    chunks: List[Tuple[int, List[LexedLine]]] = []
    current: List[LexedLine] = []
    current_start: int = 0
    saw_create = False
    for ln in lines:
        m = CREATE_RE.match(ln.text)
        if m:
            if saw_create and current:
                chunks.append((current_start, current))
            current = [ln]
            current_start = ln.lineno
            saw_create = True
        else:
            if not saw_create and not ln.is_blank and not ln.is_comment:
                # File does not start with `create` — treat the whole file
                # as a single anonymous expression.
                saw_create = True
                current_start = ln.lineno
            current.append(ln)
    if saw_create and current:
        chunks.append((current_start, current))
    return chunks


def split_sections(chunk: List[LexedLine]) -> List[_Section]:
    """Within one expression chunk, split into sections.

    A section starts at a line matching SECTION_HEADER_RE. Sub-headers
    (calibrate TERM for DIM:, target: NAME (LANG), equilibrium rule name:)
    are returned as separate _Section entries with sub_name / sub_dim set.
    """
    sections: List[_Section] = []
    current: Optional[_Section] = None
    for ln in chunk:
        if ln.is_blank or ln.is_comment:
            continue
        m = SECTION_HEADER_RE.match(ln.text)
        if m:
            if current is not None:
                sections.append(current)
            current = _Section(m.group("keyword"), ln.lineno, [])
            continue
        # Sub-headers only valid inside certain sections.
        if current is not None and current.keyword == "calibrate":
            sub = CALIBRATE_SUB_RE.match(ln.text)
            if sub:
                if current.body:
                    sections.append(current)
                current = _Section(
                    "calibrate",
                    ln.lineno,
                    [],
                    sub_name=sub.group("term").strip().strip('"'),
                    sub_dim=sub.group("dim"),
                )
                continue
        if current is not None and current.keyword == "realize":
            sub = REALIZE_TARGET_RE.match(ln.text)
            if sub:
                if current.body:
                    sections.append(current)
                current = _Section(
                    "realize",
                    ln.lineno,
                    [],
                    sub_name=sub.group("name"),
                    sub_dim=sub.group("lang").strip(),
                )
                continue
        if current is not None and current.keyword == "equilibrium":
            sub = EQUILIBRIUM_RULE_RE.match(ln.text)
            if sub and _looks_like_rule_header(sub.group("name"), current.body):
                if current.body:
                    sections.append(current)
                current = _Section(
                    "equilibrium",
                    ln.lineno,
                    [],
                    sub_name=sub.group("name"),
                )
                continue
        if current is None:
            # Lines outside any section — skip but record.
            continue
        # Preserve original text (with leading whitespace) so the
        # structure parser can compute indentation. _strip_prefix will
        # handle the stripping for parsers that don't need indent.
        current.body.append(f"{ln.lineno}:{ln.text.rstrip()}")
    if current is not None:
        sections.append(current)
    return sections


def _looks_like_rule_header(name: str, current_body: List[str]) -> bool:
    """A bare `name:` line is a rule header only if we're already inside
    an equilibrium block AND the previous body content was a rule (or empty).
    This avoids mistaking `key:` lines in other sections."""
    # We only call this when current.keyword == 'equilibrium'.
    # A rule header is followed by indented content; if the previous body
    # ended with `rationale:` or `resolution:` or is empty, this is a new
    # rule.
    if not current_body:
        return True
    last = current_body[-1].split(":", 1)[1].strip().lower()
    return last.startswith("rationale") or last.startswith("resolution")


# ---------------------------------------------------------------------------
# Dimension parsers
# ---------------------------------------------------------------------------


def _line_no(body_line: str) -> int:
    """Extract the line-number prefix added by split_sections."""
    head, _, _ = body_line.partition(":")
    try:
        return int(head)
    except ValueError:
        return 0


def _strip_prefix(body_line: str) -> str:
    """Strip the line-number prefix."""
    _, _, rest = body_line.partition(":")
    return rest.strip()


def _parse_context(body: List[str]) -> List[ContextStatement]:
    out: List[ContextStatement] = []
    # Continuation lines: a line starting with whitespace beyond the
    # previous key's indent continues the previous value.
    last_key: Optional[str] = None
    last_value: List[str] = []
    last_line: int = 0
    for raw in body:
        ln = _line_no(raw)
        text = _strip_prefix(raw)
        if not text:
            continue
        # `key: value` or `key value`
        m = re.match(r"^(?P<key>[A-Za-z_][\w]*)\s*[:=]\s*(?P<val>.*)$", text)
        if m:
            if last_key is not None:
                out.append(
                    ContextStatement(
                        key=last_key, value=" ".join(last_value).strip(), line=last_line
                    )
                )
            last_key = m.group("key")
            last_value = [m.group("val")]
            last_line = ln
        else:
            if last_key is not None:
                last_value.append(text)
    if last_key is not None:
        out.append(
            ContextStatement(
                key=last_key, value=" ".join(last_value).strip(), line=last_line
            )
        )
    return out


def _parse_structure(body: List[str]) -> List[StructureNode]:
    """Parse an indented structure tree."""
    nodes: List[StructureNode] = []
    stack: List[Tuple[int, StructureNode]] = []
    for raw in body:
        ln = _line_no(raw)
        text = _strip_prefix(raw)
        if not text:
            continue
        # Strip the line-number prefix already removed; now compute raw indent.
        # The _strip_prefix already stripped leading whitespace, so we
        # recover indent from the original `raw` after the `lineno:` prefix.
        _, _, rest = raw.partition(":")
        indent = len(rest) - len(rest.lstrip(" "))
        name = rest.strip()
        # Skip sub-labels like 'microphone_control.icon' inside a node —
        # those are properties of the node, not children.
        # We treat any '.' in name as a property reference and attach to
        # the nearest matching parent.
        node = StructureNode(name=name, indent=indent, line=ln)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        if stack:
            node.parent = stack[-1][1]
            stack[-1][1].children.append(node)
        nodes.append(node)
        stack.append((indent, node))
    return nodes


def _parse_cognitive(body: List[str]) -> List[CognitiveStatement]:
    out: List[CognitiveStatement] = []
    for raw in body:
        ln = _line_no(raw)
        text = _strip_prefix(raw)
        if not text:
            continue
        # subject.predicate = value   OR   subject.action = value
        m = re.match(
            r"^(?P<subj>[A-Za-z_][\w.]*)\.(?P<pred>[A-Za-z_][\w]*)\s*=\s*(?P<val>.*)$",
            text,
        )
        if m:
            out.append(
                CognitiveStatement(
                    subject=m.group("subj"),
                    predicate=m.group("pred"),
                    value=m.group("val").strip(),
                    line=ln,
                )
            )
            continue
        # Plain `subject = value` form
        m = re.match(r"^(?P<subj>[A-Za-z_][\w.]*)\s*=\s*(?P<val>.*)$", text)
        if m:
            out.append(
                CognitiveStatement(
                    subject=m.group("subj"),
                    predicate="value",
                    value=m.group("val").strip(),
                    line=ln,
                )
            )
    return out


def _parse_vibe(body: List[str]) -> List[VibeStatement]:
    out: List[VibeStatement] = []
    pending_annotation: Optional[str] = None
    pending_line: int = 0
    for raw in body:
        ln = _line_no(raw)
        text = _strip_prefix(raw)
        if not text:
            continue
        # Annotation in parentheses on its own line: (not pulse, not flash)
        # May appear EITHER before OR after the vibe statement it annotates.
        if text.startswith("(") and text.endswith(")"):
            annotation = text[1:-1].strip()
            if out and out[-1].annotation is None:
                # Attach to the previous statement (annotation-after form).
                out[-1].annotation = annotation
            else:
                # Stash for the next statement (annotation-before form).
                pending_annotation = annotation
                pending_line = ln
            continue
        m = re.match(
            r"^(?P<subj>[A-Za-z_][\w.]*)\.(?P<aspect>[A-Za-z_][\w]*)\s*=\s*(?P<term>.*)$",
            text,
        )
        if m:
            out.append(
                VibeStatement(
                    subject=m.group("subj"),
                    aspect=m.group("aspect"),
                    term=m.group("term").strip().strip('"'),
                    annotation=pending_annotation,
                    line=ln,
                )
            )
            pending_annotation = None
            continue
        # Bare `subject = term` form
        m = re.match(r"^(?P<subj>[A-Za-z_][\w.]*)\s*=\s*(?P<term>.*)$", text)
        if m:
            out.append(
                VibeStatement(
                    subject=m.group("subj"),
                    aspect="default",
                    term=m.group("term").strip().strip('"'),
                    annotation=pending_annotation,
                    line=ln,
                )
            )
            pending_annotation = None
    return out


def _parse_spatial(body: List[str]) -> List[SpatialStatement]:
    out: List[SpatialStatement] = []
    for raw in body:
        ln = _line_no(raw)
        text = _strip_prefix(raw)
        if not text:
            continue
        m = re.match(
            r"^(?P<subj>[A-Za-z_][\w.]*)\s+(?P<rel>located_in|scoped_to)\s+(?P<tgt>.+)$",
            text,
        )
        if m:
            out.append(
                SpatialStatement(
                    subject=m.group("subj"),
                    relation=m.group("rel"),
                    target=m.group("tgt").strip(),
                    line=ln,
                )
            )
    return out


def _parse_temporal(body: List[str]) -> List[TemporalStatement]:
    out: List[TemporalStatement] = []
    for raw in body:
        ln = _line_no(raw)
        text = _strip_prefix(raw)
        if not text:
            continue
        # A → B on TRIGGER
        m = re.match(
            r"^(?P<src>[A-Za-z_][\w ]*?)\s*→\s*(?P<tgt>[A-Za-z_][\w ]*?)\s+on\s+(?P<trig>.+)$",
            text,
        )
        if m:
            out.append(
                TemporalStatement(
                    kind="transition",
                    source=m.group("src").strip(),
                    target=m.group("tgt").strip(),
                    trigger=m.group("trig").strip(),
                    line=ln,
                )
            )
            continue
        # A → B  (no trigger)
        m = re.match(
            r"^(?P<src>[A-Za-z_][\w ]*?)\s*→\s*(?P<tgt>.+)$", text
        )
        if m:
            out.append(
                TemporalStatement(
                    kind="sequence",
                    source=m.group("src").strip(),
                    target=m.group("tgt").strip(),
                    line=ln,
                )
            )
            continue
        # X persists beyond Y
        m = re.match(
            r"^(?P<src>[A-Za-z_][\w ]*?)\s+persists\s+(?:beyond|after)\s+(?P<tgt>.+)$",
            text,
        )
        if m:
            out.append(
                TemporalStatement(
                    kind="persistence",
                    source=m.group("src").strip(),
                    target=m.group("tgt").strip(),
                    line=ln,
                )
            )
    return out


def _parse_relational(body: List[str]) -> List[RelationalStatement]:
    out: List[RelationalStatement] = []
    for raw in body:
        ln = _line_no(raw)
        text = _strip_prefix(raw)
        if not text:
            continue
        m = re.match(
            r"^(?P<src>[A-Za-z_][\w.]*)\s+(?P<rel>feeds|triggers|produces|depends_on)\s+(?P<tgt>[A-Za-z_][\w.]*)\s*(?:\((?P<qual>[^)]+)\))?\s*$",
            text,
        )
        if m:
            out.append(
                RelationalStatement(
                    source=m.group("src"),
                    relation=m.group("rel"),
                    target=m.group("tgt"),
                    qualifier=m.group("qual"),
                    line=ln,
                )
            )
    return out


def _parse_conditional(body: List[str]) -> List[ConditionalStatement]:
    out: List[ConditionalStatement] = []
    for raw in body:
        ln = _line_no(raw)
        text = _strip_prefix(raw)
        if not text:
            continue
        # unconditional preservation: X retained always (...)
        m = re.match(
            r"^(?P<subj>[A-Za-z_][\w.]*)\s+(?P<act>retained)\s+(?P<cond>always|unconditionally)\s*(?:\((?P<note>[^)]+)\))?\s*$",
            text,
        )
        if m:
            out.append(
                ConditionalStatement(
                    subject=m.group("subj"),
                    action=m.group("act"),
                    condition=m.group("cond"),
                    unconditional=True,
                    line=ln,
                )
            )
            continue
        # subject activates/begins/deactivates/retained/intensifies/lightens/etc.
        # on|when CONDITION  — accepts both 'on' and 'when' as the trigger word,
        # and any verb as the action (natural-language tolerant).
        m = re.match(
            r"^(?P<subj>[A-Za-z_][\w.]*)\s+(?P<act>[a-z_]+)\s+(?:on|when)\s+(?P<cond>.+)$",
            text,
        )
        if m:
            out.append(
                ConditionalStatement(
                    subject=m.group("subj"),
                    action=m.group("act"),
                    condition=m.group("cond").strip(),
                    unconditional=False,
                    line=ln,
                )
            )
            continue
        # Negative form: subject never does X  (e.g. "still_water never displays timer")
        m = re.match(
            r"^(?P<subj>[A-Za-z_][\w.]*)\s+never\s+(?P<cond>.+)$",
            text,
        )
        if m:
            out.append(
                ConditionalStatement(
                    subject=m.group("subj"),
                    action="never",
                    condition=m.group("cond").strip(),
                    unconditional=False,
                    line=ln,
                )
            )
            continue
        # Blocked-when form: X blocked when Y  (e.g. "cloud_processing blocked when privacy_mode_on")
        m = re.match(
            r"^(?P<subj>[A-Za-z_][\w.]*)\s+blocked\s+(?:on|when)\s+(?P<cond>.+)$",
            text,
        )
        if m:
            out.append(
                ConditionalStatement(
                    subject=m.group("subj"),
                    action="blocked",
                    condition=m.group("cond").strip(),
                    unconditional=False,
                    line=ln,
                )
            )
    return out


def _parse_behavior(body: List[List[str]]) -> List[BehavioralStatement]:
    # `body` is a flat list of `lineno:text` strings.
    out: List[BehavioralStatement] = []
    for raw in body:
        ln = _line_no(raw)
        text = _strip_prefix(raw)
        if not text:
            continue
        # behaves_as
        m = re.match(
            r"^(?P<subj>[A-Za-z_][\w.]*)\s+behaves_as\s+(?P<role>.+)$", text
        )
        if m:
            out.append(
                BehavioralStatement(
                    subject=m.group("subj"),
                    kind="behaves_as",
                    role=m.group("role").strip(),
                    line=ln,
                )
            )
            continue
        # responds_to STIMULUS with RESPONSE
        m = re.match(
            r"^(?P<subj>[A-Za-z_][\w.]*)\s+responds_to\s+(?P<stim>[A-Za-z_][\w.]*)\s+with\s+(?P<resp>.+)$",
            text,
        )
        if m:
            out.append(
                BehavioralStatement(
                    subject=m.group("subj"),
                    kind="responds_to",
                    stimulus=m.group("stim"),
                    response=m.group("resp").strip(),
                    line=ln,
                )
            )
            continue
        # transitions from A to B on EVENT
        m = re.match(
            r"^(?P<subj>[A-Za-z_][\w.]*)\s+transitions\s+from\s+(?P<from>[A-Za-z_][\w]*)\s+to\s+(?P<to>[A-Za-z_][\w]*)\s+on\s+(?P<evt>.+)$",
            text,
        )
        if m:
            out.append(
                BehavioralStatement(
                    subject=m.group("subj"),
                    kind="transitions",
                    from_state=m.group("from"),
                    to_state=m.group("to"),
                    on_event=m.group("evt").strip(),
                    line=ln,
                )
            )
            continue
        # lifecycle: A -> B -> C -> D   (uses ASCII arrow because CJK arrow
        # already used by temporal; lifecycle uses literal '->' form too)
        m = re.match(
            r"^(?P<subj>[A-Za-z_][\w.]*)\s+lifecycle:\s*(?P<chain>.+)$", text
        )
        if m:
            chain_text = m.group("chain").strip()
            # accept both -> and →
            chain_text = chain_text.replace("→", "->")
            states = [s.strip() for s in chain_text.split("->")]
            transitions = [
                LifecycleTransition(from_state=states[i], to_state=states[i + 1])
                for i in range(len(states) - 1)
            ]
            out.append(
                BehavioralStatement(
                    subject=m.group("subj"),
                    kind="lifecycle",
                    lifecycle=transitions,
                    line=ln,
                )
            )
    return out


def _parse_calibrate(sections: List[_Section]) -> List[CalibrationEntry]:
    """Calibrate is split across multiple _Section entries (one per
    `calibrate TERM for DIM:` block). Group them into entries."""
    out: List[CalibrationEntry] = []
    for sec in sections:
        if sec.keyword != "calibrate":
            continue
        if sec.sub_name is None:
            continue
        entry = CalibrationEntry(
            term=sec.sub_name, dimension=sec.sub_dim or "", line=sec.header_line
        )
        current_target: Optional[CalibrationTarget] = None
        for raw in sec.body:
            ln = _line_no(raw)
            text = _strip_prefix(raw)
            if not text:
                continue
            m = re.match(r"^maps_to\s+(.+)$", text)
            if m:
                current_target = CalibrationTarget(
                    maps_to=m.group(1).strip(), threshold=""
                )
                continue
            m = re.match(r"^threshold:\s*(.+)$", text)
            if m and current_target is not None:
                current_target.threshold = m.group(1).strip()
                continue
            m = re.match(r"^signal:\s*(.+)$", text)
            if m and current_target is not None:
                current_target.signal = m.group(1).strip()
                continue
            m = re.match(r"^note:\s*(.+)$", text)
            if m and current_target is not None:
                current_target.note = m.group(1).strip()
                continue
        if current_target is not None:
            entry.targets.append(current_target)
        out.append(entry)
    return out


def _parse_degrade(body: List[str]) -> List[DegradationEntry]:
    out: List[DegradationEntry] = []
    for raw in body:
        ln = _line_no(raw)
        text = _strip_prefix(raw)
        if not text:
            continue
        m = re.match(
            r"^(?P<mode>tolerate|require)\s+(?P<level>full|faithful|conventional|proxy|documented|optional)\s+for\s+(?P<dim>\w+)\s+on\s+(?P<aspect>.+)$",
            text,
        )
        if m:
            out.append(
                DegradationEntry(
                    level=ToleranceLevel(m.group("level")),
                    dimension=m.group("dim"),
                    aspect=m.group("aspect").strip(),
                    mode=m.group("mode"),
                )
            )
    return out


def _parse_equilibrium(sections: List[_Section]) -> List[EquilibriumRule]:
    """Equilibrium is split across multiple _Section entries (one per
    named rule). Group them into EquilibriumRule objects."""
    out: List[EquilibriumRule] = []
    for sec in sections:
        if sec.keyword != "equilibrium":
            continue
        if sec.sub_name is None:
            continue
        rule = EquilibriumRule(name=sec.sub_name, line=sec.header_line)
        conditions_buffer: List[EquilibriumCondition] = []
        for raw in sec.body:
            ln = _line_no(raw)
            text = _strip_prefix(raw)
            if not text:
                continue
            # when  DIM.PRED  AND  DIM.PRED ...
            if text.startswith("when"):
                cond_text = text[4:].strip()
                parts = re.split(r"\s+AND\s+", cond_text)
                for p in parts:
                    pm = re.match(r"^(?P<dim>\w+)\.(?P<pred>.+)$", p.strip())
                    if pm:
                        conditions_buffer.append(
                            EquilibriumCondition(
                                dimension=pm.group("dim"),
                                predicate=pm.group("pred").strip(),
                            )
                        )
                continue
            m = re.match(r"^preserve\s+(.+)$", text)
            if m:
                rule.preserve.extend(
                    [s.strip() for s in m.group(1).split(" and ")]
                )
                continue
            m = re.match(r"^resolution:\s*(.+)$", text)
            if m:
                rule.resolution = EquilibriumResolution(text=m.group(1).strip())
                continue
            m = re.match(r"^rationale:\s*(.+)$", text)
            if m:
                rule.rationale = m.group(1).strip()
                continue
        rule.conditions = conditions_buffer
        out.append(rule)
    return out


def _parse_realize(sections: List[_Section]) -> List[RealizationTarget]:
    out: List[RealizationTarget] = []
    for sec in sections:
        if sec.keyword != "realize":
            continue
        if sec.sub_name is None:
            continue
        tgt = RealizationTarget(name=sec.sub_name, language=sec.sub_dim or "")
        for raw in sec.body:
            ln = _line_no(raw)
            text = _strip_prefix(raw)
            if not text:
                continue
            m = re.match(r"^capabilities:\s*(.+)$", text)
            if m:
                tgt.capabilities = [s.strip() for s in m.group(1).split(",")]
                continue
            m = re.match(r"^can_express:\s*(.+)$", text)
            if m:
                tgt.can_express = [s.strip() for s in m.group(1).split(",")]
                continue
            m = re.match(r"^needs_bridge:\s*(.+)$", text)
            if m:
                tgt.needs_bridge = [s.strip() for s in m.group(1).split(",")]
                continue
            m = re.match(r"^cannot_express:\s*(.+)$", text)
            if m:
                tgt.cannot_express = [s.strip() for s in m.group(1).split(",")]
                continue
            m = re.match(r"^degradation:\s*(.+)$", text)
            if m:
                # Format: aspect = level, aspect = level
                pairs = m.group(1).split(",")
                for p in pairs:
                    if "=" in p:
                        asp, lvl = p.split("=", 1)
                        asp = asp.strip()
                        lvl = lvl.strip()
                        try:
                            tgt.degradation.append(
                                DegradationEntry(
                                    level=ToleranceLevel(lvl),
                                    dimension="vibe",  # default; refined later
                                    aspect=asp,
                                )
                            )
                        except ValueError:
                            pass
                continue
            m = re.match(r"^preservation_score:\s*([\d.]+)$", text)
            if m:
                try:
                    tgt.preservation_score = float(m.group(1))
                except ValueError:
                    pass
        out.append(tgt)
    return out


# ---------------------------------------------------------------------------
# Dimension parser registry (9)
# ---------------------------------------------------------------------------

DIMENSION_PARSERS: Dict[str, Callable[[List[str]], Any]] = {
    "context": _parse_context,
    "structure": _parse_structure,
    "cognitive": _parse_cognitive,
    "vibe": _parse_vibe,
    "spatial": _parse_spatial,
    "temporal": _parse_temporal,
    "relational": _parse_relational,
    "conditional": _parse_conditional,
    "behavior": _parse_behavior,
}


# ---------------------------------------------------------------------------
# CoParser — coordination layer
# ---------------------------------------------------------------------------


class CoParser:
    """Coordinated multi-parser. Lexer + section splitter + dimension parsers.

    Public API:
        parse(source) -> List[Expression]
    """

    def __init__(self) -> None:
        self.last_lexed: List[LexedLine] = []
        self.last_sections: Dict[int, List[_Section]] = {}

    def parse(self, source: str) -> List[Expression]:
        lines = lex(source)
        self.last_lexed = lines
        chunks = split_expressions(lines)
        expressions: List[Expression] = []
        for start_line, chunk in chunks:
            sections = split_sections(chunk)
            self.last_sections[start_line] = sections
            expr = self._build_expression(chunk, sections)
            expressions.append(expr)
        return expressions

    # -- internal --------------------------------------------------------

    def _build_expression(
        self, chunk: List[LexedLine], sections: List[_Section]
    ) -> Expression:
        # The first non-blank/non-comment line is the `create` header.
        name = "anonymous"
        etype = ExpressionType.UNSPECIFIED
        for ln in chunk:
            if ln.is_blank or ln.is_comment:
                continue
            m = CREATE_RE.match(ln.text)
            if m:
                name = m.group("name")
                try:
                    etype = ExpressionType(m.group("type"))
                except ValueError:
                    etype = ExpressionType.UNSPECIFIED
                break
        expr = Expression(name=name, type=etype, source_line=0)
        # Apply each dimension parser to its section(s).
        for sec in sections:
            parser = DIMENSION_PARSERS.get(sec.keyword)
            if parser is not None:
                payload = parser(sec.body)
                if sec.keyword == "context":
                    expr.context.extend(payload)
                elif sec.keyword == "structure":
                    expr.structure.extend(payload)
                else:
                    # Stash the parsed payload keyed by dimension keyword.
                    expr.raw_sections.setdefault(sec.keyword, [])
                    # Serialize payload into a stable list-of-dicts form.
                    expr.raw_sections[sec.keyword].extend(_payload_to_dicts(payload))
            elif sec.keyword == "calibrate":
                # Handled in batch below.
                pass
            elif sec.keyword == "degrade":
                entries = _parse_degrade(sec.body)
                expr.raw_sections.setdefault("degrade", [])
                expr.raw_sections["degrade"].extend(
                    {
                        "level": e.level.value,
                        "dimension": e.dimension,
                        "aspect": e.aspect,
                        "mode": e.mode,
                    }
                    for e in entries
                )
            elif sec.keyword == "equilibrium":
                # Handled in batch below.
                pass
            elif sec.keyword == "realize":
                # Handled in batch below.
                pass
        # Batch sections that span multiple sub-headers.
        calibrations = _parse_calibrate(sections)
        if calibrations:
            expr.raw_sections["calibrate"] = [
                {
                    "term": c.term,
                    "dimension": c.dimension,
                    "targets": [
                        {
                            "maps_to": t.maps_to,
                            "threshold": t.threshold,
                            "signal": t.signal,
                            "note": t.note,
                        }
                        for t in c.targets
                    ],
                }
                for c in calibrations
            ]
        rules = _parse_equilibrium(sections)
        if rules:
            expr.raw_sections["equilibrium"] = [
                {
                    "name": r.name,
                    "conditions": [
                        {"dimension": c.dimension, "predicate": c.predicate}
                        for c in r.conditions
                    ],
                    "preserve": r.preserve,
                    "resolution": r.resolution.text if r.resolution else None,
                    "rationale": r.rationale,
                }
                for r in rules
            ]
        targets = _parse_realize(sections)
        if targets:
            expr.raw_sections["realize"] = [
                {
                    "name": t.name,
                    "language": t.language,
                    "capabilities": t.capabilities,
                    "can_express": t.can_express,
                    "needs_bridge": t.needs_bridge,
                    "cannot_express": t.cannot_express,
                    "degradation": [
                        {
                            "level": d.level.value,
                            "dimension": d.dimension,
                            "aspect": d.aspect,
                            "mode": d.mode,
                        }
                        for d in t.degradation
                    ],
                    "preservation_score": t.preservation_score,
                }
                for t in targets
            ]
        return expr


def _payload_to_dicts(payload: Any) -> List[Dict[str, object]]:
    """Convert a list of dataclass instances to a list of dicts."""
    if payload is None:
        return []
    out: List[Dict[str, object]] = []
    for item in payload:
        if hasattr(item, "__dataclass_fields__"):
            d: Dict[str, object] = {}
            for f in item.__dataclass_fields__:
                v = getattr(item, f)
                if isinstance(v, list) and v and hasattr(v[0], "__dataclass_fields__"):
                    d[f] = _payload_to_dicts(v)
                else:
                    d[f] = v
            out.append(d)
        else:
            out.append({"value": item})
    return out


__all__ = [
    "CoParser",
    "lex",
    "split_expressions",
    "split_sections",
    "DIMENSION_PARSERS",
    "SECTION_KEYWORDS",
]
