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
import sys
from typing import List, Optional

from . import __version__
from .engine import Engine
from .parser import CoParser
from .sir_builder import SIRBuilder
from .equilibrium_resolver import EquilibriumResolver
from .realization_coordinator import RealizationCoordinator
from .codegen import generate as generate_code


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
    if args.command == "preview":
        return _cmd_preview(args)
    if args.command == "validate":
        return _cmd_validate(args)
    if args.command == "validate-suite":
        return _cmd_validate_suite(args)
    if args.command == "hash":
        return _cmd_hash(args)
    parser.print_help()
    return 1


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="orren", description="Orren language CLI")
    p.add_argument("--version", action="store_true", help="print version and exit")
    sub = p.add_subparsers(dest="command")
    for cmd in ("parse", "sir", "resolve", "realize", "validate", "hash"):
        sp = sub.add_parser(cmd, help=f"{cmd} a .orn file")
        sp.add_argument("file", help="path to .orn source file")
        if cmd == "realize":
            sp.add_argument("--out", default="orren_out", help="output directory")
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
    exprs = CoParser().parse(source)
    print(f"Parsed {len(exprs)} expression(s):")
    for e in exprs:
        print(f"  - {e.name} : {e.type.value}")
        for ctx in e.context:
            print(f"      {ctx.key}: {ctx.value}")
        for kw, payload in e.raw_sections.items():
            print(f"      {kw}: {len(payload)} entries")
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
    engine = Engine()
    result = engine.run(source)
    print(result.summary())
    os.makedirs(args.out, exist_ok=True)
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
    # Write a manifest with all artifact metadata.
    manifest = {
        "version": __version__,
        "source_file": os.path.abspath(args.file),
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
    return 0


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


if __name__ == "__main__":
    sys.exit(main())
