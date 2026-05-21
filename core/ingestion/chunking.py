from __future__ import annotations

import re
from typing import List, Dict, Any

from core.utils.text import normalize_whitespace

_HEADING_RE = re.compile(r"^(?:\d+(\.\d+)*\s+)?[A-Z][A-Za-z0-9 ,:\-()]{3,}$")


def chunk_text(text: str, max_chars: int = 3500, min_chars: int = 800) -> List[Dict[str, Any]]:
    """
    Heuristic chunker for papers.
    Produces chunks with:
      - chunk_index
      - text
      - source_span_json: {start_char, end_char}
    """
    text = normalize_whitespace(text)
    if not text:
        return []

    lines = [ln.strip() for ln in text.split("\n")]

    blocks: List[str] = []
    cur: List[str] = []
    for ln in lines:
        if _HEADING_RE.match(ln) and len(cur) > 0:
            blocks.append("\n".join(cur).strip())
            cur = [ln]
        else:
            cur.append(ln)
    if cur:
        blocks.append("\n".join(cur).strip())

    # Merge/split blocks into size-bound chunks
    chunks: List[str] = []
    buf = ""
    for b in blocks:
        b = b.strip()
        if not b:
            continue
        if len(buf) + len(b) + 2 <= max_chars:
            buf = (buf + "\n\n" + b).strip() if buf else b
        else:
            if buf:
                chunks.append(buf)
            buf = b
    if buf:
        chunks.append(buf)

    # Further split if any chunk is too big
    final_chunks: List[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            final_chunks.append(c)
        else:
            paras = [p.strip() for p in c.split("\n\n") if p.strip()]
            tmp = ""
            for p in paras:
                if len(tmp) + len(p) + 2 <= max_chars:
                    tmp = (tmp + "\n\n" + p).strip() if tmp else p
                else:
                    if tmp:
                        final_chunks.append(tmp)
                    tmp = p
            if tmp:
                final_chunks.append(tmp)

    # Compute source spans against the original text
    out: List[Dict[str, Any]] = []
    cursor = 0
    for idx, c in enumerate(final_chunks):
        # Find next occurrence (best-effort)
        pos = text.find(c, cursor)
        if pos == -1:
            pos = cursor
        start = pos
        end = pos + len(c)
        cursor = end
        out.append(
            {
                "chunk_index": idx,
                "text": c,
                "source_span_json": {"start_char": start, "end_char": end},
            }
        )
    return out
