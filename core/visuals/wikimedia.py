from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.visuals.download import DEFAULT_UA, download_to_cache


DEFAULT_API = "https://commons.wikimedia.org/w/api.php"


def _http_get_json(url: str, *, timeout_sec: float = 12.0, user_agent: str = DEFAULT_UA) -> Dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        data = resp.read()
    return json.loads(data.decode("utf-8", errors="ignore"))


def search_commons_images(
    query: str,
    *,
    max_results: int = 5,
    api_url: str = DEFAULT_API,
    timeout_sec: float = 12.0,
    user_agent: str = DEFAULT_UA,
) -> List[Dict[str, Any]]:
    """Search Wikimedia Commons for images.

    Returns a list of candidates with URLs and attribution metadata.
    This uses MediaWiki's API and does not scrape pages.
    """
    q = (query or "").strip()
    if not q:
        return []

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": q,
        "gsrnamespace": "6",  # File:
        "gsrlimit": str(max_results),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": "1600",
        "iiurlheight": "1600",
    }
    url = api_url + "?" + urllib.parse.urlencode(params)

    try:
        data = _http_get_json(url, timeout_sec=timeout_sec, user_agent=user_agent)
    except Exception:
        return []

    pages = (data.get("query") or {}).get("pages") or {}
    out: List[Dict[str, Any]] = []
    for _pageid, page in pages.items():
        title = page.get("title")
        infos = page.get("imageinfo") or []
        if not infos:
            continue
        info = infos[0]
        img_url = info.get("thumburl") or info.get("url")
        if not img_url:
            continue

        md = (info.get("extmetadata") or {})

        def _md(k: str) -> Optional[str]:
            v = md.get(k) or {}
            if isinstance(v, dict):
                return v.get("value")
            if isinstance(v, str):
                return v
            return None

        # These fields often contain HTML; keep them as-is so the UI can render/strip later.
        out.append(
            {
                "title": title,
                "image_url": img_url,
                "source_url": info.get("descriptionurl"),
                "license_short": _md("LicenseShortName"),
                "license_url": _md("LicenseUrl"),
                "artist": _md("Artist"),
                "credit": _md("Credit"),
                "attribution_required": _md("AttributionRequired"),
            }
        )
    return out


def download_best_image(
    query: str,
    *,
    cache_dir: str,
    api_url: str = DEFAULT_API,
    timeout_sec: float = 12.0,
    user_agent: str = DEFAULT_UA,
) -> Optional[Dict[str, Any]]:
    """Search & download one representative image for a query.

    Returns a dict compatible with your segment-pack "visuals" entries:
    {path, caption, license, source_url, attribution{...}}.
    """
    candidates = search_commons_images(
        query,
        max_results=5,
        api_url=api_url,
        timeout_sec=timeout_sec,
        user_agent=user_agent,
    )
    if not candidates:
        return None

    # Naive: pick first candidate. Later you can score by resolution/keyword match.
    c = candidates[0]
    url = c.get("image_url")
    if not url:
        return None

    try:
        local_path, sha = download_to_cache(url, cache_dir, timeout_sec=timeout_sec, user_agent=user_agent)
    except Exception:
        return None

    # Persist attribution beside the image for auditability.
    meta_path = Path(cache_dir) / f"{sha}.meta.json"
    try:
        meta_path.write_text(json.dumps(c, indent=2), encoding="utf-8")
    except Exception:
        pass

    caption = c.get("title") or query
    return {
        "path": local_path,
        "caption": caption,
        "license": "wikimedia-commons",
        "source_url": c.get("source_url"),
        "attribution": {
            "artist": c.get("artist"),
            "license_short": c.get("license_short"),
            "license_url": c.get("license_url"),
            "credit": c.get("credit"),
        },
    }
