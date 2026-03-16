from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from core.tts.base import TTSProvider, TTSConfig


class ESpeakTTS(TTSProvider):
    """Offline TTS using espeak-ng/espeak.

    Produces MP3 (via ffmpeg) by default.
    """

    name = "espeak"

    def __init__(self) -> None:
        self.espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
        self.ffmpeg_bin = shutil.which("ffmpeg")
        if not self.espeak_bin:
            raise RuntimeError(
                "espeak-ng/espeak not found. Install it (Dockerfiles include it in v1)."
            )
        if not self.ffmpeg_bin:
            raise RuntimeError("ffmpeg not found. Install it (Dockerfiles include it in v1).")

    def synthesize_to_file(self, text: str, out_path: str, cfg: TTSConfig | None = None) -> str:
        cfg = cfg or TTSConfig()
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)

        # Write text to temp file to avoid shell quoting limits.
        with tempfile.TemporaryDirectory() as td:
            txt = os.path.join(td, "input.txt")
            wav = os.path.join(td, "out.wav")
            with open(txt, "w", encoding="utf-8") as f:
                f.write(text)

            cmd = [
                self.espeak_bin,
                "-v",
                cfg.voice,
                "-s",
                str(cfg.rate),
                "-a",
                str(cfg.volume),
                "-f",
                txt,
                "-w",
                wav,
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Convert to mp3 if requested
            ext = os.path.splitext(out_path)[1].lower()
            if ext not in (".mp3", ".wav"):
                # default to mp3
                out_path = out_path + ".mp3"
                ext = ".mp3"

            if ext == ".wav":
                shutil.copyfile(wav, out_path)
                return out_path

            # MP3 via ffmpeg
            subprocess.run(
                [
                    self.ffmpeg_bin,
                    "-y",
                    "-i",
                    wav,
                    "-codec:a",
                    "libmp3lame",
                    "-qscale:a",
                    "2",
                    out_path,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return out_path
