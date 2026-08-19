# Orren Phase C/D Status

## Implemented

Orren now has a deterministic Realization IR between SIR and backend emission. The IR preserves all nine dimensions per node, target declarations, capability metadata, degradation obligations, source/SIR provenance, and a canonical content hash. It is serialized into realization manifests and validated for stable ordering and unique paths.

Backend selection is capability-driven through `orren_engine/backends.py`. Native output contracts, required toolchains, supported platforms, and runtime contracts are registered data rather than inferred from fallback filenames.

The Rust native core remains the production proof backend. Generated Rust compiles with warnings denied, executes its `main` entrypoint, emits deterministic sorted records, preserves required semantic state, rejects malformed source, and carries source/SIR/IR provenance. The shared Rust core under `native_core/rust` passes unit tests.

The Tauri adapter under `native/tauri` is configured for Linux AppImage/deb and Windows MSI/NSIS targets and uses the shared Rust native core. `cargo check` passes on the Linux sandbox after installing the required GTK/WebKit development libraries.

The Android Gradle/Kotlin adapter under `native/android` contains a complete application module, manifest, Kotlin activity, deterministic realization-state contract, and release/debug configuration. Its declared platform requirements are recorded in `platforms/capabilities.json`.

## Verification

| Area | Result |
|---|---|
| Python regression suite | Passes in full. |
| Realization IR/backend tests | Pass. |
| Sovereign conformance/adversarial tests | Pass. |
| Shared Rust native core | `cargo test`: 2 passed. |
| Tauri Linux adapter | `cargo check`: passes. |
| Windows Tauri packaging | Structurally configured; not executed on Linux. |
| Android Gradle packaging | Structurally configured; `SKIP` until Gradle and Android SDK are available. |

## Explicit non-claims

Windows MSI/NSIS installers have not been built on a Windows host or Windows CI runner. Android APK/AAB artifacts have not been built because the current environment lacks Gradle and the Android SDK. The Tauri UI has not been exercised in a graphical desktop session. These are release blockers, not hidden passes.

The next production step is platform CI: Linux Tauri packaging, Windows Tauri packaging on a Windows runner, and Android Gradle debug/release builds on an Android SDK runner. Each must compile, launch or install, exercise the native realization-state contract, and publish artifact hashes before being promoted from `SKIP` to `PASS`.
