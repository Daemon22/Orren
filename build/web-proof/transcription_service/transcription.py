"""Orren-generated transcription service.
Target: transcription_service (Python)

Scoped responsibility: cognitive.transcription only.
All other dimensions are OUT_OF_SCOPE for this target.
"""

from __future__ import annotations


def transcribe(audio_recording: bytes) -> str:
    """Transcribe an audio recording to text.

    This function satisfies the cognitive.transcription contract.
    The original_audio is preserved upstream (cognitive.preservation).
    """
    # PROXY: actual speech-to-text backend not bundled;
    # wire this to your preferred transcription service.
    raise NotImplementedError(
        "Connect transcribe() to a speech-to-text backend."
    )


def transcribe_with_metadata(audio_recording: bytes) -> dict:
    """Transcribe and return structured metadata."""
    text = transcribe(audio_recording)
    return {
        "text": text,
        "source_preserved": True,  # cognitive.preservation is honored upstream
    }
