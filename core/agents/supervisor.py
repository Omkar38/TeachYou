from __future__ import annotations

from typing import Any, Dict, List

from core.llm.router import generate_json
from core.utils.text import extractive_summary, pick_key_phrases


def plan(text: str, mode: str, quick_segments: int = 2, max_segments: int = 10, default_duration: int = 70) -> Dict[str, Any]:
    """
    Supervisor: outline + storyboard.

    Primary path: LLM-generated outline + objectives.
    Fallback: fully offline extractive summary + keyword heuristics.
    """
    key_phrases = pick_key_phrases(text, max_phrases=10)

    if mode == "quick":
        titles = ["Problem & Motivation", "Method in Simple Terms"]
        if quick_segments >= 3:
            titles.append("Key Results & Takeaways")
        titles = titles[:quick_segments]
    else:
        titles = [
            "Problem & Motivation",
            "Background / Prerequisites",
            "Data / Setup",
            "Method Overview",
            "Implementation Details",
            "Experiments / Evaluation",
            "Results",
            "Limitations",
            "Practical Implications",
            "Key Takeaways",
        ]
        titles = titles[:max_segments]

    segments: List[Dict[str, Any]] = []
    # Try LLM for a better outline/objectives.
    try:
        context = text
        if len(context) > 12000:
            context = context[:12000] + "\n\n[TRUNCATED]"

        schema = {
            "type": "object",
            "properties": {
                "outline": {"type": "array", "items": {"type": "string"}},
                "key_phrases": {"type": "array", "items": {"type": "string"}},
                "objectives": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["outline", "key_phrases", "objectives"],
        }

        prompt = (
            "You are planning an explainer video for an academic paper.\n"
            "Return JSON only.\n\n"
            f"MODE: {mode}.\n"
            f"SEGMENT_TITLES: {titles}.\n\n"
            "TASK:\n"
            "1) Provide 6-8 concise outline bullets grounded in the paper text.\n"
            "2) Provide 8-12 key phrases (terms) that are actually present or strongly implied.\n"
            "3) For each segment title, write a 1-2 sentence objective (simple, engaging).\n\n"
            "PAPER_TEXT:\n" + context
        )

        resp = generate_json(prompt=prompt, schema=schema)
        outline_bullets = [str(x).strip() for x in (resp.get("outline") or []) if str(x).strip()][:8]
        llm_phrases = [str(x).strip() for x in (resp.get("key_phrases") or []) if str(x).strip()][:12]
        objectives = [str(x).strip() for x in (resp.get("objectives") or []) if str(x).strip()]

        # Keep our lightweight keyword list as a fallback; prefer LLM phrases if present.
        if llm_phrases:
            key_phrases = llm_phrases
    except Exception:
        outline_text = extractive_summary(text, max_sentences=8)
        outline_bullets = [s.strip() for s in outline_text.split(". ") if s.strip()][:8]
        objectives = []

    for i, t in enumerate(titles):
        if i < len(objectives) and objectives[i]:
            objective = objectives[i]
        else:
            objective = f"Explain: {t}. Use simple language, relate to the paper, and define important terms."
        segments.append({"segment_index": i, "title": t, "objective": objective, "duration_target_sec": default_duration})

    return {"outline": outline_bullets, "key_phrases": key_phrases, "segments": segments}
