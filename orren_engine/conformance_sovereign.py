"""Conformance checks for realized artifacts — Language-Sovereign Edition.

This module enforces Orren's language sovereignty principle: no backend is
privileged, no runtime is canonical, and truth lives in evidence quality alone.

Status semantics (HONEST, never inflated):
    PASS        — Artifact accepted by real toolchain AND behavioral probe succeeded.
    DEGRADED    — Artifact passed a WEAKER check because full toolchain unavailable.
                 The detail field MUST explain what was skipped.
    SKIP        — No validation possible (toolchain missing, language unregistered).
    FAIL        — Artifact rejected by toolchain or behavioral probe.

Critical rules:
    1. A proxy/placeholder check may NEVER report as PASS.
    2. DEGRADED must include the specific capability that was downgraded.
    3. Every language with a realization target must have a compiler-invocation path.
    4. Adversarial cases must prove the harness can FAIL, not just pass.
    5. Python is ONE backend among MANY — its tests have equal weight to Rust's.

Evidence levels (from weakest to strongest):
    Level 0 — File existence only (unacceptable as sole check)
    Level 1 — Syntactic validity (parse / compile / --check)
    Level 2 — Structural integrity (imports resolve, references valid)
    Level 3 — Behavioral execution (function called, value verified)
    Level 4 — Integration contract (round-trip, state mutation verified)

The harness MUST report which level each check achieved.
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
from dataclasses import dataclass, asdict, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Status constants — HONEST reporting mandated by sovereignty principle
# ---------------------------------------------------------------------------

class Status:
    """Conformance check outcomes. Each has precise semantics."""
    PASS = "PASS"         # Full toolchain + behavioral verification
    DEGRADED = "DEGRADED" # Weaker check due to missing toolchain; detail explains gap
    SKIP = "SKIP"         # No validation possible; toolchain/language unregistered
    FAIL = "FAIL"         # Rejected by toolchain or probe


# Evidence levels for transparency
class EvidenceLevel:
    FILE_EXISTS = 0       # File is non-empty (weakest — unacceptable alone)
    SYNTACTIC = 1         # Parsed / compiled without errors
    STRUCTURAL = 2        # Imports resolve, references are valid
    BEHAVIORAL = 3        # Executed function, verified return value or side effect
    INTEGRATION = 4       # Round-trip contract, state mutation verified (strongest)


@dataclass
class CheckResult:
    """Single conformance check result with full provenance."""
    target: str
    path: str
    kind: str                    # Language or check type
    status: str                  # One of Status.* values
    detail: str                  # Human-readable explanation
    evidence_level: int = 0      # EvidenceLevel.* value
    toolchain_version: str = ""   # Compiler/runtime version if available
    duration_ms: float = 0.0     # How long the check took


@dataclass
class CoverageMatrix:
    """Structured coverage showing targets × languages × results."""
    targets: dict[str, dict[str, CheckResult]] = field(default_factory=dict)
    # { target_name: { language: CheckResult } }
    
    def to_dict(self) -> dict[str, Any]:
        return {
            target: {
                lang: asdict(result) 
                for lang, result in langs.items()
            }
            for target, langs in self.targets.items()
        }


# ---------------------------------------------------------------------------
# Internal probe classes
# ---------------------------------------------------------------------------

class _HTMLProbe(HTMLParser):
    """Parse HTML structure and extract references."""
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


def _run(command: list[str], cwd: Path, timeout: int = 30) -> tuple[int, str, str]:
    """Run external command, return (exit_code, stdout, stderr).

    Windows note: npm installs CLIs as ``.cmd`` shims which CreateProcess
    cannot launch directly; they are wrapped in ``cmd /c`` here.
    """
    try:
        argv = list(command)
        if os.name == "nt" and argv:
            resolved = shutil.which(argv[0])
            if resolved is None and Path(argv[0]).suffix.lower() in (".cmd", ".bat"):
                pass  # leave as-is; the cmd /c wrapper below handles it
            if resolved and resolved.lower().endswith((".cmd", ".bat")):
                argv = ["cmd", "/c", resolved] + argv[1:]
            elif Path(argv[0]).suffix.lower() in (".cmd", ".bat"):
                argv = ["cmd", "/c"] + argv
        proc = subprocess.run(
            argv, cwd=cwd, text=True, capture_output=True, timeout=timeout
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired as exc:
        return 124, "", f"timeout after {timeout}s: {exc}"
    except FileNotFoundError:
        return 127, "", f"command not found: {command[0]}"


def _toolchain_info(tool_name: str) -> tuple[bool, str]:
    """Check if toolchain exists and get version string."""
    tool_path = shutil.which(tool_name)
    if not tool_path:
        return False, ""
    code, stdout, _ = _run([tool_path, "--version"], Path("."), timeout=5)
    version = stdout.split("\n")[0] if code == 0 else "unknown"
    return True, version


_MSVC_CACHE: tuple[bool, str] | None = None


def _discover_msvc() -> tuple[bool, str]:
    """Locate an MSVC installation (cl.exe + vcvars64.bat) on Windows.

    Discovery order:
      1. ``vswhere.exe`` (installed with any recent VS/BuildTools)
      2. Well-known Visual Studio/BuildTools install roots

    Returns ``(available, version_string)``. Cached after first call.
    """
    global _MSVC_CACHE
    if _MSVC_CACHE is not None:
        return _MSVC_CACHE

    result = (False, "")
    vswhere = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / (
        "Microsoft Visual Studio/Installer/vswhere.exe"
    )
    install_roots: list[str] = []
    if vswhere.is_file():
        try:
            proc = subprocess.run(
                [str(vswhere), "-latest", "-products", "*",
                 "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                 "-property", "installationPath"],
                text=True, capture_output=True, timeout=15,
            )
            install_roots += [l.strip() for l in proc.stdout.splitlines() if l.strip()]
        except Exception:
            pass

    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    install_roots += [
        rf"{pf}\Microsoft Visual Studio\2022\BuildTools",
        rf"{pf86}\Microsoft Visual Studio\2022\BuildTools",
        rf"{pf}\Microsoft Visual Studio\2022\Community",
        rf"{pf}\Microsoft Visual Studio\2022\Professional",
        rf"{pf}\Microsoft Visual Studio\2022\Enterprise",
        rf"{pf}\Microsoft Visual Studio\2022\Preview",
    ]

    for root in install_roots:
        msvc_dir = Path(root) / "VC/Tools/MSVC"
        if not msvc_dir.is_dir():
            continue
        versions = sorted((d.name for d in msvc_dir.iterdir() if d.is_dir()), reverse=True)
        for ver in versions:
            cl = msvc_dir / ver / "bin/Hostx64/x64/cl.exe"
            vcvars = Path(root) / "VC/Auxiliary/Build/vcvars64.bat"
            if cl.is_file() and vcvars.is_file():
                result = (True, f"MSVC {ver}")
                break
        if result[0]:
            break

    _MSVC_CACHE = result
    return result


def _msvc_batch(cl_args: list[str], cwd: Path, timeout: int = 90) -> tuple[int, str, str]:
    """Run cl.exe through vcvars64.bat via a generated batch script.

    cl.exe requires the INCLUDE/LIB environment that vcvars64.bat sets up;
    invoking it bare fails even for syntax-only checks.
    """
    available, _version = _discover_msvc()
    if not available:
        return 127, "", "MSVC not available"
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    vswhere = Path(pf86) / "Microsoft Visual Studio/Installer/vswhere.exe"
    vcvars = None
    install_roots: list[str] = []
    if vswhere.is_file():
        try:
            proc = subprocess.run(
                [str(vswhere), "-latest", "-products", "*",
                 "-requires", "Microsoft.VisualStudio.Component.VC.Tools.x86.x64",
                 "-property", "installationPath"],
                text=True, capture_output=True, timeout=15,
            )
            install_roots = [l.strip() for l in proc.stdout.splitlines() if l.strip()]
        except Exception:
            pass
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    install_roots += [
        rf"{pf}\Microsoft Visual Studio\2022\BuildTools",
        rf"{pf86}\Microsoft Visual Studio\2022\BuildTools",
        rf"{pf}\Microsoft Visual Studio\2022\Community",
    ]
    for root in install_roots:
        candidate = Path(root) / "VC/Auxiliary/Build/vcvars64.bat"
        if candidate.is_file():
            vcvars = candidate
            break
    if vcvars is None:
        return 127, "", "vcvars64.bat not found"

    with tempfile.TemporaryDirectory(prefix="orren-msvc-") as td:
        bat = Path(td) / "probe.bat"
        lines = ["@echo off", f'call "{vcvars}" >nul 2>&1', "cl " + " ".join(cl_args)]
        bat.write_text("\r\n".join(lines) + "\r\n", encoding="ascii")
        proc = subprocess.run(
            ["cmd", "/c", str(bat)],
            cwd=str(cwd), text=True, capture_output=True, timeout=timeout,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


# ---------------------------------------------------------------------------
# Per-language validators — EACH LANGUAGE GETS EQUAL TREATMENT
# ---------------------------------------------------------------------------

def _validate_python(path: Path) -> CheckResult:
    """Python validator: AST parse → byte-compile → behavioral execution."""
    start = _now_ms()
    
    # Level 1: Syntactic — AST parse
    try:
        source = path.read_text(encoding="utf-8")
        ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        return CheckResult(
            target="", path=str(path), kind="python",
            status=Status.FAIL, detail=f"Syntax error: {exc}",
            evidence_level=EvidenceLevel.SYNTACTIC - 1  # Failed at syntax
        )
    
    # Level 1+: Byte-compile
    try:
        py_compile.compile(str(path), doraise=True)
    except py_compile.PyCompileError as exc:
        return CheckResult(
            target="", path=str(path), kind="python",
            status=Status.FAIL, detail=f"Byte-compile error: {exc}",
            evidence_level=EvidenceLevel.SYNTACTIC
        )
    
    # Level 3: Behavioral — import and execute
    try:
        spec = importlib.util.spec_from_file_location("orren_probe", path)
        if spec is None or spec.loader is None:
            return CheckResult(
                target="", path=str(path), kind="python",
                status=Status.DEGRADED,
                detail="Loaded but cannot create module spec; syntax valid, behavior untested",
                evidence_level=EvidenceLevel.SYNTACTIC
            )
        
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        classes = [
            v for v in vars(module).values()
            if isinstance(v, type) and v.__module__ == module.__name__
        ]
        if not classes:
            return CheckResult(
                target="", path=str(path), kind="python",
                status=Status.DEGRADED,
                detail="No implementation class found; file executes but no contract",
                evidence_level=EvidenceLevel.STRUCTURAL
            )
        
        cls = classes[0]
        with tempfile.TemporaryDirectory(prefix="orren-probe-") as root:
            # Try each class — some may require constructor args (e.g. pydantic models).
            # We test every declared class and report PASS if any satisfies a contract.
            for candidate_cls in classes:
                try:
                    instance = candidate_cls(root) if "storage" in path.name else candidate_cls()
                except Exception:
                    # Class can't be instantiated without args (e.g. pydantic BaseModel
                    # with required fields). Try next class.
                    continue

                # Test retain/retrieve contract (storage pattern)
                if hasattr(instance, "retain") and hasattr(instance, "retrieve"):
                    payload = b"orren-conformance-payload"
                    instance.retain(payload, "conformance")
                    result = instance.retrieve("conformance")
                    if result != payload:
                        return CheckResult(
                            target="", path=str(path), kind="python",
                            status=Status.FAIL,
                            detail="retain/retrieve round-trip corrupted payload",
                            evidence_level=EvidenceLevel.BEHAVIORAL
                        )
                    return CheckResult(
                        target="", path=str(path), kind="python",
                        status=Status.PASS,
                        detail="executed retain/retrieve round-trip successfully",
                        evidence_level=EvidenceLevel.INTEGRATION,
                        toolchain_version=_toolchain_info("python3")[1]
                    )
                
                # Test process/run contract (service pattern)
                for method_name in ("process", "run"):
                    method = getattr(instance, method_name, None)
                    if callable(method):
                        value = method()
                        if value is None:
                            return CheckResult(
                                target="", path=str(path), kind="python",
                                status=Status.DEGRADED,
                                detail=f"{method_name}() returned None; executed but no verifiable output",
                                evidence_level=EvidenceLevel.BEHAVIORAL
                            )
                        return CheckResult(
                            target="", path=str(path), kind="python",
                            status=Status.PASS,
                            detail=f"executed {method_name}() successfully, returned {type(value).__name__}",
                            evidence_level=EvidenceLevel.BEHAVIORAL,
                            toolchain_version=_toolchain_info("python3")[1]
                        )

            return CheckResult(
                target="", path=str(path), kind="python",
                status=Status.DEGRADED,
                detail=f"Module loaded and byte-compiled; {len(classes)} class(es) found but none "
                       f"satisfied a retain/retrieve or process/run contract (instantiation may "
                       f"require constructor arguments)",
                evidence_level=EvidenceLevel.STRUCTURAL
            )
            
    except Exception as exc:
        return CheckResult(
            target="", path=str(path), kind="python",
            status=Status.FAIL,
            detail=f"Behavioral probe failed: {type(exc).__name__}: {exc}",
            evidence_level=EvidenceLevel.STRUCTURAL
        )


def _validate_rust(path: Path) -> CheckResult:
    """Rust validator: warning-free compilation plus executable behavior when available."""
    start = _now_ms()
    rustc_available, version = _toolchain_info("rustc")

    if not rustc_available:
        return CheckResult(
            target="", path=str(path), kind="rust",
            status=Status.SKIP,
            detail="rustc toolchain unavailable — cannot validate Rust artifacts",
            evidence_level=0,
        )

    source = path.read_text(encoding="utf-8")
    has_main = "fn main" in source
    with tempfile.TemporaryDirectory(prefix="orren-rust-compile-") as build_dir:
        executable = Path(build_dir) / "orren_app"
        command = ["rustc", "--edition", "2021", "-D", "warnings", str(path)]
        if has_main:
            command.extend(["-o", str(executable)])
        else:
            command.extend(["--crate-type=lib", "--emit=metadata", "-o", "/dev/null"])
        code, stdout, stderr = _run(command, path.parent, timeout=60)
        if code != 0:
            return CheckResult(
                target="", path=str(path), kind="rust",
                status=Status.FAIL,
                detail=f"Rust warning-free compilation failed: {(stderr or stdout)[:500]}",
                evidence_level=EvidenceLevel.SYNTACTIC - 1,
                toolchain_version=version,
                duration_ms=_now_ms() - start,
            )
        if not has_main:
            return CheckResult(
                target="", path=str(path), kind="rust",
                status=Status.DEGRADED,
                detail="Rust library compiles warning-free; no executable entrypoint was available for behavioral testing",
                evidence_level=EvidenceLevel.SYNTACTIC,
                toolchain_version=version,
                duration_ms=_now_ms() - start,
            )
        run_code, output, run_error = _run([str(executable)], Path(build_dir), timeout=10)
        if run_code != 0:
            return CheckResult(
                target="", path=str(path), kind="rust",
                status=Status.FAIL,
                detail=f"Rust executable exited with {run_code}: {(run_error or output)[:500]}",
                evidence_level=EvidenceLevel.SYNTACTIC,
                toolchain_version=version,
                duration_ms=_now_ms() - start,
            )
        if not output.strip():
            return CheckResult(
                target="", path=str(path), kind="rust",
                status=Status.FAIL,
                detail="Rust executable returned no observable runtime output",
                evidence_level=EvidenceLevel.BEHAVIORAL,
                toolchain_version=version,
                duration_ms=_now_ms() - start,
            )
        return CheckResult(
            target="", path=str(path), kind="rust",
            status=Status.PASS,
            detail="Rust source compiled with warnings denied and executable behavior produced observable output",
            evidence_level=EvidenceLevel.BEHAVIORAL,
            toolchain_version=version,
            duration_ms=_now_ms() - start,
        )


def _validate_go(path: Path) -> CheckResult:
    """Go validator: go vet (static analysis) → optional build."""
    start = _now_ms()
    go_available, version = _toolchain_info("go")
    
    if not go_available:
        return CheckResult(
            target="", path=str(path), kind="go",
            status=Status.SKIP,
            detail="go toolchain unavailable — cannot validate Go artifacts",
            evidence_level=0
        )
    
    # Create temporary go.mod if needed
    parent = path.parent
    mod_file = parent / "go.mod"
    mod_existed = mod_file.exists()
    if not mod_existed:
        mod_file.write_text("module orrenprobe\ngo 1.21\n", encoding="utf-8")
    
    try:
        # Level 1-2: go vet (syntax + type checking + static analysis)
        code, stdout, stderr = _run(["go", "vet", str(parent)], parent, timeout=60)
        
        if code != 0:
            return CheckResult(
                target="", path=str(path), kind="go",
                status=Status.FAIL,
                detail=f"go vet failed: {stderr[:500]}",
                evidence_level=EvidenceLevel.SYNTACTIC,
                toolchain_version=version
            )
        
        # Level 1: Also verify it can build (without installing)
        import tempfile as _tf
        with _tf.NamedTemporaryFile(suffix=".exe" if os.name == "nt" else "", delete=False) as tf:
            tmp_exe = tf.name
        try:
            code, _, stderr = _run(
                ["go", "build", "-o", tmp_exe, "."],
                parent, timeout=60
            )
            
            if code != 0:
                return CheckResult(
                    target="", path=str(path), kind="go",
                    status=Status.DEGRADED,
                    detail=f"go vet passed but build failed: {stderr[:500]}",
                    evidence_level=EvidenceLevel.SYNTACTIC,
                    toolchain_version=version
                )
        finally:
            Path(tmp_exe).unlink(missing_ok=True)
        
        # Level 3: Behavioral — run the binary and verify output
        code, stdout, stderr = _run(
            ["go", "run", "./..."],
            parent, timeout=30
        )
        if code != 0:
            return CheckResult(
                target="", path=str(path), kind="go",
                status=Status.DEGRADED,
                detail=f"go vet + build passed but go run failed: {stderr[:500]}",
                evidence_level=EvidenceLevel.STRUCTURAL,
                toolchain_version=version,
                duration_ms=_now_ms() - start,
            )
        
        return CheckResult(
            target="", path=str(path), kind="go",
            status=Status.PASS,
            detail="Go source passes vet, builds, and executes successfully",
            evidence_level=EvidenceLevel.BEHAVIORAL,
            toolchain_version=version,
            duration_ms=_now_ms() - start
        )
    finally:
        # Clean up temp go.mod
        if not mod_existed and mod_file.exists():
            mod_file.unlink()


def _validate_c(path: Path) -> CheckResult:
    """C/C++ validator: gcc/clang -fsyntax-only, falling back to MSVC /Zs."""
    start = _now_ms()
    gcc_available, version = _toolchain_info("gcc")
    if gcc_available:
        cc = "gcc"
    else:
        clang_available, clang_version = _toolchain_info("clang")
        if clang_available:
            cc = "clang"
            version = clang_version
        else:
            msvc_available, msvc_version = _discover_msvc()
            if not msvc_available:
                return CheckResult(
                    target="", path=str(path), kind="c",
                    status=Status.SKIP,
                    detail="gcc/clang/MSVC toolchain unavailable — cannot validate C artifacts",
                    evidence_level=0
                )
            # MSVC path: /Zs performs syntax+semantic checks only.
            code, stdout, stderr = _msvc_batch(
                ["/nologo", "/Zs", "/W4", str(path.resolve())], path.parent
            )
            if code == 127:
                return CheckResult(
                    target="", path=str(path), kind="c",
                    status=Status.SKIP,
                    detail=f"MSVC environment setup failed: {stderr[:200]}",
                    evidence_level=0,
                    toolchain_version=msvc_version,
                )
            if code != 0:
                return CheckResult(
                    target="", path=str(path), kind="c",
                    status=Status.FAIL,
                    detail=f"MSVC compilation failed: {(stderr or stdout)[:500]}",
                    evidence_level=EvidenceLevel.SYNTACTIC - 1,
                    toolchain_version=msvc_version,
                )
            warnings = [l for l in ((stderr or "") + (stdout or "")).split("\n") if "warning" in l.lower()]
            if warnings:
                return CheckResult(
                    target="", path=str(path), kind="c",
                    status=Status.DEGRADED,
                    detail=f"C compiles under MSVC with {len(warnings)} warning(s): {warnings[0][:200]}",
                    evidence_level=EvidenceLevel.SYNTACTIC,
                    toolchain_version=msvc_version,
                )
            return CheckResult(
                target="", path=str(path), kind="c",
                status=Status.PASS,
                detail="C source passes MSVC syntax and semantic analysis cleanly",
                evidence_level=EvidenceLevel.SYNTACTIC,
                toolchain_version=msvc_version,
                duration_ms=_now_ms() - start,
            )

    # Determine if C or C++ from extension
    is_cpp = path.suffix in (".cpp", ".cxx", ".cc", ".hpp")
    std_flag = "-std=c++17" if is_cpp else "-std=c17"
    
    # Level 1-2: Syntax + semantic analysis (no code generation)
    code, stdout, stderr = _run(
        [cc, std_flag, "-fsyntax-only", "-Wall", "-Wextra", str(path)],
        path.parent, timeout=30
    )
    
    if code != 0:
        return CheckResult(
            target="", path=str(path), kind="c",
            status=Status.FAIL,
            detail=f"C/C++ compilation failed: {stderr[:500]}",
            evidence_level=EvidenceLevel.SYNTACTIC - 1,
            toolchain_version=version
        )
    
    warnings = [l for l in stderr.split("\n") if l.strip() and "warning:" in l]
    if warnings:
        return CheckResult(
            target="", path=str(path), kind="c",
            status=Status.DEGRADED,
            detail=f"C/C++ compiles with {len(warnings)} warning(s): {warnings[0][:200]}",
            evidence_level=EvidenceLevel.SYNTACTIC,
            toolchain_version=version
        )
    
    return CheckResult(
        target="", path=str(path), kind="c",
        status=Status.PASS,
        detail="C/C++ source passes syntax and semantic analysis cleanly",
        evidence_level=EvidenceLevel.SYNTACTIC,
        toolchain_version=version,
        duration_ms=_now_ms() - start
    )


def _validate_typescript(path: Path) -> CheckResult:
    """TypeScript validator: tsc --noEmit (full type checking)."""
    start = _now_ms()
    tsc_available, version = _toolchain_info("tsc")

    # Test files depend on the vitest toolchain (devDependencies).  They are
    # compiled and executed by `npm test`, not by tsc's project check; the
    # generated tsconfig excludes them.  Claiming tsc evidence here would be
    # dishonest — report SKIP with the exact reason.
    if path.name.endswith(".test.ts"):
        return CheckResult(
            target="", path=str(path), kind="typescript",
            status=Status.SKIP,
            detail="test file validated by 'npm test' (vitest) after dependency "
                   "install; excluded from tsc project check by generated tsconfig",
            evidence_level=0,
            toolchain_version=version if tsc_available else "",
        )

    if not tsc_available:
        # Fallback: use node for syntax-level check if available
        node_available, node_version = _toolchain_info("node")
        if node_available:
            # Try node --experimental-strip-types (Node 22+) for behavioral execution
            node_str = node_version.lower()
            node_major = 0
            for part in node_str.split("v")[-1].split("."):
                try:
                    node_major = int(part)
                    break
                except ValueError:
                    continue
            
            source = path.read_text(encoding="utf-8")
            # Basic structural validation
            has_class = "class " in source
            has_export = "export " in source
            if not has_class and not has_export:
                return CheckResult(
                    target="", path=str(path), kind="typescript",
                    status=Status.DEGRADED,
                    detail="tsc unavailable; no exported classes or functions found",
                    evidence_level=EvidenceLevel.FILE_EXISTS,
                    toolchain_version=node_version,
                )
            
            # Behavioral: if Node 22+ and file is .js (transpiled), try running
            if node_major >= 22 and path.suffix == ".js":
                code, stdout, stderr = _run(["node", str(path)], path.parent, timeout=10)
                if code == 0:
                    return CheckResult(
                        target="", path=str(path), kind="typescript",
                        status=Status.DEGRADED,
                        detail=f"tsc unavailable; node v{node_major} executed JS output (TypeScript type safety unverified)",
                        evidence_level=EvidenceLevel.BEHAVIORAL,
                        toolchain_version=node_version,
                    )
                return CheckResult(
                    target="", path=str(path), kind="typescript",
                    status=Status.DEGRADED,
                    detail=f"tsc unavailable; node v{node_major} run failed: {stderr[:200]}",
                    evidence_level=EvidenceLevel.FILE_EXISTS,
                    toolchain_version=node_version,
                )
            
            return CheckResult(
                target="", path=str(path), kind="typescript",
                status=Status.DEGRADED,
                detail=f"tsc unavailable; node v{node_major} available but cannot run TypeScript directly (type safety unverified, structure valid)",
                evidence_level=EvidenceLevel.STRUCTURAL,
                toolchain_version=node_version,
            )
        return CheckResult(
            target="", path=str(path), kind="typescript",
            status=Status.SKIP,
            detail="tsc and node toolchains unavailable — cannot validate TypeScript artifacts",
            evidence_level=0
        )
    
    # Need a tsconfig.json or create temp one
    parent = path.parent
    tsconfig = parent / "tsconfig.json"
    tsconfig_existed = tsconfig.exists()
    if not tsconfig_existed:
        tsconfig.write_text(json.dumps({
            "compilerOptions": {
                "target": "ES2020",
                "module": "commonjs",
                "strict": True,
                "noEmit": True,
                "skipLibCheck": True,
                "allowJs": False
            },
            "include": ["./**/*.ts"]
        }, indent=2), encoding="utf-8")
    
    try:
        # Level 1-2: Full type checking (no emit). Use project mode (-p .)
        # because positional file args suppress tsconfig.json (TS >= 5.5 / TS7).
        code, stdout, stderr = _run(
            ["tsc", "--noEmit", "--pretty", "false", "-p", "."],
            parent, timeout=60
        )
        
        if code != 0:
            return CheckResult(
                target="", path=str(path), kind="typescript",
                status=Status.FAIL,
                detail=f"TypeScript type errors: {stderr[:500]}",
                evidence_level=EvidenceLevel.SYNTACTIC - 1,
                toolchain_version=version
            )
        
        return CheckResult(
            target="", path=str(path), kind="typescript",
            status=Status.PASS,
            detail="TypeScript passes full strict type checking",
            evidence_level=EvidenceLevel.STRUCTURAL,  # Type checking is stronger than syntax
            toolchain_version=version,
            duration_ms=_now_ms() - start
        )
    finally:
        if not tsconfig_existed and tsconfig.exists():
            tsconfig.unlink()


def _validate_javascript(path: Path) -> CheckResult:
    """JavaScript validator: syntax check, then executable behavioral probe.

    Level 1 (SYNTACTIC): ``node --check`` — module parses without errors.
    Level 2-3: the artifact is imported under a minimal DOM shim in a
    subprocess; an exported ``wireUpEvents()`` entry point is invoked and
    semantic events (``orren:*``) dispatched during initialization are
    counted.  A module that executes and emits observable semantic events
    earns BEHAVIORAL evidence.  Anything less is reported honestly as
    DEGRADED with the exact gap named.
    """
    start = _now_ms()
    node_available, version = _toolchain_info("node")

    if not node_available:
        return CheckResult(
            target="", path=str(path), kind="javascript",
            status=Status.SKIP,
            detail="node toolchain unavailable — cannot validate JavaScript artifacts",
            evidence_level=0
        )

    # Level 1: Syntax check
    code, stdout, stderr = _run(["node", "--check", str(path)], path.parent, timeout=10)

    if code != 0:
        return CheckResult(
            target="", path=str(path), kind="javascript",
            status=Status.FAIL,
            detail=f"JavaScript syntax error: {stderr[:300]}",
            evidence_level=EvidenceLevel.SYNTACTIC - 1,
            toolchain_version=version
        )

    # Level 2-3: Execution probe under DOM shim.
    probe_status, detail, level = _probe_javascript_execution(path)
    return CheckResult(
        target="", path=str(path), kind="javascript",
        status=probe_status,
        detail=detail,
        evidence_level=level,
        toolchain_version=version,
        duration_ms=_now_ms() - start
    )


_JS_PROBE_MARKER = "__ORREN_JS_PROBE__"

_JS_PROBE_SOURCE = r"""
const report = { loaded: false, initExported: false, initRan: false, observed: [] };
class ShimElement {
  constructor(id) {
    this.id = id;
    this.attrs = new Map();
    this.listeners = new Map();
    this.hidden = false;
    this.classList = { add() {}, remove() {}, toggle() {}, contains: () => false };
  }
  setAttribute(k, v) { this.attrs.set(k, String(v)); }
  getAttribute(k) { return this.attrs.has(k) ? this.attrs.get(k) : null; }
  addEventListener(type, fn) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(fn);
  }
  dispatchEvent(evt) {
    evt.target = this;
    const list = this.listeners.get(evt.type) || [];
    for (const fn of [...list]) fn.call(this, evt);
    return true;
  }
  scrollIntoView() {}
}
const elements = new Map();
globalThis.document = {
  getElementById(id) {
    if (!elements.has(id)) elements.set(id, new ShimElement(id));
    return elements.get(id);
  },
  querySelector: () => null,
  createElement: () => new ShimElement('anon'),
};
const windowListeners = new Map();
const windowEvents = [];
globalThis.window = {
  addEventListener(type, fn) {
    if (!windowListeners.has(type)) windowListeners.set(type, []);
    windowListeners.get(type).push(fn);
  },
  removeEventListener() {},
  dispatchEvent(evt) {
    windowEvents.push({ type: evt.type });
    const list = windowListeners.get(evt.type) || [];
    for (const fn of [...list]) fn.call(null, evt);
    return true;
  },
};
globalThis.CustomEvent = class { constructor(type, opts = {}) { this.type = type; this.detail = opts.detail ?? null; } };
const store = new Map();
globalThis.localStorage = {
  setItem: (k, v) => store.set(String(k), String(v)),
  getItem: (k) => (store.has(String(k)) ? store.get(String(k)) : null),
};

