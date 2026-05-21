from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Iterable, List


@dataclass
class SceneStyle:
    width: int = 1280
    height: int = 720
    bg: str = "#FCFCFD"
    ink: str = "#111111"
    accent: str = "#2563EB"  # blue
    font_family: str = "ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Arial"


def _seed_from(*parts: str) -> int:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def _jitter_line(rng: random.Random, x1: float, y1: float, x2: float, y2: float, amp: float = 1.8, steps: int = 10) -> str:
    """Return a hand-drawn-ish quadratic polyline path."""
    pts = []
    for i in range(steps + 1):
        t = i / steps
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        # Perpendicular jitter
        dx = x2 - x1
        dy = y2 - y1
        ln = math.hypot(dx, dy) or 1.0
        nx = -dy / ln
        ny = dx / ln
        j = (rng.random() - 0.5) * 2.0 * amp
        pts.append((x + nx * j, y + ny * j))
    d = f"M {pts[0][0]:.2f} {pts[0][1]:.2f} "
    for (x, y) in pts[1:]:
        d += f"L {x:.2f} {y:.2f} "
    return d.strip()


def _checkmark_path(rng: random.Random, x: float, y: float, s: float = 18.0) -> str:
    return _jitter_line(rng, x, y, x + s * 0.35, y + s * 0.45, amp=1.4, steps=5) + " " + _jitter_line(
        rng, x + s * 0.35, y + s * 0.45, x + s, y - s * 0.2, amp=1.4, steps=6
    )


