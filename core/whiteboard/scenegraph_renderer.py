from __future__ import annotations

import html
from typing import Any, Dict, List, Tuple


def _theme(video_style: str) -> Dict[str, str]:
    if (video_style or "").lower() == "business":
        return {
            "accent": "#0f766e",  # teal
            "bg": "#0b1220",
            "panel": "#0f172a",
            "text": "#e2e8f0",
            "muted": "#94a3b8",
        }
    # education (default)
    return {
        "accent": "#2563eb",  # blue
        "bg": "#0b1220",
        "panel": "#0f172a",
        "text": "#e2e8f0",
        "muted": "#94a3b8",
    }


def _find_first(elements: List[Dict[str, Any]], type_: str) -> Dict[str, Any] | None:
    for e in elements or []:
        if isinstance(e, dict) and e.get("type") == type_:
            return e
    return None


def render_scene_html(
    scenegraph: Dict[str, Any],
    *,
    width: int,
    height: int,
    video_style: str = "education",
) -> Tuple[str, Dict[str, Any]]:
    """Render a SceneGraph into self-contained HTML.

    Returns:
      (html_string, meta)

    The HTML is designed to be recorded via Playwright. Animations are CSS-based.
    """

    theme = _theme(video_style)
    elements = scenegraph.get("elements") or []
    title_text = str(scenegraph.get("title") or "").strip() or "Scene"

    bullets_e = _find_first(elements, "bullets") or {"items": []}
    bullets = bullets_e.get("items") or []
    bullets = [str(b).strip() for b in bullets if str(b).strip()][:6]

    diagram_e = _find_first(elements, "diagram")
    diagram_engine = (diagram_e.get("engine") if diagram_e else None) or None
    diagram_code = (diagram_e.get("code") if diagram_e else "") if diagram_e else ""
    diagram_caption = (diagram_e.get("caption") if diagram_e else "") if diagram_e else ""

    caption_html = f"<div class='diagramCaption'>{html.escape(diagram_caption)}</div>" if diagram_caption else ""

    template = ((scenegraph.get("layout") or {}).get("template") or "title_bullets").lower()
    has_diagram = bool(diagram_engine and diagram_code)

    # layout
    vertical = height > width
    if template == "split" and not has_diagram:
        template = "title_bullets"

    # escape
    title_html = html.escape(title_text)
    bullets_html = "\n".join(
        f"<li style=\"animation-delay:{0.35 + i*0.28:.2f}s\">{html.escape(b)}</li>" for i, b in enumerate(bullets)
    )

    # Diagram region: for mermaid, render into a div
    diagram_block = ""
    if has_diagram and diagram_engine.lower() == "mermaid":
        mermaid_src = html.escape(diagram_code)
        diagram_block = f"""
          <div class=\"diagramWrap\">
            <div id=\"diagram\" class=\"diagram mermaid\">{mermaid_src}</div>
            {caption_html}
          </div>
        """
    elif has_diagram:
        # unknown engine => show as code block
        diagram_block = f"""
          <div class=\"diagramWrap\">
            <pre class=\"diagramCode\">{html.escape(diagram_code)}</pre>
            {caption_html}
          </div>
        """


    # Precompute conditional inserts (avoid nested f-strings inside { } expressions)
    diagram_card_html = f"<div class='card diagramCard'>{diagram_block}</div>" if has_diagram else ""
    # Build content layout
    if vertical:
        # 720x1280: stack panels
        content_html = f"""
          <div class=\"title\">{title_html}</div>
          <div class=\"stack\">
            <div class=\"card bulletsCard\">
              <ul class=\"bullets\">{bullets_html}</ul>
            </div>
            {diagram_card_html}
          </div>
        """
    else:
        # 1280x720: side-by-side
        if template == "title_diagram" and has_diagram:
            left = diagram_block
            right = f"<ul class=\"bullets\">{bullets_html}</ul>"
        else:
            left = f"<ul class=\"bullets\">{bullets_html}</ul>"
            right = diagram_block if has_diagram else ""


        right_card_html = f"<div class='card'>{right}</div>" if has_diagram else ""
        content_html = f"""
          <div class=\"title\">{title_html}</div>
          <div class=\"grid\">
            <div class=\"card\">{left}</div>
            {right_card_html}
          </div>
        """

    # Mermaid loader (CDN-first; optional local vendoring if user adds it later)
    mermaid_loader = ""
    if has_diagram and diagram_engine.lower() == "mermaid":
        mermaid_loader = """
<script>
(function(){
  function loadScript(src){
    return new Promise((resolve,reject)=>{
      const s=document.createElement('script');
      s.src=src; s.onload=()=>resolve(); s.onerror=()=>reject();
      document.head.appendChild(s);
    });
  }
  async function boot(){
    try { await loadScript('./vendor/mermaid.min.js'); }
    catch(e){ await loadScript('https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js'); }
    if (window.mermaid){
      window.mermaid.initialize({ startOnLoad: true, theme: 'dark' });
      try { window.mermaid.run({ querySelector: '#diagram' }); } catch(e) {}
    }
  }
  boot();
})();
</script>
"""

    # Styles + animations
    css = f"""
:root{{
  --bg: {theme['bg']};
  --panel: {theme['panel']};
  --text: {theme['text']};
  --muted: {theme['muted']};
  --accent: {theme['accent']};
}}
html,body{{ margin:0; padding:0; width:100%; height:100%; background:var(--bg); color:var(--text); font-family: ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,Helvetica,Arial; overflow:hidden; }}
.scene{{ width:{width}px; height:{height}px; padding:{24 if vertical else 28}px; box-sizing:border-box; display:flex; flex-direction:column; }}
.title{{ font-size:{36 if vertical else 34}px; font-weight:700; letter-spacing:-0.02em; margin:4px 0 14px; opacity:0; animation:fadeIn 0.5s ease forwards; }}
.grid{{ display:grid; grid-template-columns: 1fr 1fr; gap:16px; flex:1; }}
.stack{{ display:flex; flex-direction:column; gap:16px; flex:1; }}
.card{{ background:var(--panel); border:1px solid rgba(148,163,184,0.15); border-radius:18px; padding:18px 18px; box-shadow:0 10px 30px rgba(0,0,0,0.25); }}
.bullets{{ list-style:none; padding:0; margin:0; }}
.bullets li{{
  font-size:{26 if vertical else 22}px;
  line-height:1.25;
  margin: 10px 0;
  padding-left: 18px;
  position:relative;
  opacity:0;
  transform: translateY(8px);
  animation:pop 0.45s ease forwards;
}}
.bullets li:before{{ content:''; width:10px; height:10px; border-radius:999px; background:var(--accent); position:absolute; left:0; top: 0.55em; }}
.diagramWrap{{ width:100%; height:100%; display:flex; flex-direction:column; }}
.diagram{{ width:100%; flex:1; display:flex; align-items:center; justify-content:center; }}
.diagramCaption{{ font-size:14px; color:var(--muted); margin-top:10px; }}
.diagramCode{{ width:100%; height:100%; color:var(--text); background:rgba(0,0,0,0.35); border:1px solid rgba(148,163,184,0.20); border-radius:14px; padding:12px; font-size:14px; overflow:auto; }}
@keyframes fadeIn{{ to{{ opacity:1; }} }}
@keyframes pop{{ to{{ opacity:1; transform:translateY(0); }} }}
"""

    html_doc = f"""<!doctype html>
<html>
<head>
<meta charset='utf-8' />
<meta name='viewport' content='width=device-width, initial-scale=1.0' />
<style>{css}</style>
</head>
<body>
<div class='scene'>
  {content_html}
</div>
{mermaid_loader}
</body>
</html>
"""

    meta = {
        "template": template,
        "has_diagram": has_diagram,
        "diagram_engine": diagram_engine,
        "width": width,
        "height": height,
        "video_style": video_style,
    }
    return html_doc, meta