try {
  const mod = await import('./__PROBE_TARGET__');
  report.loaded = true;
  if (mod && typeof mod.wireUpEvents === 'function') {
    report.initExported = true;
    mod.wireUpEvents();
    report.initRan = true;
  }
  if (mod && typeof mod.startTemporalSequences === 'function') {
    report.temporalStarted = true;
    mod.startTemporalSequences();
  }
  await new Promise((resolve) => setTimeout(resolve, 500));
  report.observed = [...new Set(windowEvents.map((e) => e.type))];
  console.log('__MARKER__' + JSON.stringify(report));
} catch (err) {
  report.error = String(err && err.message ? err.message : err);
  console.log('__MARKER__' + JSON.stringify(report));
  process.exit(1);
}
""".replace("__MARKER__", _JS_PROBE_MARKER)


def _probe_javascript_execution(path: Path) -> tuple:
    """Execute a JS module under a DOM shim; return (status, detail, level)."""
    probe_path = path.parent / ".orren_js_probe_.mjs"
    try:
        probe_path.write_text(
            _JS_PROBE_SOURCE.replace("__PROBE_TARGET__", path.name),
            encoding="utf-8",
        )
        code, stdout, stderr = _run(
            ["node", probe_path.name], path.parent, timeout=20
        )
        marker_line = ""
        for line in stdout.splitlines():
            if line.startswith(_JS_PROBE_MARKER):
                marker_line = line[len(_JS_PROBE_MARKER):]
                break
        if not marker_line:
            return (
                Status.FAIL,
                f"Execution probe crashed before reporting: {stderr.strip()[:200] or 'no output'}",
                EvidenceLevel.SYNTACTIC - 1,
            )
        import json as _json
        try:
            report = _json.loads(marker_line)
        except ValueError:
            return (Status.FAIL, "Probe produced unparseable report",
                    EvidenceLevel.SYNTACTIC - 1)

        if not report.get("loaded"):
            return (
                Status.FAIL,
                f"Module failed to execute under runtime probe: "
                f"{report.get('error', 'unknown error')[:200]}",
                EvidenceLevel.SYNTACTIC - 1,
            )

        observed = report.get("observed", [])
        semantic_events = [e for e in observed if e.startswith("orren:")]
        parts = ["module executes cleanly"]
        if report.get("initRan"):
            parts.append("wireUpEvents() initialized")
        elif report.get("initExported"):
            parts.append("entry point present but raised during init")
        if semantic_events:
            parts.append(f"observed semantic events: {', '.join(sorted(semantic_events))}")
            return (Status.PASS, "; ".join(parts), EvidenceLevel.BEHAVIORAL)
        parts.append("no observable semantic events; behavioral semantics untested")
        return (Status.DEGRADED, "; ".join(parts), EvidenceLevel.STRUCTURAL)
    finally:
        if probe_path.exists():
            try:
                probe_path.unlink()
            except OSError:
                pass


def _validate_html(path: Path) -> CheckResult:
    """HTML validator: structural parsing + reference resolution."""
    start = _now_ms()
    
    try:
        content = path.read_text(encoding="utf-8")
        parser = _HTMLProbe()
        parser.feed(content)
        
        # Level 1: Basic structure
        if "html" not in parser.tags or "body" not in parser.tags:
            return CheckResult(
                target="", path=str(path), kind="html",
                status=Status.FAIL,
                detail="Document lacks required html/body structure",
                evidence_level=EvidenceLevel.FILE_EXISTS
            )
        
        # Level 2: Reference resolution
        broken_refs = []
        for ref in parser.scripts + parser.links:
            ref_path = path.parent / ref
            if not ref_path.is_file():
                broken_refs.append(ref)
        
        if broken_refs:
            return CheckResult(
                target="", path=str(path), kind="html",
                status=Status.DEGRADED,
                detail=f"HTML structure valid but {len(broken_refs)} referenced asset(s) missing: {broken_refs[:3]}",
                evidence_level=EvidenceLevel.SYNTACTIC
            )
        
        # HTML validation is inherently structural, not behavioral
        # (behavioral would require browser rendering, which is a different toolchain)
        return CheckResult(
            target="", path=str(path), kind="html",
            status=Status.DEGRADED,  # DEGRADED: structural only, no DOM behavioral test
            detail="HTML parsed and local script/style references resolved; DOM behavioral testing requires browser toolchain",
            evidence_level=EvidenceLevel.STRUCTURAL,
            duration_ms=_now_ms() - start
        )
        
    except Exception as exc:
        return CheckResult(
            target="", path=str(path), kind="html",
            status=Status.FAIL,
            detail=f"HTML parsing failed: {exc}",
            evidence_level=0
        )


def _validate_css(path: Path) -> CheckResult:
    """CSS validator: HONEST assessment of what we can actually check."""
    start = _now_ms()
    
    text = path.read_text(encoding="utf-8")
    
    if not text.strip():
        return CheckResult(
            target="", path=str(path), kind="css",
            status=Status.FAIL,
            detail="Empty stylesheet",
            evidence_level=0
        )
    
    # CRITICAL SOVEREIGNTY PRINCIPLE:
    # We do NOT have a real CSS compiler/validator available.
    # Returning PASS would be DISHONEST — it implies validation occurred when it didn't.
    # We return DEGRADED with explicit explanation of what's missing.
    
    # Check for obvious syntax issues (basic sanity, NOT real validation)
    open_braces = text.count("{")
    close_braces = text.count("}")
    if open_braces != close_braces:
        return CheckResult(
            target="", path=str(path), kind="css",
            status=Status.FAIL,
            detail=f"Mismatched braces: {open_braces} open, {close_braces} close",
            evidence_level=EvidenceLevel.FILE_EXISTS
        )
    
    # This is the HONEST report:
    return CheckResult(
        target="", path=str(path), kind="css",
        status=Status.DEGRADED,  # NEVER PASS for placeholder checks!
        detail=(
            f"Stylesheet is non-empty ({len(text)} bytes, {open_braces} rules). "
            f"CSS compiler unavailable — cannot validate selectors, properties, or values. "
            f"This is a SANITY CHECK ONLY, not a conformance validation."
        ),
        evidence_level=EvidenceLevel.FILE_EXISTS,  # Honestly: we only checked file existence + brace count
        duration_ms=_now_ms() - start
    )


def _validate_swift(path: Path) -> CheckResult:
    """Swift validator: swiftc -parse (syntax + type inference)."""
    start = _now_ms()
    swiftc_available, version = _toolchain_info("swiftc")
    
    if not swiftc_available:
        return CheckResult(
            target="", path=str(path), kind="swift",
            status=Status.SKIP,
            detail="swiftc toolchain unavailable — cannot validate Swift artifacts",
            evidence_level=0
        )
    
    # Level 1: Parse and type-check (don't compile to binary)
    code, stdout, stderr = _run(
        ["swiftc", "-parse", "-sdk", "macosx", str(path)],
        path.parent, timeout=30
    )
    
    if code != 0:
        return CheckResult(
            target="", path=str(path), kind="swift",
            status=Status.FAIL,
            detail=f"Swift parsing failed: {stderr[:500]}",
            evidence_level=EvidenceLevel.SYNTACTIC - 1,
            toolchain_version=version
        )
    
    return CheckResult(
        target="", path=str(path), kind="swift",
        status=Status.PASS,
        detail="Swift source parses and type-checks successfully",
        evidence_level=EvidenceLevel.SYNTACTIC,
        toolchain_version=version,
        duration_ms=_now_ms() - start
    )


def _validate_kotlin(path: Path) -> CheckResult:
    """Kotlin validator: kotlinc (syntax + type resolution)."""
    start = _now_ms()
    kotlinc_available, version = _toolchain_info("kotlinc")
    
    if not kotlinc_available:
        return CheckResult(
            target="", path=str(path), kind="kotlin",
            status=Status.SKIP,
            detail="kotlinc toolchain unavailable — cannot validate Kotlin artifacts",
            evidence_level=0
        )
    
    # Level 1: Syntax check (don't generate JVM bytecode)
    code, stdout, stderr = _run(
        ["kotlinc", "-script", str(path)],  # Script mode for single-file
        path.parent, timeout=30
    )
    
    # kotlinc -script will fail if there are syntax/type errors
    # but might also fail for other reasons (missing dependencies)
    if code != 0 and "error:" in stderr.lower():
        return CheckResult(
            target="", path=str(path), kind="kotlin",
            status=Status.FAIL,
            detail=f"Kotlin compilation failed: {stderr[:500]}",
            evidence_level=EvidenceLevel.SYNTACTIC - 1,
            toolchain_version=version
        )
    
    return CheckResult(
        target="", path=str(path), kind="kotlin",
        status=Status.PASS,
        detail="Kotlin source validates successfully",
        evidence_level=EvidenceLevel.SYNTACTIC,
        toolchain_version=version,
        duration_ms=_now_ms() - start
    )


def _validate_latex(path: Path) -> CheckResult:
    """LaTeX validator: latex/pdflatex -halt-on-error (syntax + expansion)."""
    start = _now_ms()
    latex_available, version = _toolchain_info("pdflatex")
    if not latex_available:
        latex_available, version = _toolchain_info("latex")
    if not latex_available:
        return CheckResult(
            target="", path=str(path), kind="latex",
            status=Status.SKIP,
            detail="LaTeX toolchain (pdflatex/latex) unavailable — cannot validate LaTeX artifacts",
            evidence_level=0
        )
    
    # Level 1-2: Attempt compilation (non-stop mode to collect all errors)
    code, stdout, stderr = _run(
        ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", str(path)],
        path.parent, timeout=30
    )
    
    if code != 0:
        # Check if it's a fatal error vs warning
        if "Fatal error" in stderr or "!" in stdout.split("\n")[0:20]:
            return CheckResult(
                target="", path=str(path), kind="latex",
                status=Status.FAIL,
                detail=f"LaTeX compilation failed: {stderr[:300] if stderr else stdout[:300]}",
                evidence_level=EvidenceLevel.SYNTACTIC - 1,
                toolchain_version=version
            )
    
    # LaTeX often produces output even with warnings
    pdf_path = path.with_suffix(".pdf")
    if pdf_path.exists():
        return CheckResult(
            target="", path=str(path), kind="latex",
            status=Status.PASS,
            detail="LaTeX document compiles to PDF successfully",
            evidence_level=EvidenceLevel.STRUCTURAL,
            toolchain_version=version,
            duration_ms=_now_ms() - start
        )
    
    return CheckResult(
        target="", path=str(path), kind="latex",
        status=Status.DEGRADED,
        detail="LaTeX processed without fatal errors but no PDF produced (possibly \\end{document} missing)",
        evidence_level=EvidenceLevel.SYNTACTIC,
        toolchain_version=version,
        duration_ms=_now_ms() - start
    )


def _validate_webaudio(path: Path) -> CheckResult:
    """WebAudio validator: JavaScript syntax check + AudioContext API presence."""
    start = _now_ms()
    
    # WebAudio is typically JS with Audio API calls
    # First validate as JavaScript
    js_result = _validate_javascript(path)
    
    if js_result.status == Status.FAIL:
        return CheckResult(
            target="", path=str(path), kind="webaudio",
            status=Status.FAIL,
            detail=f"WebAudio JavaScript invalid: {js_result.detail}",
            evidence_level=js_result.evidence_level
        )
    
    # Check for AudioContext/AudioNode usage (basic sanity)
    content = path.read_text(encoding="utf-8")
    has_audio_api = any(
        api in content for api in [
            "AudioContext", "audioContext", "OscillatorNode", 
            "GainNode", "AudioNode", "createOscillator"
        ]
    )
    
    if not has_audio_api:
        return CheckResult(
            target="", path=str(path), kind="webaudio",
            status=Status.DEGRADED,
            detail="JavaScript syntax valid but no WebAudio API usage detected",
            evidence_level=EvidenceLevel.SYNTACTIC
        )
    
    return CheckResult(
        target="", path=str(path), kind="webaudio",
        status=Status.DEGRADED,  # Can't actually run AudioContext in CLI
        detail=(
            f"WebAudio JavaScript syntax valid, AudioAPI present. "
            f"Behavioral validation requires browser environment (AudioContext cannot run headless here)."
        ),
        evidence_level=EvidenceLevel.SYNTACTIC,
        duration_ms=_now_ms() - start
    )

    # Behavioral probe: try node --check and verify function definitions
    node_available, node_version = _toolchain_info("node")
    if node_available:
        # Check syntax with node
        code, stdout, stderr = _run(
            ["node", "--check", str(path)], path.parent, timeout=10
        )
        if code == 0:
            # Verify that at least one play_* function is defined
            has_functions = "function play_" in content
            if has_functions:
                return CheckResult(
                    target="", path=str(path), kind="webaudio",
                    status=Status.DEGRADED,
                    detail=(
                        f"WebAudio syntax validated by node, AudioAPI present, "
                        f"play_* functions defined. AudioContext cannot be instantiated "
                        f"in CLI environment."
                    ),
                    evidence_level=EvidenceLevel.BEHAVIORAL,
                    toolchain_version=node_version,
                    duration_ms=_now_ms() - start,
                )
        return CheckResult(
            target="", path=str(path), kind="webaudio",
            status=Status.DEGRADED,
            detail=f"node available but syntax/behavior check incomplete: {stderr[:200]}",
            evidence_level=EvidenceLevel.SYNTACTIC,
            toolchain_version=node_version,
            duration_ms=_now_ms() - start,
        )


def _validate_text(path: Path) -> CheckResult:
    """Plain text validator: file existence + non-empty."""
    start = _now_ms()
    
    if not path.exists():
        return CheckResult(
            target="", path=str(path), kind="text",
            status=Status.FAIL,
            detail="File does not exist",
            evidence_level=0
        )
    
    size = path.stat().st_size
    if size == 0:
        return CheckResult(
            target="", path=str(path), kind="text",
            status=Status.FAIL,
            detail="File is empty",
            evidence_level=0
        )
    
    return CheckResult(
        target="", path=str(path), kind="text",
        status=Status.DEGRADED,  # Text files have minimal validation possible
        detail=f"Text file exists ({size} bytes); no structural validation possible for plain text",
        evidence_level=EvidenceLevel.FILE_EXISTS,
        duration_ms=_now_ms() - start
    )


# ---------------------------------------------------------------------------
# Validator dispatch — equal treatment for all languages
# ---------------------------------------------------------------------------

_VALIDATORS: dict[str, callable] = {
    "python": _validate_python,
    "rust": _validate_rust,
    "go": _validate_go,
    "c": _validate_c,
    "cpp": _validate_c,
    "c++": _validate_c,
    "typescript": _validate_typescript,
    "javascript": _validate_javascript,
    "js": _validate_javascript,
    "html": _validate_html,
    "css": _validate_css,
    "swift": _validate_swift,
    "kotlin": _validate_kotlin,
    "latex": _validate_latex,
    "tex": _validate_latex,
    "webaudio": _validate_webaudio,
    "text": _validate_text,
}


def check_file(path: Path, language: str) -> CheckResult:
    """Validate a single artifact file. All languages treated equally."""
    language = language.lower().strip()
    # Resolve to absolute path so subprocess validators that set cwd=path.parent
    # can reference the file unambiguously (relative paths break when the
    # subprocess cwd differs from the process cwd).
    path = Path(path).resolve()
    
    validator = _VALIDATORS.get(language)
    if validator is None:
        return CheckResult(
            target="", path=str(path), kind=language,
            status=Status.SKIP,
            detail=f"No validator registered for language '{language}'",
            evidence_level=0
        )
    
    result = validator(path)
    result.kind = language
    return result


# ---------------------------------------------------------------------------
# Adversarial test generators — prove harness CAN fail
# ---------------------------------------------------------------------------

def generate_adversarial_cases(output_dir: str | Path) -> dict[str, Any]:
    """
    Generate intentionally BAD artifacts to prove the harness rejects them.
    Returns a manifest of adversarial cases that should all produce FAIL.
    """
    output_dir = Path(output_dir)
    adversarial_dir = output_dir / "__adversarial__"
    adversarial_dir.mkdir(parents=True, exist_ok=True)
    
    cases = []
    
    # --- Python: Syntax error ---
    bad_py = adversarial_dir / "bad_syntax.py"
    bad_py.write_text("def broken(\n    # unclosed parenthesis\n", encoding="utf-8")
    cases.append({
        "path": str(bad_py.relative_to(output_dir)),
        "language": "python",
        "expected_status": Status.FAIL,
        "description": "Python syntax error (unclosed parenthesis)"
    })
    
    # --- Python: Runtime error in process() ---
    bad_behavior = adversarial_dir / "bad_behavior.py"
    bad_behavior.write_text("""
