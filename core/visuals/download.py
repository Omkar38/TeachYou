from __future__ import annotations

import hashlib
import os
import time
import urllib.request
from pathlib import Path
from typing import Optional, Tuple


DEFAULT_UA = "genai-explainer/0.1 (+https://example.invalid)"


def _guess_ext(url: str, content_type: Optional[str]) -> str:
    u = (url or "").lower()
    if u.endswith(".png"):
        return ".png"
    if u.endswith(".jpg") or u.endswith(".jpeg"):
        return ".jpg"
    if u.endswith(".webp"):
        return ".webp"
    if content_type:
        ct = content_type.lower()
        if "png" in ct:
            return ".png"
        if "jpeg" in ct or "jpg" in ct:
            return ".jpg"
        if "webp" in ct:
            return ".webp"
    return ".jpg"


def download_to_cache(
    url: str,
    cache_dir: str,
    *,
    timeout_sec: float = 12.0,
    user_agent: str = DEFAULT_UA,
    max_bytes: int = 8_000_000,
) -> Tuple[str, str]:
    """Download a URL into a deterministic cache location.

    Returns (local_path, sha256_hex).

    - Uses sha256(url) to name the file.
    - Enforces a simple max_bytes cap to avoid huge downloads.
    - If the file already exists, returns it without re-downloading.
    """
    Path(cache_dir).mkdir(parents=True, exist_ok=True)

    url_b = url.encode("utf-8", errors="ignore")
    key = hashlib.sha256(url_b).hexdigest()
    # We don't know the extension until we see headers; try common ones first.
    for ext in (".jpg", ".png", ".webp"):
        p = Path(cache_dir) / f"{key}{ext}"
        if p.exists() and p.stat().st_size > 0:
            return str(p), key

    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        ct = resp.headers.get("Content-Type")
        ext = _guess_ext(url, ct)
        out = Path(cache_dir) / f"{key}{ext}"
        if out.exists() and out.stat().st_size > 0:
            return str(out), key

        tmp = Path(cache_dir) / f".{key}.partial"
        written = 0
        with open(tmp, "wb") as f:
            while True:
                chunk = resp.read(64 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > max_bytes:
                    raise RuntimeError(f"Image too large (> {max_bytes} bytes): {url}")
                f.write(chunk)
        os.replace(tmp, out)
        # Make it obvious these are cache artifacts
        try:
            os.utime(out, (time.time(), time.time()))
        except Exception:
            pass

    return str(out), key
