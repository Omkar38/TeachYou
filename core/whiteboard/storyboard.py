from __future__ import annotations

import re
from typing import List

from core.utils.text import extractive_summary


def _clean_sent(s: str) -> str:
    s = re.sub(r"\s+", " ", s.strip())
    s = s.strip("-•* \t")
    return s


def bullets_from_script(script: str, max_bullets: int = 4) -> List[str]:
    """Extract short bullet points from narration.

    We keep this offline, deterministic, and fast.
    """
    if not script:
        return []

    # Prefer the first few extractive-summary sentences.
    summ = extractive_summary(script, max_sentences=max(6, max_bullets + 2))
    sents = [
        _clean_sent(x)
        for x in re.split(r"(?<=[.!?])\s+", summ)
        if _clean_sent(x)
    ]

    bullets: List[str] = []
    for s in sents:
        if len(s) < 10:
            continue
        # Keep bullets compact for the whiteboard.
        if len(s) > 110:
            s = s[:107].rstrip() + "…"
        bullets.append(s)
        if len(bullets) >= max_bullets:
            break

    if not bullets:
        t = _clean_sent(script)
        if len(t) > 110:
            t = t[:107].rstrip() + "…"
        bullets = [t]

    return bullets


def estimate_duration_sec(script: str, *, wpm: int = 150, min_sec: float = 8.0, max_sec: float = 45.0) -> float:
    """Fallback duration estimate from text length."""
    words = len((script or "").split())
    sec = (words / max(1, wpm)) * 60.0
    return float(max(min_sec, min(max_sec, sec)))
