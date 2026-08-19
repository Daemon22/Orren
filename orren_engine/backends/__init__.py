"""Capability-driven realization backend registry.

Backend selection is data-driven: language labels map to a backend specification,
while semantic target capabilities remain in the Realization IR. A backend may
accept a target only when its required capabilities are available or explicitly
bridged.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

from .manifest import BackendManifest, manifest_for_language, ALL_MANIFESTS


@dataclass(frozen=True)
class BackendSpec:
    key: str
    languages: Tuple[str, ...]
    native_files: Tuple[Tuple[str, str], ...]
    toolchains: Tuple[str, ...]
    platforms: Tuple[str, ...]
    capabilities: Tuple[str, ...]
    runtime_contract: str

    def supports_language(self, language: str) -> bool:
        normalized = language.lower().strip()
        if normalized in self.languages:
            return True
        # Only multi-word display labels may use substring matching. Short
        # labels such as `c` must never match `typescript`.
        return any(item in {"webaudio", "latex"} and item in normalized for item in self.languages)

    def supports_capabilities(self, requested: Iterable[str]) -> bool:
        available = set(self.capabilities)
        return set(requested).issubset(available)


_BACKENDS = (
    BackendSpec("rust", ("rust",), (("main.rs", "rust"),), ("rustc",), ("linux", "windows", "android"), ("memory_safety", "deterministic_runtime"), "executable-main-v1"),
    BackendSpec("go", ("go",), (("main.go", "go"),), ("go",), ("linux", "windows"), ("concurrency",), "executable-main-v1"),
    BackendSpec("c", ("c", "c++"), (("main.c", "c"),), ("gcc", "clang"), ("linux", "windows", "android"), ("native_memory",), "executable-main-v1"),
    BackendSpec("typescript", ("typescript",), (("app.ts", "typescript"),), ("tsc",), ("linux", "windows", "android"), ("typed_web_runtime",), "module-v1"),
    BackendSpec("webaudio", ("webaudio",), (("audio_engine.js", "webaudio"),), ("node",), ("linux", "windows", "android"), ("audio_context",), "browser-audio-v1"),
    BackendSpec("latex", ("latex", "tex"), (("document.tex", "latex"),), ("pdflatex", "latex"), ("linux", "windows"), ("document_rendering",), "document-v1"),
    BackendSpec("swift", ("swift",), (("Main.swift", "swift"),), ("swiftc",), ("linux", "windows"), ("native_ui",), "executable-main-v1"),
    BackendSpec("kotlin", ("kotlin",), (("Main.kt", "kotlin"),), ("kotlinc",), ("linux", "windows", "android"), ("managed_runtime",), "executable-main-v1"),
    BackendSpec("python", ("python",), (("service.py", "python"),), ("python3",), ("linux", "windows", "android"), ("dynamic_runtime",), "process-dict-v1"),
)

BACKENDS: Dict[str, BackendSpec] = {spec.key: spec for spec in _BACKENDS}


def backend_for_language(language: str) -> BackendSpec | None:
    normalized = language.lower().strip()
    for spec in BACKENDS.values():
        if spec.supports_language(normalized):
            return spec
    return None


def backend_for_target(language: str, capabilities: Iterable[str] = ()) -> BackendSpec:
    spec = backend_for_language(language)
    if spec is None:
        raise ValueError(f"no registered backend for language {language!r}")
    missing = sorted(set(capabilities) - set(spec.capabilities))
    if missing:
        raise ValueError(f"backend {spec.key} cannot satisfy capabilities: {', '.join(missing)}")
    return spec


__all__ = ["BackendSpec", "BACKENDS", "backend_for_language", "backend_for_target",
           "BackendManifest", "manifest_for_language", "ALL_MANIFESTS"]
