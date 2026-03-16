from __future__ import annotations

import os


def assemble_slideshow_stub(output_path: str) -> None:
    """Create a placeholder mp4 file.

    Replace with real FFmpeg slideshow rendering.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(b"FAKE_MP4_BYTES")
