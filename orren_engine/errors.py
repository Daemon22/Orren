"""
Orren Engine — Error Semantics
==============================

The language distinguishes 9 categories of parse-time and resolve-time
condition, per Phase 3 of the completion plan:

    1.  valid input            — parses cleanly, no issues
    2.  invalid syntax         — source violates the grammar
    3.  incomplete input       — grammar is valid but a required section
                                  or field is absent (e.g. `create` with
                                  no body)
    4.  ambiguous input        — source is syntactically valid but
                                  semantically ambiguous (e.g. a subject
                                  reference that could resolve to
                                  multiple nodes)
    5.  unknown concepts       — identifiers or values not recognized
                                  (e.g. an unknown tolerance level,
                                  an unknown dimension name)
    6.  conflicting requirements — equilibrium conflict with no rule
                                  that resolves it
    7.  unsupported realization — a target language that cannot
                                  express a dimension
    8.  recoverable degradation — a dimension degrades to a proxy
                                  but the tolerance level allows it
    9.  unrecoverable errors   — everything else; the engine cannot
                                  produce a meaningful result

Classes:
    OrrenError              — base, carries (code, message, line, category)
    OrrenSyntaxError        — category 2
    OrrenIncompleteError     — category 3
    OrrenAmbiguityError      — category 4
    OrrenUnknownConceptError — category 5
    OrrenConflictError       — category 6
    OrrenUnsupportedTarget   — category 7
    OrrenRecoverableWarning  — category 8
    OrrenUnrecoverableError  — category 9

ErrorCollector is a simple mutable container that accumulates errors
during parsing.  CoParser stores errors on ``self.errors``; callers can
inspect them after ``parse()`` returns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class ErrorCategory(Enum):
    """The 9 error categories from Phase 3."""

    VALID = "valid_input"
    SYNTAX = "invalid_syntax"
    INCOMPLETE = "incomplete_input"
    AMBIGUOUS = "ambiguous_input"
    UNKNOWN = "unknown_concept"
    CONFLICT = "conflicting_requirements"
    UNSUPPORTED = "unsupported_realization"
    RECOVERABLE = "recoverable_degradation"
    UNRECOVERABLE = "unrecoverable_error"


# Short numeric codes for programmatic testing.
class ErrorCode:
    """Stable string codes for each error subclass."""

    MALFORMED_CREATE = "E001"          # create header is malformed
    UNKNOWN_SECTION = "E002"           # unknown section keyword
    UNKNOWN_DIMENSION = "E003"         # unknown dimension name
    UNKNOWN_TOLERANCE = "E004"         # unknown tolerance level
    MALFORMED_STATEMENT = "E005"       # statement doesn't match any pattern
    INCOMPLETE_EXPRESSION = "E006"     # create with no body
    AMBIGUOUS_REFERENCE = "E007"       # subject resolves to >1 node
    UNKNOWN_TARGET = "E008"            # unknown realization target
    CONFLICT_UNRESOLVED = "E009"       # equilibrium conflict with no resolution
    UNSUPPORTED_LANGUAGE = "E010"      # target language not supported
    DEGRADATION_REQUIRED = "E011"      # required degradation not tolerated
    EMPTY_SOURCE = "E012"              # file has no content at all


@dataclass
class OrrenError:
    """A single language-level error or warning.

    ``category`` is one of the 9 ErrorCategory values.
    ``code`` is a stable string from ErrorCode.
    ``message`` is human-readable.
    ``line`` is 1-based source line (0 if not applicable).
    """

    code: str
    message: str
    category: ErrorCategory = ErrorCategory.UNRECOVERABLE
    line: int = 0

    def __str__(self) -> str:
        if self.line:
            return f"[{self.code}] line {self.line}: {self.message}"
        return f"[{self.code}] {self.message}"

    def __lt__(self, other: "OrrenError") -> bool:
        # Deterministic ordering for stable error output.
        return (self.line, self.code) < (other.line, other.code)


class OrrenSyntaxError(OrrenError):
    pass


class OrrenIncompleteError(OrrenError):
    pass


class OrrenAmbiguityError(OrrenError):
    pass


class OrrenUnknownConceptError(OrrenError):
    pass


class OrrenConflictError(OrrenError):
    pass


class OrrenUnsupportedTarget(OrrenError):
    pass


class OrrenRecoverableWarning(OrrenError):
    pass


class OrrenUnrecoverableError(OrrenError):
    pass


@dataclass
class ErrorCollector:
    """Collects errors during parsing and resolution.

    The CoParser and other pipeline stages append to a shared collector
    so callers can inspect all issues after ``parse()`` returns.
    """

    errors: List[OrrenError] = field(default_factory=list)

    def add(
        self,
        code: str,
        message: str,
        category: ErrorCategory = ErrorCategory.UNRECOVERABLE,
        line: int = 0,
    ) -> None:
        self.errors.append(OrrenError(code, message, category, line))

    def add_error(self, error: OrrenError) -> None:
        self.errors.append(error)

    def clear(self) -> None:
        self.errors.clear()

    @property
    def has_errors(self) -> bool:
        return any(e.category != ErrorCategory.RECOVERABLE for e in self.errors)

    @property
    def has_unrecoverable(self) -> bool:
        return any(
            e.category == ErrorCategory.UNRECOVERABLE for e in self.errors
        )

    def by_category(self, cat: ErrorCategory) -> List[OrrenError]:
        return [e for e in self.errors if e.category == cat]

    def sorted(self) -> List[OrrenError]:
        """Return errors sorted by line then code (deterministic)."""
        return sorted(self.errors)

    def __len__(self) -> int:
        return len(self.errors)

    def __iter__(self):
        return iter(self.errors)


__all__ = [
    "ErrorCategory",
    "ErrorCode",
    "OrrenError",
    "OrrenSyntaxError",
    "OrrenIncompleteError",
    "OrrenAmbiguityError",
    "OrrenUnknownConceptError",
    "OrrenConflictError",
    "OrrenUnsupportedTarget",
    "OrrenRecoverableWarning",
    "OrrenUnrecoverableError",
    "ErrorCollector",
]