def build_scene_svg(title: str, bullets: List[str], *, style: SceneStyle | None = None, seed_hint: str = "") -> str:
    style = style or SceneStyle()
    rng = random.Random(_seed_from(title, seed_hint))

    W, H = style.width, style.height

    # Layout
    pad_x = 80
    pad_y = 70
    title_y = pad_y + 36
    underline_y = title_y + 18

    # Left doodle area
    doodle_x = pad_x
    doodle_y = pad_y + 120
    doodle_w = 360
    doodle_h = 380

    bullets_x = pad_x + doodle_w + 60
    bullets_y = pad_y + 130
    bullet_gap = 76

    # Doodle: a "lightbulb + circuit" style (generic explainer vibe)
    cx = doodle_x + doodle_w * 0.45
    cy = doodle_y + doodle_h * 0.28
    r = 78
    bulb = _jitter_line(rng, cx - r, cy, cx + r, cy, amp=2.2, steps=18)

    # Simple bulb outline using multiple arcs-ish polylines
    arcs = []
    for k in range(5):
        ang1 = math.pi * (1.05 + k * 0.12)
        ang2 = math.pi * (1.95 - k * 0.12)
        x1 = cx + r * math.cos(ang1)
        y1 = cy + r * math.sin(ang1)
        x2 = cx + r * math.cos(ang2)
        y2 = cy + r * math.sin(ang2)
        arcs.append(_jitter_line(rng, x1, y1, x2, y2, amp=2.0, steps=14))
    base1 = _jitter_line(rng, cx - 45, cy + 70, cx + 45, cy + 70, amp=1.6, steps=10)
    base2 = _jitter_line(rng, cx - 35, cy + 90, cx + 35, cy + 90, amp=1.6, steps=10)
    base3 = _jitter_line(rng, cx - 25, cy + 110, cx + 25, cy + 110, amp=1.6, steps=10)

    # Circuit lines
    c1 = _jitter_line(rng, cx, cy + 110, cx, cy + 190, amp=1.8, steps=12)
    c2 = _jitter_line(rng, cx, cy + 190, cx - 90, cy + 250, amp=1.8, steps=12)
    c3 = _jitter_line(rng, cx, cy + 190, cx + 120, cy + 250, amp=1.8, steps=12)
    node1 = (cx - 90, cy + 250)
    node2 = (cx + 120, cy + 250)
    node3 = (cx, cy + 190)

    underline = _jitter_line(rng, pad_x, underline_y, W - pad_x, underline_y, amp=1.2, steps=24)

    # Build SVG elements
    paths_ink: list[str] = []
    paths_accent: list[str] = []

    # Title underline + doodle in accent
    paths_accent.append(underline)
    for p in arcs:
        paths_ink.append(p)
    paths_ink.extend([base1, base2, base3])
    paths_ink.extend([c1, c2, c3])

    # Bullet checkmarks
    bullet_paths: list[str] = []
    bullet_texts: list[str] = []
    for i, b in enumerate(bullets[:5]):
        y = bullets_y + i * bullet_gap
        bullet_paths.append(_checkmark_path(rng, bullets_x, y, s=22))
        bullet_texts.append(b)

    # Accessibility: avoid super-long title
    title = (title or "Explainer").strip()
    if len(title) > 80:
        title = title[:77].rstrip() + "…"


        # CSS (build as a single block to avoid f-string / brace parsing issues)
    css = """
      .ink { fill: none; stroke: %(ink)s; stroke-width: 4.2; stroke-linecap: round; stroke-linejoin: round; }
      .accent { fill: none; stroke: %(accent)s; stroke-width: 5.0; stroke-linecap: round; stroke-linejoin: round; }

      .draw  { stroke-dasharray: 1200; stroke-dashoffset: 1200; animation: draw 2.8s ease forwards; }
      .draw2 { stroke-dasharray: 1200; stroke-dashoffset: 1200; animation: draw 2.8s ease forwards; animation-delay: 0.25s; }
      .draw3 { stroke-dasharray: 1200; stroke-dashoffset: 1200; animation: draw 2.8s ease forwards; animation-delay: 0.55s; }

      .fade  { opacity: 0; animation: fade 0.9s ease forwards; }
      .fade1 { animation-delay: 0.9s; }
      .fade2 { animation-delay: 1.35s; }
      .fade3 { animation-delay: 1.8s; }
      .fade4 { animation-delay: 2.25s; }

      .title  { font-family: %(font)s; font-weight: 750; font-size: 42px; letter-spacing: -0.02em; fill: %(ink)s; }
      .bullet { font-family: %(font)s; font-weight: 520; font-size: 28px; fill: %(ink)s; }

      @keyframes draw { to { stroke-dashoffset: 0; } }
      @keyframes fade { to { opacity: 1; } }
    """ % {"ink": style.ink, "accent": style.accent, "font": style.font_family}

    style_block = "<style><![CDATA[\n" + css + "\n]]></style>"


    # CSS animations: stroke draw + fade in text
    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="whiteboard scene">',
        f'<rect width="{W}" height="{H}" fill="{style.bg}" />',
        # subtle dot grid
        '<defs>',
        '<pattern id="dot" width="24" height="24" patternUnits="userSpaceOnUse">',
        f'<circle cx="2" cy="2" r="1" fill="#E5E7EB" opacity="0.55" />',
        '</pattern>',
        '</defs>',
        f'<rect width="{W}" height="{H}" fill="url(#dot)" opacity="0.45" />',
        style_block,
        f'<text x="{pad_x}" y="{title_y}" class="title fade fade1">{_xml_escape(title)}</text>',
        f'<path d="{underline}" class="accent draw" />',
    ]

    # Doodle strokes
    for idx, p in enumerate(paths_ink):
        cls = "ink draw2" if idx < 4 else "ink draw3"
        svg.append(f'<path d="{p}" class="{cls}" />')

    # Nodes
    svg.append(f'<circle cx="{node1[0]:.1f}" cy="{node1[1]:.1f}" r="7" fill="{style.accent}" opacity="0.9" />')
    svg.append(f'<circle cx="{node2[0]:.1f}" cy="{node2[1]:.1f}" r="7" fill="{style.accent}" opacity="0.9" />')
    svg.append(f'<circle cx="{node3[0]:.1f}" cy="{node3[1]:.1f}" r="7" fill="{style.accent}" opacity="0.9" />')

    # Bullets
    for i, p in enumerate(bullet_paths):
        svg.append(f'<path d="{p}" class="ink draw3" />')
        cls = f"bullet fade fade{i+1 if i<4 else 4}"
        svg.append(f'<text x="{bullets_x + 46}" y="{(bullets_y + i * bullet_gap) + 10}" class="{cls}">{_xml_escape(bullet_texts[i])}</text>')

    svg.append("</svg>")
    return "\n".join(svg)


def _xml_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
