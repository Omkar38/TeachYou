from __future__ import annotations

from core.tts.base import TTSConfig, TTSProvider
from core.tts.espeak import ESpeakTTS


def build_tts_chain() -> list[TTSProvider]:
    """Create TTS providers in the desired fallback order.

    Order is configured via settings.tts_provider_order.
    Default: openai,google,espeak
    """
    from apps.api.settings import settings

    order = [p.strip().lower() for p in (settings.tts_provider_order or "").split(",") if p.strip()]
    if not order:
        order = ["openai", "google", "espeak"]

    providers: list[TTSProvider] = []
    for p in order:
        if p == "openai":
            try:
                from core.tts.openai_tts import OpenAITTS
                providers.append(OpenAITTS())
            except Exception:
                continue
        elif p == "google":
            try:
                from core.tts.google_tts import GoogleCloudTTS
                providers.append(GoogleCloudTTS())
            except Exception:
                continue
        elif p == "espeak":
            providers.append(ESpeakTTS())
        else:
            # ignore unknown
            continue

    # Always ensure we have at least one offline fallback.
    if not any(getattr(x, "name", "") == "espeak" for x in providers):
        providers.append(ESpeakTTS())

    return providers


def synthesize_with_fallback(text: str, out_path: str, cfg: TTSConfig | None = None) -> tuple[str, str]:
    """Synthesize using the configured chain.

    Returns: (audio_path, provider_name)
    """
    last_err: Exception | None = None
    for provider in build_tts_chain():
        try:
            return provider.synthesize_to_file(text, out_path, cfg=cfg), provider.name
        except Exception as e:
            last_err = e
            continue
    raise RuntimeError(f"All TTS providers failed. Last error: {last_err}")
