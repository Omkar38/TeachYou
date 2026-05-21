from __future__ import annotations

import subprocess
import shutil
from pathlib import Path

import httpx


def download_clip(url: str, dest_path: str, *, timeout_sec: float = 60.0) -> str:
    """Stream-download a video URL to dest_path. Returns dest_path."""
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with httpx.stream("GET", url, timeout=timeout_sec, follow_redirects=True) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_bytes(65536):
                f.write(chunk)
    return str(dest)


def fit_clip_to_frame(
    src: str,
    dst: str,
    width: int,
    height: int,
    duration_sec: float,
    audio_path: str | None = None,
    *,
    ffmpeg_path: str = "ffmpeg",
) -> str:
    """Scale + pad a clip to exactly width×height, trim to duration_sec, mux with optional audio."""
    ffmpeg = shutil.which(ffmpeg_path) or ffmpeg_path
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        "setsar=1,format=yuv420p"
    )

    if audio_path and Path(audio_path).exists():
        cmd = [
            ffmpeg, "-y",
            "-i", src,
            "-i", audio_path,
            "-t", f"{duration_sec:.3f}",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            dst,
        ]
    else:
        cmd = [
            ffmpeg, "-y",
            "-i", src,
            "-t", f"{duration_sec:.3f}",
            "-vf", vf,
            "-c:v", "libx264", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            dst,
        ]

    p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        tail = (p.stderr or "")[-2000:].strip()
        raise RuntimeError(f"fit_clip_to_frame failed: {tail}")
    return dst
