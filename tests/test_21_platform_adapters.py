from __future__ import annotations

import json
from pathlib import Path

from orren_engine.platforms import inspect_platform, load_capabilities


REPO = Path(__file__).parents[1]


def test_platform_capability_manifest_declares_requested_surfaces():
    capabilities = load_capabilities()
    assert set(capabilities) >= {"linux", "windows", "android"}
    assert capabilities["linux"]["desktop"]["adapter"] == "tauri"
    assert capabilities["windows"]["desktop"]["adapter"] == "tauri"
    assert capabilities["android"]["mobile"]["adapter"] == "gradle-kotlin"


def test_tauri_scaffold_has_shared_core_and_platform_targets():
    assert (REPO / "native/tauri/src-tauri/Cargo.toml").exists()
    assert (REPO / "native/tauri/src-tauri/src/main.rs").exists()
    config = json.loads((REPO / "native/tauri/src-tauri/tauri.conf.json").read_text())
    assert "msi" in config["bundle"]["targets"]
    assert "appimage" in config["bundle"]["targets"]


def test_android_gradle_scaffold_has_native_contract():
    assert (REPO / "native/android/settings.gradle.kts").exists()
    assert (REPO / "native/android/app/build.gradle.kts").exists()
    activity = (REPO / "native/android/app/src/main/java/com/orren/android/MainActivity.kt").read_text()
    assert "NativeRealizationCore" in activity
    assert "toSortedMap" in activity


def test_platform_status_is_honest():
    linux = inspect_platform("linux", "desktop")
    windows = inspect_platform("windows", "desktop")
    android = inspect_platform("android", "mobile")
    assert linux.status in {"PASS", "SKIP"}
    assert windows.status in {"PASS", "SKIP"}
    assert android.status in {"PASS", "SKIP"}
    assert linux.status == ("PASS" if not linux.missing_tools else "SKIP")