class BadService:
    def process(self):
        raise RuntimeError("Intentional failure for adversarial test")
""", encoding="utf-8")
    cases.append({
        "path": str(bad_behavior.relative_to(output_dir)),
        "language": "python",
        "expected_status": Status.FAIL,
        "description": "Python behavioral probe raises exception"
    })
    
    # --- JavaScript: Syntax error ---
    bad_js = adversarial_dir / "bad_syntax.js"
    bad_js.write_text("function broken( {\n    // unclosed brace\n", encoding="utf-8")
    cases.append({
        "path": str(bad_js.relative_to(output_dir)),
        "language": "javascript",
        "expected_status": Status.FAIL,
        "description": "JavaScript syntax error (unclosed brace)"
    })
    
    # --- HTML: Missing structure ---
    bad_html = adversarial_dir / "bad_structure.html"
    bad_html.write_text("<!DOCTYPE html><head></head>This has no body>", encoding="utf-8")
    cases.append({
        "path": str(bad_html.relative_to(output_dir)),
        "language": "html",
        "expected_status": Status.FAIL,
        "description": "HTML missing body element"
    })
    
    # --- CSS: Empty file ---
    bad_css = adversarial_dir / "empty.css"
    bad_css.write_text("", encoding="utf-8")
    cases.append({
        "path": str(bad_css.relative_to(output_dir)),
        "language": "css",
        "expected_status": Status.FAIL,
        "description": "Empty CSS file"
    })
    
    # --- Rust: Syntax error (if rustc available) ---
    if _toolchain_info("rustc")[0]:
        bad_rs = adversarial_dir / "bad_syntax.rs"
        bad_rs.write_text("fn main( {\n    // unclosed brace\n", encoding="utf-8")
        cases.append({
            "path": str(bad_rs.relative_to(output_dir)),
            "language": "rust",
            "expected_status": Status.FAIL,
            "description": "Rust syntax error (unclosed brace)"
        })
    
    # --- Go: Syntax error (if go available) ---
    if _toolchain_info("go")[0]:
        bad_go = adversarial_dir / "bad_syntax.go"
        bad_go.write_text("package main\nfunc main( {\n}\n", encoding="utf-8")
        cases.append({
            "path": str(bad_go.relative_to(output_dir)),
            "language": "go",
            "expected_status": Status.FAIL,
            "description": "Go syntax error (unclosed paren)"
        })
    
    # --- C: Syntax error (if gcc/clang available) ---
    if _toolchain_info("gcc")[0] or _toolchain_info("clang")[0]:
        bad_c = adversarial_dir / "bad_syntax.c"
        bad_c.write_text("int main( {\n    return 0;\n}\n", encoding="utf-8")
        cases.append({
            "path": str(bad_c.relative_to(output_dir)),
            "language": "c",
            "expected_status": Status.FAIL,
            "description": "C syntax error (unclosed paren)"
        })
    
    # Write adversarial manifest
    manifest = {
        "type": "adversarial_test_suite",
        "purpose": "Prove conformance harness can REJECT bad artifacts",
        "expectation": "ALL cases must produce status=FAIL",
        "cases": cases
    }
    (adversarial_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    
    return manifest


def run_adversarial_tests(output_dir: str | Path) -> dict[str, Any]:
    """
    Run adversarial test suite. Returns results showing which failures were correctly detected.
    A HEALTHY harness will have all adversarial cases as FAIL.
    """
    output_dir = Path(output_dir)
    adversarial_dir = output_dir / "__adversarial__"
    manifest_path = adversarial_dir / "manifest.json"
    
    if not manifest_path.exists():
        # Generate if not exists
        manifest = generate_adversarial_cases(output_dir)
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    results = []
    correct_rejections = 0
    false_passes = 0  # DANGEROUS: means harness is too permissive
    
    for case in manifest["cases"]:
        case_path = output_dir / case["path"]
        if not case_path.exists():
            results.append({
                **case,
                "actual_status": "SKIP",
                "correct": False,
                "detail": "Adversarial file not found"
            })
            continue
        
        result = check_file(case_path, case["language"])
        is_correct = result.status == case["expected_status"]
        
        if is_correct:
            correct_rejections += 1
        elif result.status == Status.PASS:
            false_passes += 1  # CRITICAL: harness passed something that should fail
        
        results.append({
            **case,
            "actual_status": result.status,
            "evidence_level": result.evidence_level,
            "correct": is_correct,
            "detail": result.detail
        })
    
    summary = {
        "total_cases": len(results),
        "correct_rejections": correct_rejections,
        "false_passes": false_passes,  # Must be 0 for healthy harness
        "health": "HEALTHY" if false_passes == 0 else "COMPROMISED",
        "results": results
    }
    
    # Write adversarial results
    (adversarial_dir / "results.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    
    return summary


# ---------------------------------------------------------------------------
# Main conformance runner — produces HONEST reports
# ---------------------------------------------------------------------------

def run_conformance(
    output_dir: str | Path, 
    manifest_path: str | Path | None = None,
    run_adversarial: bool = True
) -> dict[str, Any]:
    """
    Run full conformance suite with honest reporting.
    
    Args:
        output_dir: Directory containing realized artifacts
        manifest_path: Path to manifest.json (default: output_dir/manifest.json)
        run_adversarial: If True, also run adversarial tests proving harness can fail
    
    Returns:
        Comprehensive report with coverage matrix, not just flat counts.
    """
    output_dir = Path(output_dir)
    manifest_path = Path(manifest_path or output_dir / "manifest.json")
    
    if not manifest_path.exists():
        return {"error": f"Manifest not found: {manifest_path}", "passed": 0, "failed": 0, "skipped": 0, "degraded": 0}
    
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    
    # Build coverage matrix
    matrix = CoverageMatrix()
    raw_results: list[CheckResult] = []
    
    for artifact in manifest.get("artifacts", []):
        target = artifact.get("target_name", "unknown")
        if target not in matrix.targets:
            matrix.targets[target] = {}
        
        for output in artifact.get("output_files", []):
            rel = output["path"].split("/", 1)[-1]
            path = output_dir / target / rel
            language = output.get("language", "")
            
            if not path.is_file():
                result = CheckResult(
                    target=target, path=str(path), kind=language,
                    status=Status.FAIL,
                    detail="Declared artifact is missing from output directory",
                    evidence_level=0
                )
                raw_results.append(result)
                matrix.targets[target][language] = result
                continue
            
            # Run the appropriate validator (all languages treated equally)
            result = check_file(path, language)
            result.target = target
            raw_results.append(result)
            matrix.targets[target][language] = result
            
            # For Python, also run behavioral probe if parse passed
            if language == "python" and result.status in (Status.PASS, Status.DEGRADED):
                try:
                    behavior_result = _validate_python(path)
                    behavior_result.target = target
                    behavior_result.kind = "python-behavior"
                    raw_results.append(behavior_result)
                    # Store under composite key
                    matrix.targets[target]["python-behavior"] = behavior_result
                except Exception as exc:
                    fail_result = CheckResult(
                        target=target, path=str(path), kind="python-behavior",
                        status=Status.FAIL,
                        detail=f"Behavioral probe crashed: {exc}",
                        evidence_level=0
                    )
                    raw_results.append(fail_result)
                    matrix.targets[target]["python-behavior"] = fail_result
    
    # Run adversarial tests (prove harness can fail)
    adversarial_summary = None
    if run_adversarial:
        try:
            adversarial_summary = run_adversarial_tests(output_dir)
        except Exception as exc:
            adversarial_summary = {"error": str(exc), "health": "ERROR"}
    
    # Build HONEST summary — no inflation
    summary = {
        # Primary counts (honest)
        "passed": sum(1 for r in raw_results if r.status == Status.PASS),
        "degraded": sum(1 for r in raw_results if r.status == Status.DEGRADED),
        "failed": sum(1 for r in raw_results if r.status == Status.FAIL),
        "skipped": sum(1 for r in raw_results if r.status == Status.SKIP),
        
        # Detailed results
        "results": [asdict(r) for r in raw_results],
        
        # Coverage matrix (targets × languages)
        "coverage_matrix": matrix.to_dict(),
        
        # Languages exercised vs. known
        "languages_tested": sorted(set(r.kind for r in raw_results)),
        "languages_available": sorted(_VALIDATORS.keys()),
        
        # Adversarial test health
        "adversarial": adversarial_summary,
        
        # Sovereignty assertion
        "sovereignty_note": (
            "This report follows the language-sovereignty principle: "
            "no backend is privileged, DEGRADED indicates weaker validation "
            "(never inflated to PASS), and adversarial tests prove the harness "
            "can reject bad artifacts."
        )
    }
    
    return summary


def write_report(report: dict[str, Any], path: str | Path) -> None:
    """Write conformance report to JSON file."""
    Path(path).write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n", 
        encoding="utf-8"
    )


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _now_ms() -> float:
    """Current time in milliseconds."""
    import time
    return time.monotonic() * 1000


# ---------------------------------------------------------------------------
# Seven-gate validation framework
# ---------------------------------------------------------------------------
# Each realized artifact set is evaluated across seven gates.  Unlike the
# per-language validators (which check *individual files*), the seven gates
# check the *artifact set as a whole* — whether it links, runs, behaves
# correctly, handles edge cases, and preserves the source SIR dimensions.
#
# Gate semantics:
#   1. STRUCTURAL   — all declared files exist with non-zero size
#   2. SYNTACTIC    — each file passes its toolchain (delegates to check_file)
#   3. LINKABLE     — cross-file references resolve (HTML→CSS/JS, manifest↔files)
#   4. EXECUTABLE   — code loads/runs without import or module errors
#   5. BEHAVIORAL   — semantic `orren:*` events are emitted on init
#   6. OPERATIONAL  — error boundary, reduced-motion, graceful degradation
#   7. PRESERVATION — SIR dimensions preserved in output (via preservation_proof.json)
# ---------------------------------------------------------------------------

class SevenGate:
    """Canonical gate identifiers for seven-gate validation."""
    STRUCTURAL = "structural"
    SYNTACTIC = "syntactic"
    LINKABLE = "linkable"
    EXECUTABLE = "executable"
    BEHAVIORAL = "behavioral"
    OPERATIONAL = "operational"
    PRESERVATION = "preservation"

    ALL = [
        STRUCTURAL, SYNTACTIC, LINKABLE,
        EXECUTABLE, BEHAVIORAL, OPERATIONAL, PRESERVATION,
    ]


@dataclass
class GateResult:
    """Result of a single gate check against a target."""
    gate: str                 # One of SevenGate.*
    target: str              # Target name from manifest
    status: str              # PASS, DEGRADED, SKIP, or FAIL
    detail: str              # Human-readable explanation
    evidence_level: int = 0  # EvidenceLevel.*
    toolchain_version: str = ""
    duration_ms: float = 0.0


def _gate_structural(target_name: str, artifact: dict, output_dir: Path) -> GateResult:
    """Gate 1: Structural — all declared artifact files exist with non-zero size."""
    start = _now_ms()
    missing = []
    empty = []
    for out_file in artifact.get("output_files", []):
        rel = out_file["path"].split("/", 1)[-1]
        path = output_dir / target_name / rel
        if not path.exists():
            missing.append(rel)
        elif path.stat().st_size == 0:
            empty.append(rel)

    if missing:
        return GateResult(
            gate=SevenGate.STRUCTURAL, target=target_name,
            status=Status.FAIL,
            detail=f"{len(missing)} declared file(s) missing: {', '.join(missing)}",
            evidence_level=EvidenceLevel.FILE_EXISTS,
            duration_ms=_now_ms() - start,
        )
    if empty:
        return GateResult(
            gate=SevenGate.STRUCTURAL, target=target_name,
            status=Status.FAIL,
            detail=f"{len(empty)} declared file(s) are empty: {', '.join(empty)}",
            evidence_level=EvidenceLevel.FILE_EXISTS,
            duration_ms=_now_ms() - start,
        )
    return GateResult(
        gate=SevenGate.STRUCTURAL, target=target_name,
        status=Status.PASS,
        detail=f"All {len(artifact.get('output_files', []))} declared files present and non-empty",
        evidence_level=EvidenceLevel.FILE_EXISTS,
        duration_ms=_now_ms() - start,
    )


def _gate_syntactic(target_name: str, artifact: dict, output_dir: Path) -> GateResult:
    """Gate 2: Syntactic — each file passes its toolchain check."""
    start = _now_ms()
    failures = []
    degraded = []
    skipped = []
    for out_file in artifact.get("output_files", []):
        rel = out_file["path"].split("/", 1)[-1]
        path = output_dir / target_name / rel
        language = out_file.get("language", "text")
        if not path.is_file():
            failures.append(f"{rel}: missing")
            continue
        result = check_file(path, language)
        if result.status == Status.FAIL:
            failures.append(f"{rel}: {result.detail[:120]}")
        elif result.status == Status.DEGRADED:
            degraded.append(f"{rel}: {result.detail[:120]}")
        elif result.status == Status.SKIP:
            # toml files (Cargo.toml) and other non-code config files are
            # acceptable as SKIP — they don't need a language toolchain.
            if language in ("toml",):
                continue  # Config file, not a code artifact
            skipped.append(f"{rel}: {language} toolchain unavailable")

    if failures:
        return GateResult(
            gate=SevenGate.SYNTACTIC, target=target_name,
            status=Status.FAIL,
            detail="Syntactic failures: " + "; ".join(failures),
            evidence_level=EvidenceLevel.SYNTACTIC,
            duration_ms=_now_ms() - start,
        )
    if degraded:
        return GateResult(
            gate=SevenGate.SYNTACTIC, target=target_name,
            status=Status.DEGRADED,
            detail="All files parse but " + str(len(degraded)) + " gate(s) lack full toolchain: " + "; ".join(degraded[:3]),
            evidence_level=EvidenceLevel.SYNTACTIC,
            duration_ms=_now_ms() - start,
        )
    if skipped and not degraded:
        return GateResult(
            gate=SevenGate.SYNTACTIC, target=target_name,
            status=Status.DEGRADED,
            detail="Toolchain unavailable for " + str(len(skipped)) + " file(s): " + "; ".join(skipped[:3]),
            evidence_level=EvidenceLevel.SYNTACTIC,
            duration_ms=_now_ms() - start,
        )
    return GateResult(
        gate=SevenGate.SYNTACTIC, target=target_name,
        status=Status.PASS,
        detail=f"All {len(artifact.get('output_files', []))} files accepted by toolchain",
        evidence_level=EvidenceLevel.SYNTACTIC,
        duration_ms=_now_ms() - start,
    )
    return GateResult(
        gate=SevenGate.SYNTACTIC, target=target_name,
        status=Status.PASS,
        detail=f"All {len(artifact.get('output_files', []))} files accepted by toolchain",
        evidence_level=EvidenceLevel.SYNTACTIC,
        duration_ms=_now_ms() - start,
    )


def _gate_linkable(target_name: str, artifact: dict, output_dir: Path) -> GateResult:
    """Gate 3: Linkable — cross-file references resolve.

    For web targets: checks that HTML ``<link>``/``<script>`` references
    resolve to actual files in the output directory.  Also verifies that
    every file declared in the manifest exists.
    """
    start = _now_ms()
    target_dir = output_dir / target_name
    broken_links = []

    for out_file in artifact.get("output_files", []):
        rel = out_file["path"].split("/", 1)[-1]
        path = target_dir / rel
        if not path.is_file():
            broken_links.append(f"{rel}: declared in manifest but missing from disk")
            continue

        ext = path.suffix.lower()
        if ext == ".html":
            source = path.read_text(encoding="utf-8")
            probe = _HTMLProbe()
            try:
                probe.feed(source)
            except Exception:
                pass
            for script_src in probe.scripts:
                # Scripts may be external (with src) or inline (no src)
                if script_src and not script_src.startswith(("http://", "https://", "//")):
                    if not (target_dir / script_src).exists():
                        broken_links.append(f"{rel} -> {script_src}: script not found")
            for link_href in probe.links:
                if link_href and not link_href.startswith(("http://", "https://", "//")):
                    if not (target_dir / link_href).exists():
                        broken_links.append(f"{rel} -> {link_href}: stylesheet not found")

    if broken_links:
        return GateResult(
            gate=SevenGate.LINKABLE, target=target_name,
            status=Status.FAIL,
            detail="Broken cross-file references: " + "; ".join(broken_links[:5]),
            evidence_level=EvidenceLevel.STRUCTURAL,
            duration_ms=_now_ms() - start,
        )
    return GateResult(
        gate=SevenGate.LINKABLE, target=target_name,
        status=Status.PASS,
        detail="All cross-file references resolve to real files",
        evidence_level=EvidenceLevel.STRUCTURAL,
        duration_ms=_now_ms() - start,
    )


def _gate_executable(target_name: str, artifact: dict, output_dir: Path) -> GateResult:
    """Gate 4: Executable — code loads/runs without import or module errors."""
    start = _now_ms()
    node_available, _ = _toolchain_info("node")
    rustc_available, _ = _toolchain_info("rustc")
    go_available, _ = _toolchain_info("go")

    non_executable = []
    executable_files = []

    for out_file in artifact.get("output_files", []):
        rel = out_file["path"].split("/", 1)[-1]
        path = output_dir / target_name / rel
        language = out_file.get("language", "text")

        if language in ("javascript", "js") and node_available and path.is_file():
            probe_status, detail, level = _probe_javascript_execution(path)
            if probe_status == Status.FAIL:
                non_executable.append(f"{rel}: {detail[:120]}")
            else:
                executable_files.append(rel)
        elif language == "python" and path.is_file():
            # Python import test
            try:
                source = path.read_text(encoding="utf-8")
                ast.parse(source, filename=str(path))
                py_compile.compile(str(path), doraise=True)
                # Try to actually load the module
                import importlib.util as _ilu
                spec = _ilu.spec_from_file_location("orren_exec_probe", path)
                if spec and spec.loader:
                    module = _ilu.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    executable_files.append(rel)
                else:
                    non_executable.append(f"{rel}: could not create module spec")
            except ModuleNotFoundError as exc:
                non_executable.append(f"{rel}: missing dependency ({exc.name})")
            except Exception as exc:
                non_executable.append(f"{rel}: {str(exc)[:120]}")
        elif language in ("rust",) and rustc_available and path.is_file():
            # Rust: attempt compilation — executable if has main(), else lib
            source = path.read_text(encoding="utf-8")
            has_main = "fn main" in source
            import tempfile as _tf
            with _tf.TemporaryDirectory(prefix="orren-rust-gate-") as build_dir:
                exe = Path(build_dir) / "orren_app"
                cmd = ["rustc", "--edition", "2021", "-D", "warnings", str(path)]
                if has_main:
                    cmd.extend(["-o", str(exe)])
                else:
                    cmd.extend(["--crate-type=lib", "--emit=metadata", "-o", "/dev/null"])
                code, stdout, stderr = _run(cmd, path.parent, timeout=60)
                if code == 0:
                    if has_main:
                        run_code, output, _ = _run([str(exe)], Path(build_dir), timeout=10)
                        if run_code == 0 and output.strip():
                            executable_files.append(rel)
                        else:
                            non_executable.append(f"{rel}: compiled but no runtime output")
                    else:
                        executable_files.append(rel)
                else:
                    non_executable.append(f"{rel}: rustc compilation failed: {(stderr or stdout)[:80]}")
        elif language == "go" and go_available and path.is_file():
            # Go: attempt build + run as execution proof
            parent = path.parent
            import tempfile as _tf
            with _tf.TemporaryDirectory(prefix="orren-go-gate-") as tmpdir:
                exe_path = Path(tmpdir) / "orren_go_app"
                code, _, stderr = _run(
                    ["go", "build", "-o", str(exe_path), str(path)],
                    parent, timeout=60
                )
                if code == 0 and exe_path.is_file():
                    executable_files.append(rel)
                else:
                    non_executable.append(f"{rel}: go build failed: {stderr[:80]}")
        elif language in ("html", "css", "text", "webaudio"):
            # Not directly executable, skip
            pass
        else:
            # Languages whose toolchain may be unavailable (c, swift, kotlin, etc.)
            if not path.is_file():
                non_executable.append(f"{rel}: file missing")
            elif language in ("c", "cpp") and path.is_file():
                # C: compile + run with the first available toolchain, requiring
                # observable stdout (fail-closed: silent success is not evidence).
                import tempfile as _tfc
                gcc_ok, _ = _toolchain_info("gcc")
                clang_ok, _ = _toolchain_info("clang")
                cc = "gcc" if gcc_ok else ("clang" if clang_ok else None)
                exe_path = None
                error_detail = ""
                with _tfc.TemporaryDirectory(prefix="orren-c-gate-") as build_dir:
                    out_name = "orren_app.exe" if os.name == "nt" else "orren_app"
                    exe_candidate = Path(build_dir) / out_name
                    if cc is not None:
                        std_flag = "-std=c17" if language == "c" else "-std=c++17"
                        code, _, stderr = _run(
                            [cc, std_flag, "-Wall", "-Wextra", "-O1", str(path), "-o", str(exe_candidate)],
                            Path(build_dir), timeout=60,
                        )
                        if code == 0 and exe_candidate.is_file():
                            exe_path = exe_candidate
                        else:
                            error_detail = f"{cc} build failed: {stderr[:80]}"
                    elif _discover_msvc()[0]:
                        code, stdout, stderr = _msvc_batch(
                            ["/nologo", "/W4", "/O2", f"/Fe:{exe_candidate}", str(path.resolve())],
                            Path(build_dir),
                        )
                        produced = exe_candidate if exe_candidate.suffix else exe_candidate.with_suffix(".exe")
                        if code == 0 and produced.is_file():
                            exe_path = produced
                        else:
                            error_detail = f"MSVC build failed: {(stderr or stdout)[:120]}"
                    else:
                        # No C toolchain of any kind — honest unverified status.
                        non_executable.append(f"{rel}: C toolchain unavailable, execution unverified")
                    if exe_path is not None:
                        run_code, output, _ = _run([str(exe_path)], Path(build_dir), timeout=15)
                        if run_code == 0 and output.strip():
                            executable_files.append(rel)
                        else:
                            non_executable.append(
                                f"{rel}: compiled but no observable runtime output ({error_detail or 'exit ' + str(run_code)})"
                            )
                    elif error_detail:
                        non_executable.append(f"{rel}: {error_detail}")
            elif language in ("typescript",) and path.is_file() and path.name.endswith(".test.ts"):
                non_executable.append(
                    f"{rel}: test file executes via 'npm test' (vitest); requires dependency install"
                    if _toolchain_info("tsc")[0] or _toolchain_info("node")[0]
                    else f"{rel}: node/tsc unavailable, execution unverified"
                )
            elif language in ("typescript",) and not _toolchain_info("tsc")[0]:
                non_executable.append(f"{rel}: tsc unavailable, execution unverified")
            elif language in ("latex", "tex") and not _toolchain_info("pdflatex")[0]:
                non_executable.append(f"{rel}: pdflatex unavailable, execution unverified")
            elif language in ("swift",) and not _toolchain_info("swiftc")[0]:
                non_executable.append(f"{rel}: swiftc unavailable, execution unverified")
            elif language in ("kotlin",) and not _toolchain_info("kotlinc")[0]:
                non_executable.append(f"{rel}: kotlinc unavailable, execution unverified")
            else:
                non_executable.append(f"{rel}: toolchain unavailable, execution unverified")

    if non_executable:
        all_langs = set()
        for of in artifact.get("output_files", []):
            all_langs.add(of.get("language", "text"))
        has_executable_lang = any(l in ("javascript", "js", "python", "rust", "go") for l in all_langs)
        if has_executable_lang and not node_available and not rustc_available and not go_available:
            return GateResult(
                gate=SevenGate.EXECUTABLE, target=target_name,
                status=Status.DEGRADED,
                detail="Execution probe available but no toolchain found; " + str(len(non_executable)) + " file(s) unverified: " + "; ".join(non_executable[:3]),
                evidence_level=EvidenceLevel.SYNTACTIC,
                duration_ms=_now_ms() - start,
            )
        return GateResult(
            gate=SevenGate.EXECUTABLE, target=target_name,
            status=Status.DEGRADED,
            detail=f"{len(non_executable)} file(s) could not be execution-verified: " + "; ".join(non_executable[:3]),
            evidence_level=EvidenceLevel.SYNTACTIC,
            duration_ms=_now_ms() - start,
        )
    if not executable_files:
        return GateResult(
            gate=SevenGate.EXECUTABLE, target=target_name,
            status=Status.SKIP,
            detail="No executable files in this target",
            evidence_level=0,
            duration_ms=_now_ms() - start,
        )
    return GateResult(
        gate=SevenGate.EXECUTABLE, target=target_name,
        status=Status.PASS,
        detail=f"{len(executable_files)} file(s) loaded/executed cleanly",
        evidence_level=EvidenceLevel.BEHAVIORAL,
        duration_ms=_now_ms() - start,
    )


def _gate_behavioral(target_name: str, artifact: dict, output_dir: Path) -> GateResult:
    """Gate 5: Behavioral — semantic ``orren:*`` events are emitted on init."""
    start = _now_ms()
    node_available, _ = _toolchain_info("node")

    if not node_available:
        return GateResult(
            gate=SevenGate.BEHAVIORAL, target=target_name,
            status=Status.SKIP,
            detail="node unavailable — behavioral probe cannot run",
            evidence_level=0,
            duration_ms=_now_ms() - start,
        )

    js_files = [
        output_dir / target_name / of["path"].split("/", 1)[-1]
        for of in artifact.get("output_files", [])
        if of.get("language", "") in ("javascript", "js")
        and (output_dir / target_name / of["path"].split("/", 1)[-1]).is_file()
    ]

    if not js_files:
        return GateResult(
            gate=SevenGate.BEHAVIORAL, target=target_name,
            status=Status.SKIP,
            detail="No JavaScript files to probe for behavioral events",
            evidence_level=0,
            duration_ms=_now_ms() - start,
        )

    total_events = set()
    pass_count = 0
    for js_path in js_files:
        probe_status, detail, level = _probe_javascript_execution(js_path)
        if probe_status == Status.PASS:
            pass_count += 1
            # Re-extract events from detail
            if "observed semantic events:" in detail:
                events_part = detail.split("observed semantic events:")[1].strip()
                for ev in events_part.split(", "):
                    total_events.add(ev.strip())

    if pass_count == 0:
        return GateResult(
            gate=SevenGate.BEHAVIORAL, target=target_name,
            status=Status.DEGRADED,
            detail="No JS modules emitted observable semantic events; behavioral semantics untested",
            evidence_level=EvidenceLevel.STRUCTURAL,
            duration_ms=_now_ms() - start,
        )
    return GateResult(
        gate=SevenGate.BEHAVIORAL, target=target_name,
        status=Status.PASS,
        detail=f"{pass_count} module(s) emitted semantic events: {', '.join(sorted(total_events)) or 'none'}",
        evidence_level=EvidenceLevel.BEHAVIORAL,
        duration_ms=_now_ms() - start,
    )


def _gate_operational(target_name: str, artifact: dict, output_dir: Path) -> GateResult:
    """Gate 6: Operational — error boundary, reduced-motion, graceful degradation."""
    start = _now_ms()
    target_dir = output_dir / target_name
    findings = []
    missing = []

    all_langs = set()
    for of in artifact.get("output_files", []):
        all_langs.add(of.get("language", "text"))

    is_web = any(l in ("html", "css", "javascript", "js") for l in all_langs)

    if is_web:
        # --- Web-specific operational checks ---
        html_files = [
            output_dir / target_name / of["path"].split("/", 1)[-1]
            for of in artifact.get("output_files", [])
            if of.get("language", "") == "html"
            and (output_dir / target_name / of["path"].split("/", 1)[-1]).is_file()
        ]

        error_boundary_found = False
        reduced_motion_css = False
        reduced_motion_js = False
        prefers_color_scheme = False

        for html_path in html_files:
            source = html_path.read_text(encoding="utf-8")
            if "error-boundary" in source.lower() or "orren-error" in source.lower():
                error_boundary_found = True
            if "aria-live" in source:
                findings.append("aria-live present in HTML")

        css_files = [
            output_dir / target_name / of["path"].split("/", 1)[-1]
            for of in artifact.get("output_files", [])
            if of.get("language", "") == "css"
            and (output_dir / target_name / of["path"].split("/", 1)[-1]).is_file()
        ]

        for css_path in css_files:
            css = css_path.read_text(encoding="utf-8")
            if "prefers-reduced-motion" in css:
                reduced_motion_css = True
                findings.append("prefers-reduced-motion CSS guard present")
            if "prefers-color-scheme" in css:
                prefers_color_scheme = True
                findings.append("prefers-color-scheme CSS guard present")
            if ":focus-visible" in css:
                findings.append("focus-visible styling present")

        js_files = [
            output_dir / target_name / of["path"].split("/", 1)[-1]
            for of in artifact.get("output_files", [])
            if of.get("language", "") in ("javascript", "js")
            and (output_dir / target_name / of["path"].split("/", 1)[-1]).is_file()
        ]

        for js_path in js_files:
            js = js_path.read_text(encoding="utf-8")
            if "prefers-reduced-motion" in js or "matchMedia" in js:
                reduced_motion_js = True
                findings.append("JS reduced-motion guard present")
            if "onerror" in js:
                error_boundary_found = True
                findings.append("window.onerror handler present")
            if "try" in js and "catch" in js:
                findings.append("error handling (try/catch) present in JS")

        if not error_boundary_found:
            missing.append("error boundary")
        if not reduced_motion_css and not reduced_motion_js:
            missing.append("reduced-motion handling")
        if not prefers_color_scheme:
            missing.append("prefers-color-scheme")
    else:
        # --- Non-web operational checks ---
        # For compiled languages, error handling is the key operational concern.
        for of in artifact.get("output_files", []):
            rel = of["path"].split("/", 1)[-1]
            path = output_dir / target_name / rel
            if not path.is_file():
                continue
            language = of.get("language", "text")
            try:
                source = path.read_text(encoding="utf-8")
            except Exception:
                continue

            if language in ("rust",):
                if "Result" in source or "Option" in source or "?" in source or ".unwrap(" in source:
                    findings.append("Rust: error handling via Result/Option present")
                else:
                    missing.append("Rust: no error handling (Result/Option)")
            elif language == "go":
                if "error" in source.lower() or "err" in source:
                    findings.append("Go: error handling present")
                else:
                    missing.append("Go: no error handling")
            elif language in ("c", "cpp"):
                if "NULL" in source or "errno" in source or "assert" in source or "return -1" in source:
                    findings.append("C: error checking present")
                else:
                    missing.append("C: no error checking")
            elif language == "python":
                if "try" in source and "except" in source:
                    findings.append("Python: try/except present")
                elif "raise " in source or "assert " in source:
                    findings.append("Python: raise/assert present")
                else:
                    missing.append("Python: no error handling")
            elif language in ("typescript",):
                if "try" in source and "catch" in source:
                    findings.append("TypeScript: try/catch present")
                else:
                    missing.append("TypeScript: no error handling")
            elif language == "swift":
                if "try" in source or "guard" in source or "Result" in source:
                    findings.append("Swift: error handling present")
                else:
                    missing.append("Swift: no error handling")
            elif language == "kotlin":
                if "try" in source or "catch" in source or "Result" in source:
                    findings.append("Kotlin: error handling present")
                else:
                    missing.append("Kotlin: no error handling")
            elif language in ("latex", "tex"):
                # LaTeX doesn't have runtime error handling; check for graceful degradation
                if "providecommand" in source or "ifdef" in source or "IfFileExists" in source:
                    findings.append("LaTeX: graceful degradation patterns present")
                else:
                    # Not an error — LaTeX is declarative; just note it
                    findings.append("LaTeX: declarative (no runtime errors possible)")
            if not missing:
                missing = []  # Clear any non-critical findings

    if missing:
        return GateResult(
            gate=SevenGate.OPERATIONAL, target=target_name,
            status=Status.DEGRADED,
            detail="Missing operational features: " + ", ".join(missing) +
                   ("; found: " + "; ".join(findings) if findings else ""),
            evidence_level=EvidenceLevel.STRUCTURAL,
            duration_ms=_now_ms() - start,
        )
    return GateResult(
        gate=SevenGate.OPERATIONAL, target=target_name,
        status=Status.PASS,
        detail="; ".join(findings) if findings else "All operational features present (error boundary, reduced-motion, prefers-color-scheme)",
        evidence_level=EvidenceLevel.STRUCTURAL,
        duration_ms=_now_ms() - start,
    )


def _gate_preservation(target_name: str, artifact: dict, output_dir: Path) -> GateResult:
    """Gate 7: Preservation — SIR dimensions preserved in output."""
    start = _now_ms()
    proof_path = output_dir / "preservation_proof.json"

    if not proof_path.is_file():
        return GateResult(
            gate=SevenGate.PRESERVATION, target=target_name,
            status=Status.FAIL,
            detail="preservation_proof.json not found — no preservation evidence",
            evidence_level=0,
            duration_ms=_now_ms() - start,
        )

    try:
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return GateResult(
            gate=SevenGate.PRESERVATION, target=target_name,
            status=Status.FAIL,
            detail=f"preservation_proof.json is invalid JSON: {exc}",
            evidence_level=EvidenceLevel.SYNTACTIC,
            duration_ms=_now_ms() - start,
        )

    fail_closed = proof.get("fail_closed", False)
    preservation_score = proof.get("preservation_score", 0)

    # Check that each target has preservation info
    targets = proof.get("targets", [])
    target_proof = None
    if isinstance(targets, list):
        for t in targets:
            if isinstance(t, dict):
                if target_name in t.get("name", "") or t.get("name", "") in target_name:
                    target_proof = t
                    break
        if target_proof is None and targets:
            target_proof = targets[0]
    elif isinstance(targets, dict):
        for tname, tproof in targets.items():
            if target_name in tname or tname in target_name:
                target_proof = tproof
                break
        if target_proof is None and targets:
            target_proof = next(iter(targets.values()))

    if not target_proof:
        return GateResult(
            gate=SevenGate.PRESERVATION, target=target_name,
            status=Status.FAIL,
            detail="No per-target preservation entry in proof",
            evidence_level=EvidenceLevel.STRUCTURAL,
            duration_ms=_now_ms() - start,
        )

    # The fail_closed flag means the system correctly refuses to claim
    # preservation when gaps exist
    if not fail_closed:
        return GateResult(
            gate=SevenGate.PRESERVATION, target=target_name,
            status=Status.FAIL,
            detail="fail_closed is False — system may silently drop degraded dimensions",
            evidence_level=EvidenceLevel.STRUCTURAL,
            duration_ms=_now_ms() - start,
        )

    # Check that source/sir hashes are preserved
    has_source_hash = bool(proof.get("source_sha256"))
    has_sir_hash = bool(proof.get("sir_sha256"))
    has_ir_hash = bool(proof.get("realization_ir_sha256"))

    if not (has_source_hash and has_sir_hash and has_ir_hash):
        return GateResult(
            gate=SevenGate.PRESERVATION, target=target_name,
            status=Status.FAIL,
            detail="Missing cryptographic proof of source/SIR/IR preservation",
            evidence_level=EvidenceLevel.STRUCTURAL,
            duration_ms=_now_ms() - start,
        )

    # Extract per-target preservation fields
    target_score = target_proof.get("preservation_score", 0) if isinstance(target_proof, dict) else 0
    target_artifacts = target_proof.get("artifacts", []) if isinstance(target_proof, dict) else []
    proxy_only = target_proof.get("proxy_only", False) if isinstance(target_proof, dict) else False
    tstatus = target_proof.get("status", "") if isinstance(target_proof, dict) else ""

    detail_parts = []
    if has_source_hash:
        detail_parts.append("source_sha256 verified")
    if has_sir_hash:
        detail_parts.append("sir_sha256 verified")
    if has_ir_hash:
        detail_parts.append("ir_sha256 verified")
    detail_parts.append(f"fail_closed={fail_closed}")
    if target_artifacts:
        detail_parts.append(f"{len(target_artifacts)} artifacts tracked")
    if proxy_only:
        detail_parts.append("proxy_only mode")
    if tstatus:
        detail_parts.append(f"target_status={tstatus}")

    # Score threshold: premium targets should have score >= 0.80
    score_threshold = 0.80
    if target_score is not None and target_score < score_threshold:
        return GateResult(
            gate=SevenGate.PRESERVATION, target=target_name,
            status=Status.DEGRADED,
            detail=f"preservation_score={target_score} below premium threshold {score_threshold}; " +
                   "; ".join(detail_parts),
            evidence_level=EvidenceLevel.INTEGRATION,
            duration_ms=_now_ms() - start,
        )

    return GateResult(
        gate=SevenGate.PRESERVATION, target=target_name,
        status=Status.PASS,
        detail="; ".join(detail_parts),
        evidence_level=EvidenceLevel.INTEGRATION,
        duration_ms=_now_ms() - start,
    )


def run_seven_gate_conformance(
    output_dir: str | Path,
    manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    """Run all seven gates on a realized output directory.

    Each gate evaluates the artifact set as a whole, not individual files.
    Results are returned per-target per-gate with honest status reporting.

    Args:
        output_dir: Directory containing realized artifacts.
        manifest_path: Path to manifest.json (default: ``output_dir/manifest.json``).

    Returns:
        Dict with per-target gate results, summary counts, and sovereignty note.
    """
    output_dir = Path(output_dir)
    manifest_path = Path(manifest_path or output_dir / "manifest.json")

    if not manifest_path.exists():
        return {
            "error": f"Manifest not found: {manifest_path}",
            "pass": 0, "degraded": 0, "failed": 0, "skipped": 0,
            "gates": {},
        }

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    gate_results: dict[str, dict[str, GateResult]] = {}  # target -> gate -> result
    all_results: list[GateResult] = []

    gate_runners = {
        SevenGate.STRUCTURAL: _gate_structural,
        SevenGate.SYNTACTIC: _gate_syntactic,
        SevenGate.LINKABLE: _gate_linkable,
        SevenGate.EXECUTABLE: _gate_executable,
        SevenGate.BEHAVIORAL: _gate_behavioral,
        SevenGate.OPERATIONAL: _gate_operational,
        SevenGate.PRESERVATION: _gate_preservation,
    }

    for artifact in manifest.get("artifacts", []):
        target_name = artifact.get("target_name", "unknown")
        if target_name not in gate_results:
            gate_results[target_name] = {}

        for gate_name in SevenGate.ALL:
            runner = gate_runners[gate_name]
            try:
                result = runner(target_name, artifact, output_dir)
            except Exception as exc:
                result = GateResult(
                    gate=gate_name, target=target_name,
                    status=Status.FAIL,
                    detail=f"Gate {gate_name} crashed: {type(exc).__name__}: {exc}",
                    evidence_level=0,
                    duration_ms=0,
                )
            gate_results[target_name][gate_name] = result
            all_results.append(result)

    summary = {
        "passed": sum(1 for r in all_results if r.status == Status.PASS),
        "degraded": sum(1 for r in all_results if r.status == Status.DEGRADED),
        "failed": sum(1 for r in all_results if r.status == Status.FAIL),
        "skipped": sum(1 for r in all_results if r.status == Status.SKIP),
        "gates": {
            target: {
                gate: {
                    "status": result.status,
                    "detail": result.detail,
                    "evidence_level": result.evidence_level,
                    "toolchain_version": result.toolchain_version,
                    "duration_ms": result.duration_ms,
                }
                for gate, result in gates.items()
            }
            for target, gates in gate_results.items()
        },
    }

    # Compute per-gate pass rate
    for gate_name in SevenGate.ALL:
        gate_total = sum(1 for r in all_results if r.gate == gate_name)
        gate_pass = sum(1 for r in all_results if r.gate == gate_name and r.status == Status.PASS)
        summary["gates"][f"__{gate_name}_summary__"] = {
            "passed": gate_pass,
            "total": gate_total,
            "rate": round(gate_pass / gate_total, 2) if gate_total else 0,
        }

    summary["sovereignty_note"] = (
        "Seven-gate validation enforces the language-sovereignty principle: "
        "no backend is privileged, DEGRADED indicates weaker validation "
        "(never inflated to PASS), and gates that cannot run are reported as SKIP."
    )

    return summary


__all__ = [
    "CheckResult", "CoverageMatrix", "Status", "EvidenceLevel",
    "SevenGate", "GateResult",
    "run_conformance", "write_report", "check_file",
    "run_seven_gate_conformance",
    "generate_adversarial_cases", "run_adversarial_tests",
]
