from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def _run(cmd: list[str]) -> None:
    p = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0:
        tail = (p.stderr or "").strip()
        if len(tail) > 4000:
            tail = tail[-4000:]
        raise RuntimeError(f"Command failed (exit={p.returncode}): {cmd}\n\nffmpeg stderr (tail):\n{tail}")


def render_html_to_mp4(
    html_path: str,
    out_mp4: str,
    *,
    duration_sec: float,
    width: int = 1280,
    height: int = 720,
    fps: int = 30,
    audio_path: str | None = None,
    ffmpeg_path: str = "ffmpeg",
) -> str:
    """Render a self-contained HTML scene to an MP4.

    Uses Playwright to record video (webm) then converts/muxes with ffmpeg.
    """
    html_p = Path(html_path)
    if not html_p.exists():
        raise FileNotFoundError(html_path)

    out_p = Path(out_mp4)
    out_p.parent.mkdir(parents=True, exist_ok=True)

    tmp = out_p.parent / "_pw_tmp"
    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True, exist_ok=True)

    # Lazy import so API container doesn't need playwright.
    from playwright.sync_api import sync_playwright

    webm_path: Path | None = None
    with sync_playwright() as p:
        browser = p.chromium.launch(
            args=["--no-sandbox", "--disable-dev-shm-usage"],
            headless=True,
        )
        context = browser.new_context(
            viewport={"width": width, "height": height},
            record_video_dir=str(tmp),
            record_video_size={"width": width, "height": height},
        )
        page = context.new_page()
        page.goto(html_p.resolve().as_uri())
        # give browser a tick to paint
        page.wait_for_timeout(200)

        # record for requested duration
        page.wait_for_timeout(int(max(0.5, duration_sec) * 1000))

        video = page.video
        page.close()
        context.close()
        browser.close()
        if video:
            webm_path = Path(video.path())

    if not webm_path or not webm_path.exists():
        raise RuntimeError("Playwright did not produce a video file")

    # Convert to mp4 and optionally mux audio.
    if audio_path and Path(audio_path).exists():
        _run([
            ffmpeg_path,
            "-y",
            "-i",
            str(webm_path),
            "-i",
            str(audio_path),
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-shortest",
            str(out_p),
        ])
    else:
        _run([
            ffmpeg_path,
            "-y",
            "-i",
            str(webm_path),
            "-r",
            str(fps),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            str(out_p),
        ])

    # Clean temp
    try:
        shutil.rmtree(tmp, ignore_errors=True)
    except Exception:
        pass

    return str(out_p)
