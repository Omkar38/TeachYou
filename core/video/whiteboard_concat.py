from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List


def _run(cmd: List[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        tail = (p.stderr or "").strip()
        if len(tail) > 4000:
            tail = tail[-4000:]
        raise RuntimeError(f"Command failed (exit={p.returncode}): {cmd}\n\nffmpeg stderr (tail):\n{tail}")


def concat_mp4_clips(clips: List[str], out_mp4: str, *, ffmpeg_path: str = "ffmpeg") -> str:
    """Concatenate MP4 clips (same resolution/codec) into a single MP4."""
    if not clips:
        raise ValueError("No clips to concatenate")

    out_p = Path(out_mp4)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    tmp_dir = out_p.parent / "tmp_concat"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    concat_list = tmp_dir / "concat.txt"

    lines = []
    for c in clips:
        p = Path(c)
        if not p.exists():
            raise FileNotFoundError(c)
        # Use absolute paths with -safe 0
        s = str(p.resolve()).replace("'", "'\\''")
        lines.append(f"file '{s}'")
    concat_list.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Try stream copy first; fall back to re-encode if needed.
    try:
        _run([
            ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c",
            "copy",
            str(out_p),
        ])
    except RuntimeError:
        _run([
            ffmpeg_path,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(out_p),
        ])

    return str(out_p)
