"""Orren CLI — command-line entry point.

Usage:
    orren parse FILE              Parse and print expression summary.
    orren sir FILE                Parse + build SIR; print node summary.
    orren resolve FILE            Parse + SIR + equilibrium; print report.
    orren realize FILE [--out D]  Full pipeline; write generated artifacts to D.
    orren preview FILE [--out F]  Generate a self-contained HTML preview.
    orren validate FILE           Run basic checks against FILE.
    orren validate-suite          Run the canonical 48-test validation suite.
    orren hash FILE               Print a content hash of the SIR (reproducibility).
    orren --version

Reproducibility contract:
    The same .orn source MUST produce the same SIR hash and the same
    generated artifacts, byte-for-byte, on every run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from . import __version__
from .engine import Engine
from .parser import CoParser
from .sir_builder import SIRBuilder
from .equilibrium_resolver import EquilibriumResolver
from .realization_coordinator import RealizationCoordinator
from .codegen import generate as generate_code
from .conformance import run_conformance, write_report
from .conformance_sovereign import run_conformance as run_sovereign_conformance, write_report as write_sovereign_report
from .database import graph_hash
from .realization_ir import lower_graph
from .backends import BACKENDS, backend_for_language, backend_for_target
from . import backends as _backends_pkg
from .conformance_sovereign import check_file as _sovereign_check_file


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(argv)
    if args.version:
        print(f"orren {__version__}")
        return 0
    if not args.command:
        parser.print_help()
        return 1
    if args.command == "parse":
        return _cmd_parse(args)
    if args.command == "sir":
        return _cmd_sir(args)
    if args.command == "resolve":
        return _cmd_resolve(args)
    if args.command == "realize":
        return _cmd_realize(args)
    if args.command == "build":
        return _cmd_build(args)
    if args.command == "test":
        return _cmd_test(args)
    if args.command == "preview":
        return _cmd_preview(args)
    if args.command == "validate":
        return _cmd_validate(args)
    if args.command == "validate-suite":
        return _cmd_validate_suite(args)
    if args.command == "hash":
        return _cmd_hash(args)
    if args.command == "db" and getattr(args, "dbsub", None) == "init":
        return _cmd_db_init(args)
    if args.command == "db-init":
        return _cmd_db_init(args)
    if args.command == "snapshot":
        return _cmd_snapshot(args)
    if args.command == "diff":
        return _cmd_diff(args)
    if args.command == "restore":
        return _cmd_restore(args)
    if args.command == "gc":
        return _cmd_gc(args)
    parser.print_help()
    return 1


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="orren", description="Orren language CLI")
    p.add_argument("--version", action="store_true", help="print version and exit")
    sub = p.add_subparsers(dest="command")
    for cmd in ("parse", "sir", "resolve", "realize", "build", "validate", "hash"):
        sp = sub.add_parser(cmd, help=f"{cmd} a .orn file")
        sp.add_argument("file", help="path to .orn source file")
        if cmd in ("realize", "build"):
            sp.add_argument("--out", default="orren_out", help="output directory")
            sp.add_argument("--db", default=None, help="SQLite project database path")
            sp.add_argument("--ephemeral", action="store_true",
                            help="bypass the database entirely (ephemeral run)")
    sp_test = sub.add_parser("test", help="run conformance tests against an existing realization directory")
    sp_test.add_argument("out", help="realization directory containing manifest.json")
    sp_test.add_argument("--report", default=None, help="JSON report path (default: <out>/conformance.json)")
    sp_test.add_argument("--ephemeral", action="store_true",
                         help="bypass the database entirely (ephemeral run)")
    # --- Database lifecycle (durable semantic repository) ---
    sp_db = sub.add_parser("db", help="manage the SQLite semantic repository")
    sp_db.add_argument("dbsub", choices=("init",), help="db subcommand")
    sp_db.add_argument("--path", default=None, help="SQLite database path")
    sp_db.add_argument("--project", default="orren-project", help="project name")
    sp_db_init = sub.add_parser("db-init", aliases=("init-db",),
                                help="alias for 'db init'")
    sp_db_init.add_argument("--path", default=None, help="SQLite database path")
    sp_db_init.add_argument("--project", default="orren-project", help="project name")

    sp_snap = sub.add_parser("snapshot", help="emit a deterministic byte snapshot of a revision")
    sp_snap.add_argument("--path", required=True, help="SQLite database path")
    sp_snap.add_argument("--revision", default=None, help="revision id (default: working head)")
    sp_snap.add_argument("--out", default=None, help="output file path (default: stdout)")

    sp_diff = sub.add_parser("diff", help="compare two revisions of a project")
    sp_diff.add_argument("--path", required=True, help="SQLite database path")
    sp_diff.add_argument("revisions", nargs=2, metavar=("REVISION_A", "REVISION_B"))
    sp_diff.add_argument("--format", default="json", choices=("json", "text"),
                         help="output format (default: json)")

    sp_restore = sub.add_parser("restore", help="restore a revision as the working head (undo/redo)")
    sp_restore.add_argument("--path", required=True, help="SQLite database path")
    sp_restore.add_argument("revision", help="revision id to restore")

    sp_gc = sub.add_parser("gc", help="garbage-collect unreferenced rows from a project database")
    sp_gc.add_argument("--path", required=True, help="SQLite database path")
    sp_gc.add_argument("--dry-run", action="store_true", default=False,
                       help="report only; do not delete anything")

    sp_preview = sub.add_parser("preview", help="generate a self-contained HTML preview")
    sp_preview.add_argument("file", help="path to .orn source file")
    sp_preview.add_argument("--out", default=None, help="output HTML path (default: <name>.preview.html)")
    sub.add_parser("validate-suite", help="run the 48-test validation suite against the bundled examples")
    return p


def _read_source(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _cmd_parse(args) -> int:
    source = _read_source(args.file)
    parser = CoParser()
    exprs = parser.parse(source)
    print(f"Parsed {len(exprs)} expression(s):")
    for e in exprs:
        print(f"  - {e.name} : {e.type.value}")
        for ctx in e.context:
            print(f"      {ctx.key}: {ctx.value}")
        for kw, payload in e.raw_sections.items():
            print(f"      {kw}: {len(payload)} entries")
    # Report any parse-time errors detected.
    errors = parser.errors.sorted()
    if errors:
        print(f"\nParse errors ({len(errors)}):")
        for err in errors:
            cat = err.category.value
            print(f"  [{cat}] {err.code} line {err.line}: {err.message}")
    return 0


def _cmd_sir(args) -> int:
    source = _read_source(args.file)
    exprs = CoParser().parse(source)
    graph = SIRBuilder().build(exprs)
    print(f"SIR graph: {len(graph.nodes)} nodes")
    for node in graph.nodes:
        dims_with_content = [
            d.value for d in __import__("orren_engine").data_model.Dimension
            if node.has_dimension_content(d)
        ]
        print(f"  - {node.path} ({node.kind})")
        if dims_with_content:
            print(f"      dimensions: {', '.join(dims_with_content)}")
    print(f"Equilibrium rules: {len(graph.equilibrium_rules)}")
    print(f"Realization targets: {len(graph.realization_targets)}")
    return 0


def _cmd_resolve(args) -> int:
    source = _read_source(args.file)
    exprs = CoParser().parse(source)
    graph = SIRBuilder().build(exprs)
    report = EquilibriumResolver().resolve(graph)
    print(f"Outcomes: {len(report.outcomes)}")
    for o in report.outcomes:
        print(f"  - {o.rule_name} @ {o.node_path}")
        print(f"      preserve: {o.preserve}")
        if o.resolution_text:
            print(f"      resolution: {o.resolution_text}")
    print(f"Unresolved conflicts: {len(report.unresolved_conflicts)}")
    for c in report.unresolved_conflicts:
        print(f"  - {c}")
    return 0


def _cmd_realize(args) -> int:
    source = _read_source(args.file)
    # Provenance MUST hash the on-disk bytes verbatim (CRLF preserved) so the
    # recorded source_sha256 is the file the user actually committed.  The IR's
    # internal source_hash (see lower_graph) independently hashes the decoded
    # text used for lowering — both are honest, distinct provenance anchors.
    source_bytes = Path(args.file).read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    # Engine() always runs in ephemeral mode.  When --db is supplied we persist
    # the realization into a SQLiteRepo *after* generation — never via
    # Engine(db_path=...) which uses the incompatible ProjectDatabase schema.
    engine = Engine()
    result = engine.run(source)
    print(result.summary())
    os.makedirs(args.out, exist_ok=True)
    written_artifacts: List[Tuple[str, str, str]] = []
    for tgt in result.graph.realization_targets:
        files = generate_code(result.graph, tgt)
        tgt_dir = os.path.join(args.out, tgt.name)
        os.makedirs(tgt_dir, exist_ok=True)
        for fname, code in files.items():
            # `fname` is like "web_interface/index.html" — strip the prefix.
            short = fname.split("/", 1)[1] if "/" in fname else fname
            fpath = os.path.join(tgt_dir, short)
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(code)
            print(f"  wrote {fpath}")
            written_artifacts.append((tgt.name, short, fpath))
    # Write a manifest with artifact metadata and the backend-neutral IR.
    realization_ir = lower_graph(result.graph, source)
    manifest = {
        "version": __version__,
        "source_file": os.path.basename(args.file),
        "source_sha256": source_hash,
        "sir_sha256": graph_hash(result.graph),
        "realization_ir_sha256": realization_ir.content_hash(),
        "realization_ir": realization_ir.to_dict(),
        "provenance": {
            "compiler": "orren",
            "compiler_version": __version__,
            "source_sha256": source_hash,
            "sir_sha256": graph_hash(result.graph),
            "realization_ir_sha256": realization_ir.content_hash(),
        },
        "expressions": result.expressions_count,
        "sir_nodes": result.sir_node_count,
        "equilibrium_outcomes": result.equilibrium_outcomes,
        "unresolved_conflicts": result.unresolved_conflicts,
        "artifacts": [a.to_dict() for a in result.artifacts],
    }
    mpath = os.path.join(args.out, "manifest.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    print(f"  wrote {mpath}")
    _emit_preservation_proof(args.out, source_hash, result, realization_ir,
                              written_artifacts)
    if getattr(args, "db", None) and not getattr(args, "ephemeral", False):
        _persist_realization(args.db, source_bytes, source_hash, result,
                             realization_ir, written_artifacts)
    return 0


def _cmd_build(args) -> int:
    """Realize, then validate emitted artifacts with available toolchains."""
    realize_status = _cmd_realize(args)
    if realize_status != 0:
        return realize_status
    report = run_sovereign_conformance(args.out, run_adversarial=True)
    report_path = os.path.join(args.out, "conformance.json")
    write_sovereign_report(report, report_path)
    print(f"Build conformance: {report['passed']} passed, {report['degraded']} degraded, {report['failed']} failed, {report['skipped']} skipped")
    print(f"  report: {report_path}")
    return 0 if report["failed"] == 0 else 1


def _cmd_test(args) -> int:
    """Test an existing realization; never generates missing output."""
    report = run_sovereign_conformance(args.out, run_adversarial=True)
    report_path = args.report or os.path.join(args.out, "conformance.json")
    write_sovereign_report(report, report_path)
    print(f"Test conformance: {report['passed']} passed, {report['degraded']} degraded, {report['failed']} failed, {report['skipped']} skipped")
    print(f"  report: {report_path}")
    return 0 if report["failed"] == 0 else 1


def _cmd_preview(args) -> int:
    """Generate a self-contained HTML preview of the .orn source."""
    from .preview import write_preview
    source = _read_source(args.file)
    engine = Engine()
    result = engine.run(source)
    if result.graph is None or result.graph.root is None:
        print("ERROR: no SIR graph built", file=sys.stderr)
        return 1
    # Default output path: <basename>.preview.html next to the source.
    if args.out is None:
        base = os.path.splitext(os.path.basename(args.file))[0]
        out_path = os.path.join(os.path.dirname(os.path.abspath(args.file)),
                                f"{base}.preview.html")
    else:
        out_path = args.out
    write_preview(result.graph, out_path, artifacts=result.artifacts)
    print(f"Preview written to: {out_path}")
    print(f"  {len(result.graph.nodes)} entities, "
          f"{len(result.graph.equilibrium_rules)} equilibrium rules, "
          f"{len(result.artifacts)} realization targets")
    print(f"  Open in browser: file://{os.path.abspath(out_path)}")
    return 0


def _cmd_validate(args) -> int:
    """Run basic validation checks against the given file."""
    source = _read_source(args.file)
    engine = Engine()
    result = engine.run(source)
    # Basic checks mirroring 07_VALIDATION_v3.md:
    checks = []
    checks.append(("parsed_at_least_one_expression", result.expressions_count >= 1))
    checks.append(("sir_built_at_least_one_node", result.sir_node_count >= 1))
    checks.append(("all_nodes_have_9_dimensions",
                   all(n.all_dimensions_present() for n in result.graph.nodes)))
    checks.append(("realization_artifacts_present", len(result.artifacts) > 0))
    checks.append(("preservation_scores_in_range",
                   all(0.0 <= a.preservation_score <= 1.0 for a in result.artifacts)))
    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)
    print(f"Validation: {passed}/{total} checks passed")
    for name, ok in checks:
        marker = "PASS" if ok else "FAIL"
        print(f"  [{marker}] {name}")
    return 0 if passed == total else 1


def _cmd_validate_suite(args) -> int:
    """Run the canonical 48-test validation suite against the bundled
    7 example files. No FILE argument required — uses the examples/
    directory shipped with the package."""
    from .validate import run_all, print_report
    examples_dir = os.path.join(os.path.dirname(__file__), "..", "examples")
    examples_dir = os.path.abspath(examples_dir)
    if not os.path.isdir(examples_dir):
        print(f"ERROR: examples directory not found: {examples_dir}", file=sys.stderr)
        return 2
    p1, p2, all_passed = run_all(examples_dir, verbose=False)
    print_report(p1, p2)
    return 0 if all_passed else 1


def _cmd_hash(args) -> int:
    """Print a content hash of the SIR graph.

    Reproducibility contract: same source → same hash, every run.
    """
    source = _read_source(args.file)
    exprs = CoParser().parse(source)
    graph = SIRBuilder().build(exprs)
    sig = graph.signature()
    h = hashlib.sha256(sig.encode("utf-8")).hexdigest()
    print(h)
    return 0


# ---------------------------------------------------------------------------
# Preservation proof (Reference Backend — Rust service target)
# ---------------------------------------------------------------------------

# File-extension → language-name mapping.  The language name must match one of
# the keys registered in ``conformance_sovereign._VALIDATORS`` so that
# :func:`~orren_engine.conformance_sovereign.check_file` can dispatch to the
# correct per-language validator.
_EXT_TO_LANG: Dict[str, str] = {
    ".py": "python",
    ".rs": "rust",
    ".go": "go",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".hh": "cpp",
    ".ts": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".sass": "css",
    ".swift": "swift",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".tex": "latex",
    ".txt": "text",
    ".webaudio": "webaudio",
}


def _language_for_file(path: str) -> str:
    """Infer a conformance-language tag from a file path's extension.

    The returned value is a key understood by
    :func:`~orren_engine.conformance_sovereign.check_file` (i.e. one of the
    :data:`~orren_engine.conformance_sovereign._VALIDATORS` keys).

    Args:
        path: Filesystem path to a generated artifact.

    Returns:
        The canonical language name (e.g. ``"rust"``, ``"html"``), defaulting
        to ``"text"`` when the extension is unrecognised.
    """
    ext = Path(path).suffix.lower()
    return _EXT_TO_LANG.get(ext, "text")


def _detect_proxy(source_text: str) -> bool:
    """Return True when generated source is proxy-only (no real realisation).

    Fail-closed: a file that contains only ``// PROXY:`` or ``// DEGRADED:``
    markers and no executable realisation must never be reported as a success.

    Args:
        source_text: The generated source text to inspect.

    Returns:
        ``True`` when the source degrades to a proxy comment.
    """
    stripped = source_text.replace("//", " ").strip()
    has_proxy = "PROXY:" in source_text or "DEGRADED:" in source_text
    has_code = any(token for token in stripped.split() if token not in ("",))
    return has_proxy and not _has_executable_realisation(source_text)


def _has_executable_realisation(source_text: str) -> bool:
    """Heuristic: true when the source contains a real entry point or body.

    Args:
        source_text: Generated source text.

    Returns:
        ``True`` when an executable realisation signal is present.
    """
    # Rust: a main fn or pub fn process; Python: a callable def; TS: a function
    # or class declaration.  A proxy-only file has none of these.
    signals = ("fn main", "fn process", "pub fn", "def ", "def process",
               "function ", "export default", "class ", "fn ", "main()")
    return any(sig in source_text for sig in signals)


def _emit_preservation_proof(out_dir: str, source_hash: str, result: Any,
                             realization_ir: Any,
                             written_artifacts: List[Tuple[str, str, str]]) -> None:
    """Write ``preservation_proof.json`` consolidating provenance and toolchain
    evidence for each realization target.

    Honest-by-construction: a target is ``PASS`` only when its toolchain is
    available, the emitted artifact validates structurally, and no proxy-only
    realisation is detected.  Every other outcome is ``SKIP`` (no toolchain),
    ``DEGRADED`` (proxy/unsupported), or ``FAIL`` (actual check failure).

    Args:
        out_dir: Realisation output directory.
        source_hash: Verified SHA-256 of the on-disk source bytes.
        result: :class:`~orren_engine.engine.EngineResult`.
        realization_ir: Lowered :class:`RealizationIR`.
        written_artifacts: ``(target_name, short_path, abs_path)`` triples.
    """
    try:
        from .backends.manifest import manifest_for_language

        written_by_target: Dict[str, List[str]] = {}
        for tgt_name, _short, fpath in written_artifacts:
            written_by_target.setdefault(tgt_name, []).append(fpath)

        target_reports: List[Dict[str, Any]] = []
        reference_verified = False
        for tgt in result.graph.realization_targets:
            files = written_by_target.get(tgt.name, [])
            artifacts_report: List[Dict[str, Any]] = []
            any_pass = False
            proxy_detected = False
            for fpath in files:
                text = Path(fpath).read_text(encoding="utf-8", errors="replace")
                proxy = _detect_proxy(text)
                proxy_detected = proxy_detected or proxy
                status = "SKIP"
                evidence = "toolchain unavailable"
                try:
                    _cr = _sovereign_check_file(Path(fpath), _language_for_file(fpath))
                    status = _cr.status
                    evidence = _cr.detail
                except Exception as exc:  # pragma: no cover - defensive
                    status = "FAIL"
                    evidence = f"checker error: {exc}"
                if proxy:
                    # Fail-closed: a proxied target can never be PASS.
                    if status == "PASS":
                        status = "DEGRADED"
                        evidence = "proxied realisation; fail-closed downgrade"
                if status == "PASS":
                    any_pass = True
                artifacts_report.append({
                    "path": os.path.relpath(fpath, out_dir),
                    "status": status,
                    "evidence": evidence,
                    "proxy_only": proxy,
                })
            spec = backend_for_language(tgt.language)
            toolchain = spec.toolchains[0] if spec and spec.toolchains else None
            toolchain_available = bool(shutil.which(toolchain)) if toolchain else False
            manifest = manifest_for_language(tgt.language)
            preservation_score = (
                manifest.preservation_score if manifest is not None
                else (getattr(spec, "preservation_score", None) if spec else None)
            ) or 1.0
            if not toolchain_available:
                target_status = "SKIP"
            elif proxy_detected or not any_pass:
                target_status = "DEGRADED" if proxy_detected else "FAIL"
            else:
                target_status = "PASS"
            if target_status == "PASS" and toolchain_available:
                reference_verified = True
            target_reports.append({
                "name": tgt.name,
                "language": tgt.language,
                "preservation_score": preservation_score,
                "toolchain": toolchain,
                "toolchain_available": toolchain_available,
                "capabilities": (
                    manifest.supported_operations if manifest is not None
                    else (spec.capabilities if spec else [])
                ),
                "unsupported_cases": (
                    manifest.unsupported_cases if manifest is not None else []
                ),
                "status": target_status,
                "proxy_only": proxy_detected,
                "artifacts": artifacts_report,
            })
        proof = {
            "version": __version__,
            "source_sha256": source_hash,
            "sir_sha256": graph_hash(result.graph),
            "realization_ir_sha256": realization_ir.content_hash(),
            "fail_closed": True,
            "reference_backend_verified": reference_verified,
            "targets": target_reports,
        }
        ppath = os.path.join(out_dir, "preservation_proof.json")
        with open(ppath, "w", encoding="utf-8") as f:
            json.dump(proof, f, indent=2, sort_keys=True)
        print(f"  wrote {ppath}")
    except Exception as exc:  # pragma: no cover - proof is best-effort
        print(f"  preservation proof unavailable: {exc}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Database lifecycle commands
# ---------------------------------------------------------------------------


def _persist_realization(db_path: str, source_bytes: bytes, source_hash: str,
                         result: Any, realization_ir: Any,
                         written_artifacts: List[Tuple[str, str, str]]) -> None:
    """Persist a realization into a SQLite semantic repository.

    Creates the database file if it does not yet exist, begins a fresh revision,
    stores the source bytes, the SIR graph, and one artifact row per generated
    file.  This is the durable state boundary for a realization — the engine
    itself always runs ephemerally.

    Args:
        db_path: Filesystem path to the SQLite project database.
        source_bytes: Verbatim on-disk source bytes (for provenance).
        source_hash: SHA-256 of the source bytes.
        result: :class:`~orren_engine.engine.EngineResult` from the run.
        realization_ir: Lowered :class:`~orren_engine.realization_ir.RealizationIR`.
        written_artifacts: ``(target_name, short_path, abs_path)`` triples for
            every file written to the output directory.
    """
    from .storage import SQLiteRepo

    if not os.path.exists(db_path):
        SQLiteRepo.init(db_path, "orren-project")
    repo = SQLiteRepo(db_path, "orren-project")
    try:
        sir_hash = graph_hash(result.graph)
        revision_id = repo.begin_revision(
            parent_id=repo.latest_revision, source_hash=source_hash,
            sir_hash=sir_hash, compiler_version=__version__)
        repo.put_source(repo.project_id, "source.orn", source_bytes, source_hash)
        repo.put_sir_graph(revision_id, result.graph)
        # Record generated artifacts (one row per file written to --out).
        for tgt_name, _short, fpath in written_artifacts:
            tgt_lang = ""
            for tgt in result.graph.realization_targets:
                if tgt.name == tgt_name:
                    tgt_lang = tgt.language
                    break
            target_id = repo.compute_target_id(revision_id, tgt_name, tgt_lang or "text")
            file_bytes = Path(fpath).read_bytes()
            file_hash = hashlib.sha256(file_bytes).hexdigest()
            storage_uri = f"file://{os.path.abspath(fpath)}"
            repo.store_artifact(revision_id, target_id, _short, tgt_lang or "text",
                                file_hash, storage_uri)
        print(f"  persisted revision {revision_id} to {db_path}")
    finally:
        repo.close()


def _open_or_init_repo(args) -> Any:
    """Open a :class:`SQLiteRepo`, initialising the file if absent.

    Args:
        args: Parsed CLI namespace with a ``path`` attribute.

    Returns:
        An open :class:`~orren_engine.storage.SQLiteRepo`.
    """
    from .storage import SQLiteRepo

    path = getattr(args, "path", None) or os.path.join(os.getcwd(), "orren.db")
    project = getattr(args, "project", None) or "orren-project"
    if not os.path.exists(path):
        SQLiteRepo.init(path, project)
    return SQLiteRepo(path, project)


def _cmd_db_init(args) -> int:
    """Initialise a new SQLite semantic repository."""
    from .storage import SQLiteRepo, SCHEMA_VERSION

    path = args.path or os.path.join(os.getcwd(), "orren.db")
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"ERROR: database already exists: {path}", file=sys.stderr)
        print("  Use 'orren db' against the existing file, or remove it first.",
              file=sys.stderr)
        return 1
    project_id = SQLiteRepo.init(path, args.project)
    print(f"Initialized semantic repository: {path}")
    print(f"  project_id: {project_id}")
    print(f"  schema_version: {SCHEMA_VERSION}")
    print("  journal_mode: WAL  foreign_keys: ON")
    return 0


def _cmd_snapshot(args) -> int:
    """Emit a deterministic byte snapshot of a revision."""
    repo = _open_or_init_repo(args)
    try:
        revision_id = args.revision or repo.latest_revision
        if not revision_id:
            print("ERROR: no --revision given and no working head exists",
                  file=sys.stderr)
            return 1
        data = repo.snapshot(revision_id)
        if args.out:
            with open(args.out, "wb") as f:
                f.write(data)
            print(f"  wrote {args.out} ({len(data)} bytes)")
        else:
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.write(b"\n")
        print(f"snapshot: {revision_id} ({len(data)} bytes)")
    finally:
        repo.close()
    return 0


def _diff_revisions(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, List[Any]]:
    """Compute a semantic diff between two revision snapshot documents.

    Args:
        a: Snapshot document A (revision A).
        b: Snapshot document B (revision B).

    Returns:
        A dict with ``added``/``removed``/``changed`` lists of change records.
    """
    paths_a = {n["path"]: n for n in a.get("nodes", [])}
    paths_b = {n["path"]: n for n in b.get("nodes", [])}
    added = [p for p in paths_b if p not in paths_a]
    removed = [p for p in paths_a if p not in paths_b]
    changed = [
        {"path": p, "before": paths_a[p], "after": paths_b[p]}
        for p in paths_a
        if p in paths_b and paths_a[p] != paths_b[p]
    ]
    return {"added": sorted(added), "removed": sorted(removed), "changed": changed}


def _cmd_diff(args) -> int:
    """Compare two revisions of a project."""
    import json as _json

    path = args.path
    a_id, b_id = args.revisions
    from .storage import SQLiteRepo

    repo = SQLiteRepo(path, "orren-project")
    try:
        try:
            a = _json.loads(repo.snapshot(a_id).decode("utf-8"))
        except KeyError:
            print(f"ERROR: revision not found: {a_id}", file=sys.stderr)
            return 1
        try:
            b = _json.loads(repo.snapshot(b_id).decode("utf-8"))
        except KeyError:
            print(f"ERROR: revision not found: {b_id}", file=sys.stderr)
            return 1
        diff = _diff_revisions(a, b)
        if args.format == "json":
            print(_json.dumps(diff, indent=2, sort_keys=True))
        else:
            print(f"Revision diff: {a_id} -> {b_id}")
            print(f"  added nodes: {len(diff['added'])}")
            print(f"  removed nodes: {len(diff['removed'])}")
            print(f"  changed nodes: {len(diff['changed'])}")
    finally:
        repo.close()
    return 0


def _cmd_restore(args) -> int:
    """Restore a revision as the durable working head."""
    from .storage import SQLiteRepo

    repo = SQLiteRepo(args.path, "orren-project")
    try:
        repo.restore(repo.project_id, args.revision)
        print(f"Restored working head to {args.revision}")
    except KeyError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        repo.close()
    return 0


def _cmd_gc(args) -> int:
    """Garbage-collect unreferenced rows from a project database."""
    from .storage import SQLiteRepo

    repo = SQLiteRepo(args.path, "orren-project")
    try:
        summary = repo.gc(dry_run=getattr(args, "dry_run", False))
        label = "DRY RUN" if getattr(args, "dry_run", False) else "done"
        print(f"Garbage collection ({label}):")
        for key, value in summary.items():
            print(f"  {key}: {value}")
    finally:
        repo.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
