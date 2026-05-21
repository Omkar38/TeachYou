from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List

from core.llm.router import generate_json
from core.storyboard.schema import (
    PRESET_CONFIG,
    CaptionStyle,
    Scene,
    Storyboard,
    Voiceover,
)
from core.utils.text import extractive_summary, pick_key_phrases


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def plan_storyboard(
    text: str,
    job_id: str,
    title: str = "",
    aspect_ratio: str = "9:16",
    length_preset: str = "30s",
    mode: str = "quick",
) -> Storyboard:
    """
    General-purpose storyboard planner.

    Primary: LLM generates scene titles, objectives, and scripts in one call.
    Fallback: offline extractive summary splits into scenes with placeholder scripts.
    """
    n_scenes, duration_s, words_per_scene = PRESET_CONFIG.get(
        length_preset, PRESET_CONFIG["30s"]
    )

    # deep mode adds scenes relative to preset
    if mode == "deep" and n_scenes < 8:
        n_scenes = min(n_scenes * 2, 8)

    text_preview = text[:8000] if len(text) > 8000 else text

    scenes = _llm_scenes(
        text_preview, n_scenes=n_scenes, words_per_scene=words_per_scene,
        aspect_ratio=aspect_ratio, length_preset=length_preset,
    )

    if not scenes:
        scenes = _offline_scenes(text, n_scenes=n_scenes, duration_s=duration_s)

    # Attach shared defaults to every scene
    for i, s in enumerate(scenes):
        s.order = i
        s.duration_s = duration_s
        s.voiceover = Voiceover(provider="espeak", voice_id="en-us", speed=1.0)
        s.captions = CaptionStyle(style="minimal")

    inferred_title = title or _infer_title(text, scenes)

    return Storyboard(
        storyboard_id=str(uuid.uuid4()),
        job_id=job_id,
        title=inferred_title,
        aspect_ratio=aspect_ratio,  # type: ignore[arg-type]
        length_preset=length_preset,  # type: ignore[arg-type]
        scenes=scenes,
        created_at=datetime.utcnow(),
        version=1,
    )


# ---------------------------------------------------------------------------
# LLM path
# ---------------------------------------------------------------------------

def _llm_scenes(
    text: str,
    *,
    n_scenes: int,
    words_per_scene: int,
    aspect_ratio: str,
    length_preset: str,
) -> list[Scene]:
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "scenes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title":     {"type": "string"},
                        "objective": {"type": "string"},
                        "script":    {"type": "string"},
                    },
                    "required": ["title", "objective", "script"],
                },
            },
        },
        "required": ["title", "scenes"],
    }

    prompt = (
        "You are planning a short-form video storyboard. Return JSON only.\n\n"
        f"Aspect ratio: {aspect_ratio} | Length: {length_preset} | Scenes: {n_scenes}\n\n"
        "Rules:\n"
        f"- Exactly {n_scenes} scene(s).\n"
        f"- Each 'script' is {words_per_scene} words, conversational and direct.\n"
        "- First scene: hook the viewer immediately.\n"
        "- Last scene: clear takeaway or call to action.\n"
        "- No academic language, no bullet lists in the script.\n\n"
        "Source text / topic:\n"
        f"{text}\n\n"
        "JSON schema:\n"
        '{"title": "...", "scenes": [{"title": "...", "objective": "...", "script": "..."}]}'
    )

    try:
        resp = generate_json(prompt=prompt, schema=schema)
        raw_scenes = resp.get("scenes") or []
        out: list[Scene] = []
        for item in raw_scenes[:n_scenes]:
            out.append(Scene(
                scene_id=str(uuid.uuid4()),
                title=str(item.get("title") or "").strip(),
                objective=str(item.get("objective") or "").strip(),
                script=str(item.get("script") or "").strip(),
            ))
        return out
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Offline fallback
# ---------------------------------------------------------------------------

def _offline_scenes(text: str, *, n_scenes: int, duration_s: float) -> list[Scene]:
    summary = extractive_summary(text, max_sentences=n_scenes * 3)
    sentences = [s.strip() for s in summary.split(". ") if s.strip()]

    bucket_size = max(1, len(sentences) // max(1, n_scenes))
    scenes: list[Scene] = []

    for i in range(n_scenes):
        start = i * bucket_size
        chunk = sentences[start : start + bucket_size]
        script = ". ".join(chunk).strip()
        if not script:
            script = f"Part {i + 1} of the topic."
        title = _title_from_script(script, index=i, total=n_scenes)
        scenes.append(Scene(
            scene_id=str(uuid.uuid4()),
            title=title,
            objective=f"Cover: {title}",
            script=script,
        ))

    return scenes


def _title_from_script(script: str, *, index: int, total: int) -> str:
    labels = ["Introduction", "Core Concept", "Key Details", "Examples", "Takeaway"]
    if index < len(labels):
        return labels[index]
    return f"Part {index + 1}"


def _infer_title(text: str, scenes: list[Scene]) -> str:
    if scenes and scenes[0].title:
        # Use first 4 words of scene 1 title as a rough title
        words = scenes[0].title.split()
        return " ".join(words[:6])
    phrases = pick_key_phrases(text, max_phrases=3)
    if phrases:
        return phrases[0].title()
    return "Untitled Video"


# ---------------------------------------------------------------------------
# Legacy shim — keeps existing callers working during the transition
# ---------------------------------------------------------------------------

def plan(
    text: str,
    mode: str,
    quick_segments: int = 2,
    max_segments: int = 10,
    default_duration: int = 70,
) -> Dict[str, Any]:
    """Backward-compatible wrapper. Returns the old dict shape."""
    length_preset = "30s" if mode == "quick" else "3m"
    sb = plan_storyboard(
        text=text,
        job_id="",
        aspect_ratio="9:16",
        length_preset=length_preset,
        mode=mode,
    )
    segments: List[Dict[str, Any]] = [
        {
            "segment_index": s.order,
            "title": s.title,
            "objective": s.objective,
            "duration_target_sec": s.duration_s,
        }
        for s in sb.scenes
    ]
    key_phrases = pick_key_phrases(text, max_phrases=10)
    return {
        "outline": [],
        "key_phrases": key_phrases,
        "segments": segments,
    }
