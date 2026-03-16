from __future__ import annotations

import io
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader

try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:  # pragma: no cover
    Image = None  # type: ignore
    ImageDraw = None  # type: ignore
    ImageFont = None  # type: ignore


@dataclass
class VisualAsset:
    path: str
    kind: str  # extracted_image | generated_slide
    caption: str


def _safe_mkdir(path: str) -> None:
    Path(path).mkdir(parents=True, exist_ok=True)


def extract_images_from_pdf(pdf_path: str, out_dir: str, max_images: int = 20) -> list[VisualAsset]:
    """Extract embedded raster images from a PDF.

    Notes:
      - This does NOT render pages (no poppler dependency).
      - Many papers embed figures as images; when they do, this is usually enough for an MVP slideshow.
    """
    _safe_mkdir(out_dir)
    reader = PdfReader(pdf_path)
    assets: list[VisualAsset] = []
    img_idx = 0

    for page_i, page in enumerate(reader.pages):
        if img_idx >= max_images:
            break
        try:
            resources = page.get("/Resources")
            if not resources:
                continue
            xobj = resources.get("/XObject")
            if not xobj:
                continue
            xobj = xobj.get_object()
        except Exception:
            continue

        for name in xobj:
            if img_idx >= max_images:
                break
            try:
                obj = xobj[name].get_object()
                subtype = obj.get("/Subtype")
                if subtype != "/Image":
                    continue
                data = obj.get_data()

                # Heuristic extension
                filt = obj.get("/Filter")
                ext = "bin"
                if filt == "/DCTDecode":
                    ext = "jpg"
                elif filt == "/JPXDecode":
                    ext = "jp2"
                elif filt == "/FlateDecode":
                    # Often PNG-like raw. We'll write PNG if PIL can open it later; otherwise .bin
                    ext = "png"

                out_path = os.path.join(out_dir, f"fig_{page_i+1:03d}_{img_idx:03d}.{ext}")
                with open(out_path, "wb") as f:
                    f.write(data)

                caption = f"Extracted figure from page {page_i+1} ({name})"
                assets.append(VisualAsset(path=out_path, kind="extracted_image", caption=caption))
                img_idx += 1
            except Exception:
                continue

    return assets


def _wrap_text(text: str, width: int = 54) -> list[str]:
    words = re.split(r"\s+", text.strip())
    lines: list[str] = []
    cur: list[str] = []
    cur_len = 0
    for w in words:
        if not w:
            continue
        if cur_len + len(w) + (1 if cur else 0) > width:
            lines.append(" ".join(cur))
            cur = [w]
            cur_len = len(w)
        else:
            cur.append(w)
            cur_len += len(w) + (1 if cur_len else 0)
    if cur:
        lines.append(" ".join(cur))
    return lines


def render_text_slide(
    title: str,
    bullets: Iterable[str],
    out_path: str,
    size: tuple[int, int] = (1280, 720),
) -> VisualAsset:
    """Generate a simple slide image with title + bullets.

    This guarantees the video pipeline works even if the PDF has no extractable figures.
    """
    if Image is None:
        raise RuntimeError("Pillow is required to generate slides. Install pillow.")

    _safe_mkdir(str(Path(out_path).parent))
    img = Image.new("RGB", size, color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Fonts: use default if system fonts unavailable
    try:
        font_title = ImageFont.truetype("DejaVuSans.ttf", 46)
        font_body = ImageFont.truetype("DejaVuSans.ttf", 30)
    except Exception:
        font_title = ImageFont.load_default()
        font_body = ImageFont.load_default()

    x, y = 70, 60
    draw.text((x, y), title[:120], fill=(0, 0, 0), font=font_title)
    y += 90

    for b in bullets:
        if y > size[1] - 90:
            break
        for line in _wrap_text(b, width=62):
            draw.text((x, y), f"• {line}", fill=(0, 0, 0), font=font_body)
            y += 42
        y += 12

    img.save(out_path)
    return VisualAsset(path=out_path, kind="generated_slide", caption=title)
