"""Platform adapter capability metadata and honest toolchain classification."""
from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class PlatformStatus:
    platform: str
    adapter: str
    required_tools: List[str]
    available_tools: List[str]
    missing_tools: List[str]

    @property
    def status(self) -> str:
        return "PASS" if not self.missing_tools else "SKIP"


def load_capabilities(path: Path | None = None) -> Dict[str, object]:
    path = path or Path(__file__).parents[1] / "platforms" / "capabilities.json"
    return json.loads(path.read_text(encoding="utf-8"))["platforms"]


def inspect_platform(platform: str, surface: str, path: Path | None = None) -> PlatformStatus:
    data = load_capabilities(path)
    entry = data[platform][surface]
    required = list(entry["toolchains"])
    available = [tool for tool in required if shutil.which(tool)]
    missing = [tool for tool in required if tool not in available]
    return PlatformStatus(platform, entry["adapter"], required, available, missing)


__all__ = ["PlatformStatus", "load_capabilities", "inspect_platform"]
