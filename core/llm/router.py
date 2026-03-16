from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import httpx

from apps.api.settings import settings


@dataclass
class LLMResult:
    provider: str
    text: str


def _extract_json_object(s: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON extraction (handles models that wrap JSON in text)."""
    if not s:
        return None
    s = s.strip()
    try:
        return json.loads(s)
    except Exception:
        pass

    # Try to find the first {...} block
    m = re.search(r"\{[\s\S]*\}", s)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _gemini_generate(prompt: str, model: str) -> str:
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY missing")
    url = f"https://generativelanguage.googleapis.com/v1/models/{model}:generateContent"
    headers = {
        "x-goog-api-key": settings.gemini_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": settings.llm_temperature,
            "maxOutputTokens": settings.llm_max_output_tokens,
        },
    }
    with httpx.Client(timeout=settings.llm_timeout_sec) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    # candidates[0].content.parts[0].text
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini returned no candidates")
    content = candidates[0].get("content") or {}
    parts = content.get("parts") or []
    text = "".join(p.get("text", "") for p in parts if isinstance(p, dict)).strip()
    if not text:
        raise RuntimeError("Gemini returned empty text")
    return text


def _openai_generate(prompt: str, model: str) -> str:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY missing")
    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "input": prompt,
    }
    with httpx.Client(timeout=settings.llm_timeout_sec) as client:
        r = client.post(url, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    # Try the most stable fields first
    if isinstance(data, dict):
        if isinstance(data.get("output_text"), str) and data["output_text"].strip():
            return data["output_text"].strip()

        # Parse message outputs
        out = data.get("output") or []
        for item in out:
            if not isinstance(item, dict):
                continue
            content = item.get("content") or []
            for c in content:
                if isinstance(c, dict) and c.get("type") == "output_text":
                    t = c.get("text")
                    if isinstance(t, str) and t.strip():
                        return t.strip()

    raise RuntimeError("OpenAI response had no text")


def _ollama_generate(prompt: str, model: str, *, force_json: bool = False) -> str:
    url = settings.ollama_base_url.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": settings.llm_temperature},
    }
    if force_json:
        payload["format"] = "json"  # Ollama supports this on /api/generate :contentReference[oaicite:2]{index=2}

    with httpx.Client(timeout=settings.llm_timeout_sec) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()

    text = (data.get("response") or "").strip()
    if not text:
        raise RuntimeError("Ollama returned empty text")
    return text



def generate_text(prompt: str, *, force_json: bool = False) -> Optional[LLMResult]:
    order = [p.strip() for p in (settings.llm_provider_order or "").split(",") if p.strip()]
    for provider in order:
        try:
            if provider == "gemini":
                return LLMResult("gemini", _gemini_generate(prompt, settings.gemini_model))
            if provider == "openai":
                return LLMResult("openai", _openai_generate(prompt, settings.openai_model))
            if provider == "ollama":
                return LLMResult("ollama", _ollama_generate(prompt, settings.ollama_model, force_json=force_json))
            if provider == "offline":
                return None
        except Exception as e:
            print(f"[LLM FAIL] {provider}: {e}")
            continue
    return None


class JSONResult(dict):
    """
    Dict-like parsed JSON with optional raw result.
    Supports:
      out = generate_json(...); out.get(...)
      obj, raw = generate_json(...)
    """
    def __init__(self, obj, raw):
        super().__init__(obj or {})
        self.obj = obj
        self.raw = raw

    def __iter__(self):
        yield self.obj
        yield self.raw


def generate_json(prompt: str, schema: str | None = None, schema_hint: str | None = None, **kwargs):
    if schema is None and schema_hint:
        schema = schema_hint

    forced = prompt
    if schema:
        forced += f"\n\nJSON schema/shape hint:\n{schema}"
    forced += "\n\nReturn ONLY a valid JSON object. Do not wrap in markdown."

    res = generate_text(forced, force_json=True)
    if not res:
        return JSONResult(None, None)

    obj = _extract_json_object(res.text)
    return JSONResult(obj, res)