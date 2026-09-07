"""Minimal shim for Zaryel validation utilities.

This file provides lightweight stand-ins for the real `zaryel_validator`
implementation so the Python package can import and basic checks can run.

The real validator may perform deep structural validation; this shim
returns an empty report (no issues) and preserves the expected API.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ZaryelIssue:
    path: str
    message: str
    severity: str = "warning"


@dataclass
class ZaryelReport:
    issues: List[ZaryelIssue]

    def __init__(self, issues: Optional[List[ZaryelIssue]] = None) -> None:
        self.issues = issues or []

    def is_clean(self) -> bool:
        return len(self.issues) == 0

    def summary(self) -> str:
        if self.is_clean():
            return "Zaryel: no issues"
        return f"Zaryel: {len(self.issues)} issues"


def validate_zaryel(source: str) -> ZaryelReport:
    """Validate a zaryel source string.

    This shim performs no validation and returns a clean report.
    The real implementation should replace this with full checks.
    """
    return ZaryelReport()


def validate_zaryel_graph(graph) -> ZaryelReport:
    """Validate an in-memory SIR/IR graph.

    The shim assumes the graph is valid and returns an empty report.
    """
    return ZaryelReport()


__all__ = ["ZaryelIssue", "ZaryelReport", "validate_zaryel", "validate_zaryel_graph"]
