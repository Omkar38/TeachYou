from __future__ import annotations

from typing import Any, Dict, List

from core.llm.router import _extract_json_object, generate_json, generate_text
from core.retrieval.bm25_retriever import BM25Retriever
from core.utils.text import extractive_summary


def teach(
    segment_title: str,
    objective: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 5,
    depth: str = "quick",
) -> Dict[str, Any]:
    texts = [c["text"] for c in chunks]
    retriever = BM25Retriever.build(texts)
    ranked = retriever.top_k(query=f"{segment_title}. {objective}", k=min(top_k, len(texts)))

    chosen = [chunks[i] for i, _ in ranked if i < len(chunks)]
    chosen_text = "\n\n".join(c["text"] for c in chosen)

    # LLM-first narration (fallback to offline extractive summary)
    base_summary = extractive_summary(chosen_text, max_sentences=8)
    if not base_summary:
        base_summary = extractive_summary("\n\n".join(texts[:3]), max_sentences=6)

    style = "concise" if depth == "quick" else "rich but clear"
    max_words = 180 if depth == "quick" else 300

    prompt = (
        "You are a helpful teacher generating narration for a paper-to-explainer video. "
        "Write a spoken, engaging script for ONE segment.\n\n"
        f"Segment title: {segment_title}\n"
        f"Objective: {objective}\n"
        f"Style: {style}\n"
        f"Target length: <= {max_words} words\n\n"
        "Ground your script strictly in the provided SOURCE NOTES (do not invent facts). "
        "Explain unfamiliar terms briefly. Avoid equations unless necessary. "
        "Return JSON with keys: script (string), key_terms (list[str]).\n\n"
        "SOURCE NOTES:\n"
        f"{chosen_text[:12000]}\n\n"
        "(If the notes are noisy, use this extractive summary as a backbone):\n"
        f"{base_summary}\n"
    )

    # out = generate_json(prompt, schema_hint="{script: string, key_terms: list[string]}")
    out = generate_json(prompt, schema="{script: string, key_terms: list[string]}")
    script = str(out.get("script") or "").strip() or (
        f"{segment_title}.\n\nIn simple terms: {base_summary}".strip()
    )

    citations = [{"chunk_index": c["chunk_index"]} for c in chosen] or [{"chunk_index": 0}]

    return {
        "script": script,
        "citations": citations,
        "selected_chunk_indices": [c["chunk_index"] for c in chosen],
        "key_terms": out.get("key_terms") or [],
    }
