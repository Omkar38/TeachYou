from __future__ import annotations

from typing import Any

from core.llm.router import generate_json
from core.storyboard.schema import Storyboard

_EDITABLE_FIELDS = {"title", "objective", "script", "duration_s"}


def edit_storyboard(
    storyboard: Storyboard,
    instruction: str,
) -> tuple[Storyboard, list[dict[str, Any]]]:
    """Apply a natural language instruction to a storyboard.

    Returns (updated_storyboard, applied_changes).
    Falls back to returning the original storyboard unchanged if the LLM is unavailable.
    """
    scenes_summary = "\n".join(
        f"  [{i}] title={s.title!r}  script={s.script[:100]!r}{'…' if len(s.script) > 100 else ''}"
        for i, s in enumerate(storyboard.scenes)
    )

    schema = {
        "type": "object",
        "properties": {
            "changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "scene_index": {"type": "integer",
                                        "description": "-1 for storyboard-level title; 0-based scene index otherwise"},
                        "field": {"type": "string", "enum": list(_EDITABLE_FIELDS)},
                        "value": {"description": "New value (string for text fields, number for duration_s)"},
                    },
                    "required": ["scene_index", "field", "value"],
                },
            },
            "explanation": {"type": "string"},
        },
        "required": ["changes", "explanation"],
    }

    prompt = (
        "You are editing a short-form video storyboard. Apply the user's instruction with minimal changes.\n\n"
        f"Storyboard title: {storyboard.title!r}\n"
        f"Total scenes: {len(storyboard.scenes)}\n\n"
        "Scenes:\n"
        f"{scenes_summary}\n\n"
        f"User instruction: {instruction}\n\n"
        "Rules:\n"
        "- scene_index: -1 = storyboard title; 0..N-1 = specific scene\n"
        "- field: title | objective | script | duration_s\n"
        "- Script rewrites must stay conversational and direct — no bullet lists\n"
        "- Only touch what the instruction explicitly asks to change\n"
        "- Return changes: [] if nothing needs to change\n\n"
        'JSON: {"changes": [{"scene_index": 0, "field": "script", "value": "..."}], "explanation": "..."}'
    )

    try:
        resp = generate_json(prompt=prompt, schema=schema)
        raw_changes = resp.get("changes") or []
    except Exception:
        return storyboard, []

    if not raw_changes:
        return storyboard, []

    updated = storyboard.model_copy(deep=True)
    applied: list[dict[str, Any]] = []

    for ch in raw_changes:
        idx = ch.get("scene_index", -99)
        field = str(ch.get("field") or "")
        value = ch.get("value")

        if field not in _EDITABLE_FIELDS:
            continue

        if idx == -1:
            if field == "title" and isinstance(value, str):
                updated.title = value
                applied.append(ch)
        elif 0 <= idx < len(updated.scenes):
            scene = updated.scenes[idx]
            if field == "title":
                scene.title = str(value)
            elif field == "objective":
                scene.objective = str(value)
            elif field == "script":
                scene.script = str(value)
            elif field == "duration_s":
                try:
                    scene.duration_s = float(value)
                except (TypeError, ValueError):
                    continue
            applied.append(ch)

    return updated, applied
