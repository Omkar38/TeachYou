from __future__ import annotations

from typing import Any, Dict

from core.llm.router import generate_json
from core.whiteboard.storyboard import bullets_from_script


SCENEGRAPH_SHAPE = (
    "{version: string, title: string, layout: {template: string, notes: string}, elements: list[object]}"
)


def plan_scenegraph(
    *,
    title: str,
    objective: str,
    script: str,
    video_style: str,
    width: int,
    height: int,
    mode: str = "quick",
) -> Dict[str, Any]:
    """Plan a SceneGraph for one segment.

    Preferred path: ask LLM for a small, structured SceneGraph (JSON only).
    Fallback path: deterministic bullets-only SceneGraph.

    The returned SceneGraph is intentionally minimal but designed to be editable:
    - `elements` is an ordered list of renderable items (title, bullets, diagram, etc.)
    - diagrams use `engine=mermaid` so we can render via Playwright
    """

    title_clean = (title or "Scene").strip() or "Scene"
    objective_clean = (objective or "").strip()
    script_clean = (script or "").strip()

    bullets = bullets_from_script(script_clean, max_bullets=4)

    # Light heuristic: if the segment sounds like a process/pipeline, ask for a mermaid diagram.
    wants_diagram = any(
        k in script_clean.lower()
        for k in ["pipeline", "workflow", "process", "steps", "architecture", "flow", "diagram"]
    )

    prompt = (
        "You are generating a SceneGraph for a whiteboard explainer scene.\n"
        "Output ONLY valid JSON. No markdown.\n\n"
        f"VIDEO_STYLE: {video_style}\n"
        f"CANVAS: {width}x{height}\n"
        f"MODE: {mode}\n\n"
        "GOAL: Create a clean, editable scene layout optimized for text clarity.\n"
        "- Keep on-screen text short (<= 12 words per bullet).\n"
        "- Prefer 3-4 bullets.\n"
        "- If a diagram helps, include ONE mermaid diagram element (engine=mermaid).\n"
        "- Do NOT include any external links.\n\n"
        f"SEGMENT_TITLE: {title_clean}\n"
        f"SEGMENT_OBJECTIVE: {objective_clean}\n\n"
        "NARRATION_SCRIPT:\n"
        f"{script_clean[:2000]}\n\n"
        "SUGGESTED_BULLETS (you may edit):\n"
        + "\n".join(f"- {b}" for b in bullets)
    )

    out = generate_json(
        prompt,
        schema=SCENEGRAPH_SHAPE,
    )

    obj = out.obj if hasattr(out, "obj") else None
    if isinstance(obj, dict) and obj.get("elements"):
        # Ensure minimal required keys exist.
        obj.setdefault("version", "1.0")
        obj.setdefault("title", title_clean)
        obj.setdefault("layout", {"template": "split" if wants_diagram else "title_bullets", "notes": ""})
        return obj

    # Offline fallback
    sg: Dict[str, Any] = {
        "version": "1.0",
        "title": title_clean,
        "layout": {
            "template": "split" if wants_diagram else "title_bullets",
            "notes": "offline_fallback",
        },
        "elements": [
            {"type": "title", "text": title_clean},
            {"type": "bullets", "items": bullets or [objective_clean] if objective_clean else ["Key idea", "How it works", "Why it matters"]},
        ],
    }

    if wants_diagram:
        # Very simple diagram skeleton.
        sg["elements"].append(
            {
                "type": "diagram",
                "engine": "mermaid",
                "code": "graph TD\n  Input-->Process\n  Process-->Output",
                "caption": "High-level flow",
            }
        )

    return sg
