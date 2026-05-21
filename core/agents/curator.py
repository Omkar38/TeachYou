from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from core.visuals.wikimedia import download_best_image
from core.visuals.web import download_first_web_image


def pick_visuals(
    extracted_dir: str,
    prefer_figures: bool = True,
    max_visuals: int = 3,
    *,
    queries: Optional[List[str]] = None,
    web_provider: str = "offline",
    web_out_dir: Optional[str] = None,
    web_extra: int = 0,
) -> List[Dict[str, Any]]:
    """
    Offline visuals: pick from extracted figures first, then rendered pages.
    """
    base = Path(extracted_dir)
    figs = sorted((base / "figures").glob("*.*"))
    pages = sorted((base / "pages").glob("*.png"))

    chosen: List[Dict[str, Any]] = []
    if prefer_figures:
        for p in figs[:max_visuals]:
            chosen.append({"path": str(p), "caption": "Figure from the paper", "license": "paper-embedded"})
    while len(chosen) < max_visuals and pages:
        p = pages[len(chosen) % len(pages)]
        chosen.append({"path": str(p), "caption": "Rendered page view", "license": "paper-page"})

    # Optional: web fallback / augmentation.
    #
    # - If we have fewer than `max_visuals`, we try to fill the remaining slots.
    # - If `web_extra > 0`, we *also* try to append up to that many additional web visuals
    #   even if we already have `max_visuals` paper visuals.
    if web_provider != "offline" and queries and web_out_dir:
        web_dir = Path(web_out_dir)
        web_dir.mkdir(parents=True, exist_ok=True)

        used_paths = {v.get("path") for v in chosen if v.get("path")}

        def _try_add_web(q: str) -> bool:
            nonlocal used_paths
            q = (q or "").strip()
            if not q:
                return False

            # Provider cascade: Wikimedia -> DuckDuckGo (hybrid) / DuckDuckGo-only.
            if web_provider in {"wikimedia", "hybrid"}:
                img = download_best_image(q, cache_dir=str(web_dir))
                if img and img.get("path") and img["path"] not in used_paths:
                    used_paths.add(img["path"])
                    chosen.append(img)
                    return True

            if web_provider in {"ddg", "hybrid"}:
                path = download_first_web_image([q], out_dir=str(web_dir))
                if path and path not in used_paths:
                    used_paths.add(path)
                    chosen.append({"path": path, "caption": f"Web image: {q}", "license": "web"})
                    return True
            return False

        # (1) Fill remaining slots up to `max_visuals`.
        if len(chosen) < max_visuals:
            for q in queries:
                if len(chosen) >= max_visuals:
                    break
                _try_add_web(q)

        # (2) Augment with up to `web_extra` additional visuals.
        extra = int(web_extra or 0)
        if extra > 0:
            for q in queries:
                if extra <= 0:
                    break
                if _try_add_web(q):
                    extra -= 1
    return chosen
