"""Orren-generated audio storage service.
Target: audio_storage (Python)

Scoped responsibility: cognitive.preservation (retain original_audio).
HARD CONTRACT: original_audio is retained unconditionally,
even if storage is constrained or transcription succeeds.
"""

from __future__ import annotations

import os
import hashlib
import time


class AudioStorage:
    def __init__(self, root_dir: str = "/var/orren/audio"):
        self.root_dir = root_dir
        os.makedirs(root_dir, exist_ok=True)

    def retain(self, audio_bytes: bytes, recording_id: str | None = None) -> str:
        """Retain original audio. This is an unconditional contract."""
        if recording_id is None:
            recording_id = hashlib.sha256(audio_bytes).hexdigest()[:16]
        path = os.path.join(self.root_dir, f"{recording_id}.bin")
        with open(path, "wb") as f:
            f.write(audio_bytes)
        # Write a sidecar manifest recording the preservation contract.
        manifest = {
            "recording_id": recording_id,
            "retained_at": time.time(),
            "bytes": len(audio_bytes),
            "contract": "unconditional_preservation",
        }
        with open(path + ".manifest.json", "w") as f:
            import json
            json.dump(manifest, f)
        return path

    def retrieve(self, recording_id: str) -> bytes:
        path = os.path.join(self.root_dir, f"{recording_id}.bin")
        with open(path, "rb") as f:
            return f.read()
