from __future__ import annotations

import re
from collections import Counter
from typing import List

_STOPWORDS = {
    "a","an","the","and","or","but","if","then","than","that","this","these","those",
    "to","of","in","on","for","with","as","by","at","from","into","about","over","under",
    "is","are","was","were","be","been","being","it","its","we","they","their","them","you",
    "i","he","she","his","her","our","ours","your","yours","can","could","should","would",
    "may","might","must","will","just","not","no","yes","do","does","did","done",
}

_SENT_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?", re.IGNORECASE)


def normalize_whitespace(text: str) -> str:
    if not text:
        return ""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"[\t ]+", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def tokenize(text: str) -> List[str]:
    t = normalize_whitespace(text).lower()
    return _TOKEN_RE.findall(t)


def extractive_summary(text: str, max_sentences: int = 6) -> str:
    text = normalize_whitespace(text)
    if not text:
        return ""
    sents = [s.strip() for s in _SENT_SPLIT_RE.split(text) if s.strip()]
    if not sents:
        return ""

    toks = [w for w in tokenize(text) if w not in _STOPWORDS and len(w) > 2]
    if not toks:
        return " ".join(sents[:max_sentences])

    freq = Counter(toks)

    scored = []
    for i, s in enumerate(sents):
        sw = [w for w in tokenize(s) if w not in _STOPWORDS and len(w) > 2]
        score = (sum(freq.get(w, 0) for w in sw) / max(1, len(sw))) if sw else 0.0
        scored.append((i, score, s))

    top = sorted(scored, key=lambda x: x[1], reverse=True)[:max_sentences]
    top_sorted = sorted(top, key=lambda x: x[0])
    return " ".join(s for _, __, s in top_sorted)


def pick_key_phrases(text: str, max_phrases: int = 8) -> List[str]:
    toks = [t for t in tokenize(text) if t not in _STOPWORDS and len(t) > 2]
    if not toks:
        return []

    uni = Counter(toks)
    bi = Counter(" ".join(pair) for pair in zip(toks, toks[1:]))

    candidates = []
    for k, v in uni.items():
        candidates.append((k, float(v)))
    for k, v in bi.items():
        candidates.append((k, float(v) * 1.25))

    candidates.sort(key=lambda x: x[1], reverse=True)

    out = []
    seen = set()
    for k, _ in candidates:
        if k in seen:
            continue
        seen.add(k)
        out.append(k)
        if len(out) >= max_phrases:
            break
    return out
