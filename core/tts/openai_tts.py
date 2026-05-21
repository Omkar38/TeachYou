from __future__ import annotations

from pathlib import Path

import httpx

from apps.api.settings import settings
from core.tts.base import TTSConfig, TTSProvider


class OpenAITTS(TTSProvider):
    """OpenAI Text-to-Speech provider.

    Notes:
      - Requires OPENAI_API_KEY.
      - Outputs MP3.
    """

    name = "openai"

    def synthesize_to_file(self, text: str, out_path: str, cfg: TTSConfig | None = None) -> str:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY missing")

        cfg = cfg or TTSConfig()
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.openai_tts_model,
            "voice": settings.openai_tts_voice,
            "format": "mp3",
            "input": text,
        }

        timeout = float(getattr(settings, "tts_timeout_sec", 60.0))
        with httpx.Client(timeout=timeout) as client:
            r = client.post(url, headers=headers, json=payload)
            r.raise_for_status()
            out.write_bytes(r.content)
        return str(out)
