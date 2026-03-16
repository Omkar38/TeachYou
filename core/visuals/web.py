from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional

import httpx

try:
    # Optional dependency (preferred) for DuckDuckGo image search.
    from duckduckgo_search import DDGS  # type: ignore
except Exception:  # pragma: no cover
    DDGS = None


_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36"


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _download(url: str, out_path: Path, timeout: int = 20) -> Optional[str]:
    try:
        with httpx.Client(headers={"User-Agent": _UA}, timeout=timeout, follow_redirects=True) as client:
            r = client.get(url)
            r.raise_for_status()
            out_path.write_bytes(r.content)
        return str(out_path)
    except Exception:
        return None


def search_duckduckgo_images(query: str, limit: int = 5) -> List[str]:
    """Return a list of image URLs (best-effort).

    Uses duckduckgo_search when available; otherwise returns an empty list.
    """

    if DDGS is None:
        return []

    urls: List[str] = []
    try:
        with DDGS() as ddgs:
            for r in ddgs.images(query, max_results=limit):
                # duckduckgo_search returns keys like: image, thumbnail, title, url, source
                img = r.get("image")
                if img and isinstance(img, str):
                    urls.append(img)
    except Exception:
        return []

    # Dedup while preserving order
    seen = set()
    out: List[str] = []
    for u in urls:
        if u in seen:
            continue
        seen.add(u)
        out.append(u)
    return out


def download_first_web_image(
    queries: Iterable[str],
    out_dir: str,
    limit_per_query: int = 5,
) -> Optional[str]:
    """Download a single "best effort" image from the open web via DuckDuckGo.

    Returns a local file path on success.
    """

    out = Path(out_dir)
    _ensure_dir(out)

    for q in queries:
        urls = search_duckduckgo_images(q, limit=limit_per_query)
        for i, url in enumerate(urls):
            ext = Path(url.split("?")[0]).suffix.lower()
            if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
                ext = ".jpg"
            dst = out / f"web_{abs(hash((q, url))) % 10**10}_{i:02d}{ext}"
            saved = _download(url, dst)
            if saved:
                return saved

    return None
