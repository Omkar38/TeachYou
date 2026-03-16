from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TTSConfig:
    voice: str = "en-us"
    rate: int = 170
    volume: int = 100


class TTSProvider:
    """Minimal TTS provider interface."""

    name: str = "base"

    def synthesize_to_file(self, text: str, out_path: str, cfg: TTSConfig | None = None) -> str:
        raise NotImplementedError


def get_default_tts_provider() -> TTSProvider:
    """Offline-first default: espeak/espeak-ng.

    This keeps the MVP runnable without paid APIs.
    """

    from core.tts.espeak import ESpeakTTS

    return ESpeakTTS()
