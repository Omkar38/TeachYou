from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from pypdf import PdfReader

from core.ingestion.visuals import extract_images_from_pdf
from core.utils.text import normalize_whitespace


def extract_text_from_pdf(pdf_path: str, max_pages: Optional[int] = None) -> str:
    reader = PdfReader(pdf_path)
    parts: List[str] = []

    for i, page in enumerate(reader.pages):
        if max_pages is not None and i >= max_pages:
            break
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        if t:
            parts.append(t)

    return normalize_whitespace("\n\n".join(parts))


def ingest_pdf(
    pdf_path: str,
    out_dir: str,
    max_pages: Optional[int] = None,
    max_images: int = 20,
) -> Dict[str, Any]:
    out_dir_p = Path(out_dir)
    out_dir_p.mkdir(parents=True, exist_ok=True)

    figures_dir = out_dir_p / "figures"
    pages_dir = out_dir_p / "pages"
    figures_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    reader = PdfReader(pdf_path)
    pages: List[Dict[str, Any]] = []
    full_parts: List[str] = []

    for i, page in enumerate(reader.pages):
        if max_pages is not None and i >= max_pages:
            break
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        t = normalize_whitespace(t)
        pages.append({"page_index": i, "text": t})
        if t:
            full_parts.append(t)

    full_text = normalize_whitespace("\n\n".join(full_parts))
    (out_dir_p / "text.txt").write_text(full_text, encoding="utf-8")
    (out_dir_p / "pages.json").write_text(json.dumps(pages, indent=2), encoding="utf-8")

    figures = extract_images_from_pdf(str(pdf_path), str(figures_dir), max_images=max_images)

    manifest = {
        "pdf_path": str(Path(pdf_path).resolve()),
        "out_dir": str(out_dir_p.resolve()),
        "page_count": len(pages),
        "text_path": str((out_dir_p / "text.txt").resolve()),
        "pages_json": str((out_dir_p / "pages.json").resolve()),
        "pages_dir": str(pages_dir.resolve()),
        "figures_dir": str(figures_dir.resolve()),
        "figures": [f.path for f in figures],
    }

    (out_dir_p / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
