from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Dict, List, Optional


def _format_ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def write_srt(segments: List[Dict], out_srt: str) -> str:
    out = Path(out_srt)
    out.parent.mkdir(parents=True, exist_ok=True)

    t = 0.0
    lines: List[str] = []
    for i, seg in enumerate(segments, start=1):
        dur = float(seg.get("duration_target_sec", 60.0))
        if dur <= 0:
            dur = 1.0
        start = _format_ts(t)
        end = _format_ts(t + dur)
        title = seg.get("title", f"Segment {i}")

        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(title)
        lines.append("")
        t += dur

    out.write_text("\n".join(lines), encoding="utf-8")
    return str(out)


def _run(cmd: List[str]) -> None:
    # Capture stderr so failures inside Celery show the real ffmpeg error (not just exit code 254)
    p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        tail = (p.stderr or "").strip()
        if len(tail) > 4000:
            tail = tail[-4000:]
        raise RuntimeError(f"Command failed (exit={p.returncode}): {cmd}\n\nffmpeg stderr (tail):\n{tail}")


def _ffprobe_duration(path: str, ffprobe_path: str = "ffprobe") -> Optional[float]:
    try:
        out = subprocess.check_output(
            [
                ffprobe_path,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                path,
            ],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="ignore").strip()
        return float(out) if out else None
    except Exception:
        return None


def _concat_list_line(p: Path) -> str:
    # IMPORTANT:
    # ffmpeg concat demuxer resolves relative paths relative to the concat file's directory.
    # Since concat.txt is written inside tmp_video/ (same directory as the clips),
    # write only the basename to avoid duplicated paths like:
    # tmp_video/data/outputs/.../tmp_video/clip_000.mp4
    s = str(p.name).replace("'", "'\\''")
    return f"file '{s}'"


def build_slideshow(
    segments: List[Dict],
    out_video: str,
    out_dir: str,
    narration_mp3: str,
    ffmpeg_path: str = "ffmpeg",
    ffprobe_path: str = "ffprobe",
    width: int = 1280,
    height: int = 720,
    fps: int = 25,
) -> str:
    out_dir_p = Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)

    tmp = out_dir_p / "tmp_video"
    tmp.mkdir(parents=True, exist_ok=True)

    clip_paths: List[Path] = []

    narration_dur = None
    if narration_mp3 and Path(narration_mp3).exists():
        narration_dur = _ffprobe_duration(narration_mp3, ffprobe_path=ffprobe_path)

    for idx, seg in enumerate(segments):
        dur = float(seg.get("duration_target_sec", 60.0))
        if dur <= 0:
            dur = 1.0

        visuals = seg.get("visuals") or []
        img_path: Optional[Path] = None
        if visuals:
            try:
                img_path = Path(visuals[0]["path"]).expanduser()
            except Exception:
                img_path = None

        clip = tmp / f"clip_{idx:03d}.mp4"

        if img_path is None or not img_path.exists():
            _run(
                [
                    ffmpeg_path,
                    "-y",
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c=white:s={width}x{height}:r={fps}:d={dur}",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(clip),
                ]
            )
        else:
            vf = (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
                "format=yuv420p"
            )
            _run(
                [
                    ffmpeg_path,
                    "-y",
                    "-loop",
                    "1",
                    "-t",
                    f"{dur}",
                    "-i",
                    str(img_path),
                    "-r",
                    str(fps),
                    "-vf",
                    vf,
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    str(clip),
                ]
            )

        clip_paths.append(clip)

    concat_list = tmp / "concat.txt"
    concat_list.write_text(
        "\n".join(_concat_list_line(p) for p in clip_paths) + "\n",
        encoding="utf-8",
    )

    video_no_audio = out_dir_p / "slideshow_no_audio.mp4"

    # First try stream copy (fast). If that fails (codec/container mismatch), fall back to re-encode.
    try:
        _run(
            [
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
                str(video_no_audio),
            ]
        )
    except RuntimeError:
        _run(
            [
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
                str(video_no_audio),
            ]
        )

    out_video_p = Path(out_video)
    out_video_p.parent.mkdir(parents=True, exist_ok=True)

    if not narration_mp3 or not Path(narration_mp3).exists():
        out_video_p.write_bytes(video_no_audio.read_bytes())
        return str(out_video_p)

    _run(
        [
            ffmpeg_path,
            "-y",
            "-i",
            str(video_no_audio),
            "-i",
            narration_mp3,
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(out_video_p),
        ]
    )

    if narration_dur is not None and narration_dur > 0:
        trimmed = out_dir_p / "explainer_trimmed.mp4"
        _run(
            [
                ffmpeg_path,
                "-y",
                "-i",
                str(out_video_p),
                "-t",
                f"{narration_dur:.3f}",
                "-c",
                "copy",
                str(trimmed),
            ]
        )
        out_video_p.write_bytes(trimmed.read_bytes())

    return str(out_video_p)
