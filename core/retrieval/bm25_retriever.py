from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from rank_bm25 import BM25Okapi

from core.utils.text import tokenize


@dataclass
class BM25Retriever:
    texts: List[str]
    bm25: BM25Okapi

    @classmethod
    def build(cls, texts: List[str]) -> "BM25Retriever":
        tokenized = [tokenize(t) for t in texts]
        return cls(texts=texts, bm25=BM25Okapi(tokenized))

    def top_k(self, query: str, k: int = 5) -> List[Tuple[int, float]]:
        q = tokenize(query)
        scores = self.bm25.get_scores(q)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked[:k]
