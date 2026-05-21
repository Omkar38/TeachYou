from __future__ import annotations

import urllib.parse
from typing import List, Dict


def youtube_search_links(phrases: List[str], max_links: int = 3) -> List[Dict[str, str]]:
    """
    Offline: produce YouTube search URLs (no crawling).
    """
    links = []
    for ph in phrases[:max_links]:
        q = urllib.parse.quote_plus(ph + " explained")
        links.append(
            {
                "title": f"YouTube: {ph} explained",
                "url": f"https://www.youtube.com/results?search_query={q}",
                "why": "Optional deeper background",
            }
        )
    return links
