from __future__ import annotations

from pathlib import Path


def wrap_svg_as_html(svg: str, *, title: str = "Scene", out_html: str) -> str:
    """Write a self-contained HTML that plays SVG animations."""
    p = Path(out_html)
    p.parent.mkdir(parents=True, exist_ok=True)

    html = f"""<!doctype html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\" />
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
    <title>{_html_escape(title)}</title>
    <style>
      html, body {{ height: 100%; margin: 0; }}
      body {{
        display: grid;
        place-items: center;
        background: radial-gradient(1200px 700px at 25% 20%, rgba(37,99,235,0.10), transparent 55%),
                    radial-gradient(900px 600px at 75% 70%, rgba(16,185,129,0.10), transparent 55%),
                    #FAFAFB;
      }}
      .frame {{
        width: 1280px;
        height: 720px;
        border-radius: 26px;
        overflow: hidden;
        box-shadow: 0 30px 80px rgba(0,0,0,0.10);
        background: #FCFCFD;
      }}
      /* A tiny film-safe padding in case overlays are added later */
      .safe {{ width: 100%; height: 100%; padding: 0; }}
      .safe > svg {{ width: 100%; height: 100%; display: block; }}
    </style>
  </head>
  <body>
    <div class=\"frame\">
      <div class=\"safe\">
        {svg}
      </div>
    </div>
  </body>
</html>
"""

    p.write_text(html, encoding="utf-8")
    return str(p)


def _html_escape(s: str) -> str:
    return (
        (s or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
