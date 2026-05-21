from __future__ import annotations

from typing import Optional

import httpx

from core.storyboard.schema import MediaCandidate

_PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
_PIXABAY_VIDEO_URL = "https://pixabay.com/api/videos/"

_PEXELS_ORIENTATION = {"9:16": "portrait", "16:9": "landscape", "1:1": "square"}
_PIXABAY_ORIENTATION = {"9:16": "vertical", "16:9": "horizontal", "1:1": "horizontal"}


def _pick_pexels_file(files: list[dict], orientation: str) -> Optional[dict]:
    """Choose the best video file from a Pexels video object."""
    if not files:
        return None
    portrait = orientation == "9:16"
    # Filter by rough shape match, prefer hd
    shaped = [f for f in files if f.get("file_type") == "video/mp4" and (
        (portrait and int(f.get("height") or 0) >= int(f.get("width") or 1)) or
        (not portrait and int(f.get("width") or 0) >= int(f.get("height") or 1))
    )]
    pool = shaped or [f for f in files if f.get("file_type") == "video/mp4"]
    if not pool:
        return None
    hd = [f for f in pool if f.get("quality") == "hd"]
    return (hd or pool)[0]


def search_pexels(
    query: str,
    aspect_ratio: str = "9:16",
    api_key: str = "",
    limit: int = 5,
) -> list[MediaCandidate]:
    if not api_key:
        return []
    orientation = _PEXELS_ORIENTATION.get(aspect_ratio, "portrait")
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(
                _PEXELS_VIDEO_URL,
                headers={"Authorization": api_key},
                params={"query": query, "per_page": limit, "orientation": orientation},
            )
            r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    out: list[MediaCandidate] = []
    for v in data.get("videos") or []:
        f = _pick_pexels_file(v.get("video_files") or [], aspect_ratio)
        if not f:
            continue
        out.append(MediaCandidate(
            source="pexels",
            url=str(f.get("link") or ""),
            thumb_url=str(v.get("image") or ""),
            duration_s=float(v.get("duration") or 0),
            width=int(f.get("width") or 0),
            height=int(f.get("height") or 0),
        ))
    return out


def search_pixabay(
    query: str,
    aspect_ratio: str = "9:16",
    api_key: str = "",
    limit: int = 5,
) -> list[MediaCandidate]:
    if not api_key:
        return []
    orientation = _PIXABAY_ORIENTATION.get(aspect_ratio, "vertical")
    try:
        with httpx.Client(timeout=15.0) as client:
            r = client.get(
                _PIXABAY_VIDEO_URL,
                params={
                    "key": api_key,
                    "q": query,
                    "per_page": limit,
                    "video_type": "film",
                    "orientation": orientation,
                },
            )
            r.raise_for_status()
        data = r.json()
    except Exception:
        return []

    out: list[MediaCandidate] = []
    for hit in data.get("hits") or []:
        videos = hit.get("videos") or {}
        chosen = None
        for quality in ("large", "medium", "small"):
            v = videos.get(quality)
            if v and v.get("url"):
                chosen = v
                break
        if not chosen:
            continue
        out.append(MediaCandidate(
            source="pixabay",
            url=str(chosen["url"]),
            thumb_url=str(hit.get("userImageURL") or ""),
            duration_s=float(hit.get("duration") or 0),
            width=int(chosen.get("width") or 0),
            height=int(chosen.get("height") or 0),
        ))
    return out


def search_broll(
    query: str,
    aspect_ratio: str = "9:16",
    *,
    pexels_key: str = "",
    pixabay_key: str = "",
    limit: int = 5,
) -> list[MediaCandidate]:
    """Search Pexels then Pixabay; combine up to `limit` results."""
    results: list[MediaCandidate] = []
    if pexels_key:
        results.extend(search_pexels(query, aspect_ratio, pexels_key, limit))
    if pixabay_key and len(results) < limit:
        results.extend(search_pixabay(query, aspect_ratio, pixabay_key, limit - len(results)))
    return results[:limit]
