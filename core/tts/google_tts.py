from __future__ import annotations

from pathlib import Path

from apps.api.settings import settings
from core.tts.base import TTSConfig, TTSProvider


class GoogleCloudTTS(TTSProvider):
    """Google Cloud Text-to-Speech provider.

    Requires GOOGLE_APPLICATION_CREDENTIALS in the environment (service account json),
    or other Google auth configured inside the container.
    """

    name = "google"

    def synthesize_to_file(self, text: str, out_path: str, cfg: TTSConfig | None = None) -> str:
        try:
            from google.cloud import texttospeech  # type: ignore
        except Exception as e:
            raise RuntimeError("google-cloud-texttospeech not installed") from e

        cfg = cfg or TTSConfig()
        out = Path(out_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        client = texttospeech.TextToSpeechClient()

        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=settings.google_tts_voice_name or "en-US-Standard-C",
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=float(getattr(settings, "google_tts_speaking_rate", 1.0)),
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        out.write_bytes(response.audio_content)
        return str(out)
