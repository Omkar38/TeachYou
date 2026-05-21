from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any

_WORDS_PER_LINE = 8

# ASS color format: &H<AA><BB><GG><RR>  (alpha, blue, green, red)
# white = &H00FFFFFF,  black = &H00000000,  yellow (BGR) = &H0000FFFF
_STYLE_MAP: dict[str, str] = {
    "minimal": (
        "FontName=Arial,FontSize=20,"
        "PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,"
        "Bold=0,Outline=1,Shadow=1,Alignment=2,MarginV=24"
    ),
    "big_bold": (
        "FontName=Arial,FontSize=42,"
        "PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,"
        "Bold=1,Outline=3,Shadow=1,Alignment=2,MarginV=48"
    ),
    "karaoke": (
        "FontName=Arial,FontSize=42,"
        "PrimaryColour=&H0000FFFF,OutlineColour=&H00000000,"
        "Bold=1,Outline=3,Shadow=1,Alignment=2,MarginV=48"
    ),
}


def _ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def script_to_srt_block(
    script: str,
    duration_sec: float,
    start_sec: float = 0.0,
    entry_idx: int = 1,
) -> tuple[str, int]:
    """Convert a single script to SRT entries distributed across duration_sec.

    Returns (srt_text, next_entry_idx).
    Words are grouped into ~_WORDS_PER_LINE-word lines with evenly spread timing.
    """
    words = script.split()
    if not words:
        return "", entry_idx

    # Chunk words into caption lines
    chunks: list[str] = []
    i = 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + _WORDS_PER_LINE]))
        i += _WORDS_PER_LINE

    n = len(chunks)
    spf = duration_sec / n  # seconds per frame

    lines: list[str] = []
    for j, chunk in enumerate(chunks):
        t0 = start_sec + j * spf
        t1 = start_sec + (j + 1) * spf
        lines.append(f"{entry_idx + j}\n{_ts(t0)} --> {_ts(t1)}\n{chunk}\n")

    return "\n".join(lines), entry_idx + n


def build_job_srt(segments: list[dict[str, Any]], out_srt: str) -> str:
    """Build a unified SRT for an entire job from segment metadata dicts.

    Each dict should have: script (str), duration_sec (float).
    Falls back to 'title' if script is empty.
    """
    out_p = Path(out_srt)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    parts: list[str] = []
    cursor = 0.0
    entry = 1
    for seg in segments:
        dur = float(seg.get("duration_sec") or seg.get("duration_target_sec") or 12.0)
        script = str(seg.get("script") or seg.get("title") or "").strip()
        if script:
            block, entry = script_to_srt_block(script, dur, start_sec=cursor, entry_idx=entry)
            parts.append(block)
        cursor += dur

    out_p.write_text("\n".join(p for p in parts if p), encoding="utf-8")
    return str(out_p)


def burn_captions(
    mp4_in: str,
    srt_path: str,
    mp4_out: str,
    *,
    style: str = "minimal",
    ffmpeg_path: str = "ffmpeg",
) -> str:
    """Burn SRT subtitles into a video using FFmpeg subtitles filter.

    Returns mp4_out path. Raises RuntimeError on failure.
    """
    ffmpeg = shutil.which(ffmpeg_path) or ffmpeg_path
    force_style = _STYLE_MAP.get(style, _STYLE_MAP["minimal"])

    # The subtitles filter needs the path with colons escaped (especially on Windows).
    # On POSIX, resolve to absolute and escape colons.
    srt_abs = str(Path(srt_path).resolve())
    srt_escaped = srt_abs.replace("\\", "/").replace(":", "\\:")

    vf = f"subtitles='{srt_escaped}':force_style='{force_style}'"
    cmd = [ffmpeg, "-y", "-i", mp4_in, "-vf", vf, "-c:a", "copy", mp4_out]

    p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        tail = (p.stderr or "")[-3000:].strip()
        raise RuntimeError(f"caption burn failed (exit {p.returncode}): {tail}")
    return mp4_out
