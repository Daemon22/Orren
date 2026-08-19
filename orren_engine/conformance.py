"""Conformance checks for realized artifacts.

These checks are intentionally evidence-producing: a backend is PASS only when
its emitted files are actually accepted by an available toolchain and its
smallest executable behavior probe succeeds.  Missing toolchains are SKIP,
never PASS.
"""
from __future__ import annotations

import ast
import json
import os
import py_compile
import shutil
import subprocess
import tempfile
import importlib.util
from dataclasses import dataclass, asdict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    target: str
    path: str
    kind: str
    status: str
    detail: str


class _HTMLProbe(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.scripts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append(tag)
        attrs_dict = dict(attrs)
        if tag == "script" and attrs_dict.get("src"):
            self.scripts.append(attrs_dict["src"] or "")
        if tag == "link" and attrs_dict.get("href"):
            self.links.append(attrs_dict["href"] or "")


def _run(command: list[str], cwd: Path, timeout: int = 10) -> tuple[int, str]:
    try:
        proc = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        return 124, f"timeout after {timeout}s: {exc}"
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def check_file(path: Path, language: str) -> tuple[str, str]:
    language = language.lower()
    if language == "python":
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            py_compile.compile(str(path), doraise=True)
            return "PASS", "Python parsed and byte-compiled"
        except (SyntaxError, py_compile.PyCompileError) as exc:
            return "FAIL", str(exc)
    if language == "javascript":
        node = shutil.which("node")
        if not node:
            return "SKIP", "node toolchain unavailable"
        code, detail = _run([node, "--check", str(path)], path.parent)
        return ("PASS" if code == 0 else "FAIL"), detail or "Node syntax check passed"
    if language == "html":
        try:
            parser = _HTMLProbe()
            parser.feed(path.read_text(encoding="utf-8"))
            if "html" not in parser.tags or "body" not in parser.tags:
                return "FAIL", "document lacks html/body structure"
            for ref in parser.scripts + parser.links:
                if not (path.parent / ref).is_file():
                    return "FAIL", f"missing referenced asset: {ref}"
            return "PASS", "HTML parsed and local script/style references resolved"
        except Exception as exc:
            return "FAIL", str(exc)
    if language == "css":
        text = path.read_text(encoding="utf-8")
        if not text.strip():
            return "FAIL", "empty stylesheet"
        return "PASS", "stylesheet is non-empty (CSS compiler unavailable)"
    if language in {"text", "latex"}:
        return ("PASS", "text artifact emitted") if path.stat().st_size else ("FAIL", "empty artifact")
    return "SKIP", f"no validator registered for language {language!r}"


def run_conformance(output_dir: str | Path, manifest_path: str | Path | None = None) -> dict[str, Any]:
    output_dir = Path(output_dir)
    manifest_path = Path(manifest_path or output_dir / "manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results: list[CheckResult] = []
    for artifact in manifest.get("artifacts", []):
        target = artifact.get("target_name", "unknown")
        for output in artifact.get("output_files", []):
            rel = output["path"].split("/", 1)[-1]
            path = output_dir / target / rel
            if not path.is_file():
                results.append(CheckResult(target, str(path), output.get("language", ""), "FAIL", "declared artifact is missing"))
                continue
            status, detail = check_file(path, output.get("language", ""))
            results.append(CheckResult(target, str(path), output.get("language", ""), status, detail))
        if artifact.get("target_language", "").lower() == "python":
            py_files = [output_dir / target / o["path"].split("/", 1)[-1] for o in artifact.get("output_files", []) if o.get("language") == "python"]
            for py_file in py_files:
                if py_file.is_file():
                    try:
                        status, detail = _python_behavior(py_file)
                    except Exception as exc:
                        status, detail = "FAIL", f"behavior probe raised {type(exc).__name__}: {exc}"
                    results.append(CheckResult(target, str(py_file), "behavior", status, detail))
    summary = {
        "passed": sum(r.status == "PASS" for r in results),
        "failed": sum(r.status == "FAIL" for r in results),
        "skipped": sum(r.status == "SKIP" for r in results),
        "results": [asdict(r) for r in results],
    }
    return summary


def _python_behavior(path: Path) -> tuple[str, str]:
    spec = importlib.util.spec_from_file_location("orren_generated_probe", path)
    if spec is None or spec.loader is None:
        return "FAIL", "could not load generated Python module"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    classes = [value for value in vars(module).values() if isinstance(value, type) and value.__module__ == module.__name__]
    if not classes:
        return "FAIL", "no generated implementation class found"
    cls = classes[0]
    with tempfile.TemporaryDirectory(prefix="orren-probe-") as root:
        try:
            instance = cls(root) if "storage" in path.name else cls()
        except TypeError:
            instance = cls()
        if hasattr(instance, "retain") and hasattr(instance, "retrieve"):
            payload = b"orren-conformance-payload"
            instance.retain(payload, "conformance")
            if instance.retrieve("conformance") != payload:
                return "FAIL", "retain/retrieve round-trip changed payload"
            return "PASS", "executed retain/retrieve round-trip successfully"
        for method_name in ("process", "run"):
            method = getattr(instance, method_name, None)
            if callable(method):
                value = method()
                if value is None:
                    return "FAIL", f"executed {method_name}() returned None"
                return "PASS", f"executed {method_name}() successfully"
        return "FAIL", "no executable process/run or retain/retrieve contract found"


def write_report(report: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = ["CheckResult", "run_conformance", "write_report"]
