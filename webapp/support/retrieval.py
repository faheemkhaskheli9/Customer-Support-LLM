"""Module 5: eligibility filters first, then BM25 (optionally fused with embeddings)."""

from __future__ import annotations

import functools
import math
import os
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from django.conf import settings

from .corpus import Chunk, ingest, load_corpus

TOP_K = 3
MIN_SCORE = 3.5
MIN_COSINE = 0.45  # a starting value: re-tune it for each embedding model
RRF_K = 60
K1, B = 1.5, 0.75
TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")
STOPWORDS = {
    "a", "an", "and", "are", "at", "be", "can", "do", "does", "for", "from", "get", "how", "i",
    "if", "in", "is", "it", "me", "my", "of", "on", "or", "our", "the", "there", "this", "to",
    "what", "when", "will", "with", "you", "your",
}
SUFFIXES = ("ing", "ed", "es", "s", "e")


def stem(word: str) -> str:
    """Naive suffix stripping: a deliberate shortcut, crude ("twice" -> "twic") but consistent."""
    for suffix in SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: -len(suffix)]
    return word


def tokens(text: str) -> list[str]:
    """Lowercase words; codes like RET-30 stay whole and also add their parts."""
    out = []
    for word in TOKEN_RE.findall(text.lower()):
        parts = [word] + (word.split("-") if "-" in word else [])
        out.extend(stem(part) for part in parts if part not in STOPWORDS)
    return out


class BM25:
    def __init__(self, texts: list[str]) -> None:
        self.terms = [Counter(tokens(t)) for t in texts]
        self.lengths = [sum(c.values()) for c in self.terms]
        self.average = sum(self.lengths) / max(len(texts), 1)
        df = Counter(term for counts in self.terms for term in counts)
        n = len(texts)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    def score(self, i: int, query_terms: list[str]) -> float:
        counts, total = self.terms[i], 0.0
        for term in set(query_terms):
            f = counts.get(term, 0)
            if f:
                norm = K1 * (1 - B + B * self.lengths[i] / self.average)
                total += self.idf[term] * f * (K1 + 1) / (f + norm)
        return total


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder:
    def __init__(self) -> None:
        from openai import OpenAI

        key = os.getenv("OPENAI_API_KEY", "").strip()
        if not key:
            raise RuntimeError("Configure OPENAI_API_KEY for hybrid retrieval")
        self.model = os.getenv("OPENAI_EMBEDDING_MODEL", "").strip() or "text-embedding-3-small"
        self.client = OpenAI(api_key=key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            result = self.client.embeddings.create(model=self.model, input=texts)
        except Exception as exc:
            raise RuntimeError("Embedding request failed") from exc
        return [item.embedding for item in result.data]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def exclusion(chunks: list[Chunk], region: str, today: str) -> list[str]:
    """Why each chunk may not be used ('' means it is eligible evidence)."""
    current: dict[str, int] = {}
    for c in chunks:
        if c.status == "approved" and c.effective_date <= today:
            current[c.doc_id] = max(current.get(c.doc_id, 0), c.version)
    reasons = []
    for c in chunks:
        if c.status != "approved":
            reasons.append(c.status)  # draft or retired
        elif c.effective_date > today:
            reasons.append("not_yet_effective")
        elif c.version != current[c.doc_id]:
            reasons.append("superseded")
        elif c.region not in ("all", region):
            reasons.append("other_region")
        else:
            reasons.append("")
    return reasons


@dataclass(frozen=True)
class Retrieval:
    passages: tuple[Chunk, ...]
    reason: str  # found, no_match or region_needed
    mode: str
    candidates: tuple[dict, ...]
    excluded: dict

    def summary(self) -> dict:
        """IDs, scores and counts only, never passage text: safe to keep in the session."""
        return {"reason": self.reason, "mode": self.mode, "candidates": list(self.candidates),
                "excluded": self.excluded, "passages": [c.chunk_id for c in self.passages]}


class Retriever:
    def __init__(self, chunks: list[Chunk], embedder: Embedder | None = None,
                 min_score: float = MIN_SCORE) -> None:
        self.chunks = chunks
        self.embedder = embedder
        self.min_score = min_score
        self.index = BM25([f"{c.doc_id} {c.title} {c.heading} {c.text}" for c in chunks])
        self._vectors: list[list[float]] | None = None

    def vectors(self) -> list[list[float]]:
        if self._vectors is None:  # embed the corpus once, on first use
            self._vectors = self.embedder.embed([f"{c.title} {c.heading} {c.text}" for c in self.chunks])
        return self._vectors

    def retrieve(self, message: str, *, region: str = "", today: date | str | None = None,
                 k: int = TOP_K) -> Retrieval:
        today = str(today or date.today())
        reasons = exclusion(self.chunks, region, today)
        eligible = [i for i, r in enumerate(reasons) if not r]
        query = tokens(message)
        keyword = {i: self.index.score(i, query) for i in eligible}
        similarity = {i: 0.0 for i in eligible}
        if self.embedder:
            vectors, (q,) = self.vectors(), self.embedder.embed([message])
            similarity = {i: cosine(q, vectors[i]) for i in eligible}
            gate = [i for i in eligible if keyword[i] >= self.min_score or similarity[i] >= MIN_COSINE]
            kw_rank = {i: r for r, i in enumerate(sorted(eligible, key=lambda i: -keyword[i]), 1)}
            vec_rank = {i: r for r, i in enumerate(sorted(eligible, key=lambda i: -similarity[i]), 1)}
            fused = lambda i: -(1 / (RRF_K + kw_rank[i]) + 1 / (RRF_K + vec_rank[i]))  # noqa: E731
            order, ranked = sorted(gate, key=fused), sorted(eligible, key=fused)
        else:
            ranked = sorted(eligible, key=lambda i: -keyword[i])
            order = [i for i in ranked if keyword[i] >= self.min_score]
        passages = tuple(self.chunks[i] for i in order[:k])
        if passages:
            reason = "found"
        elif any(r == "other_region" and self.index.score(i, query) >= self.min_score
                 for i, r in enumerate(reasons)):
            reason = "region_needed"
        else:
            reason = "no_match"
        used = set(order[:k])
        candidates = tuple(
            {"chunk_id": self.chunks[i].chunk_id, "doc_id": self.chunks[i].doc_id,
             "heading": self.chunks[i].heading, "keyword": round(keyword[i], 2),
             "cosine": round(similarity[i], 2), "used": i in used}
            for i in ranked if keyword[i] > 0 or similarity[i] > 0)[:5]
        return Retrieval(passages, reason, "hybrid" if self.embedder else "keyword", candidates,
                         dict(sorted(Counter(r for r in reasons if r).items())))


def evidence_text(passages: tuple[Chunk, ...]) -> str:
    """Numbered, source-tagged passages: the only approved evidence a route may use."""
    return "\n".join(f"[{n}] ({c.doc_id} v{c.version}, {c.title} — {c.heading}) {c.text}"
                     for n, c in enumerate(passages, 1))


def citation(n: int, c: Chunk) -> dict:
    """Built from retrieval metadata, never from what the model wrote."""
    return {"n": n, "doc_id": c.doc_id, "title": c.title, "heading": c.heading,
            "version": c.version, "effective_date": c.effective_date, "source": c.source,
            "chunk_id": c.chunk_id, "excerpt": c.text[:280]}


LABELS = {"": "in use", "not_yet_effective": "not yet effective", "other_region": "other region"}


def corpus_table(chunks: list[Chunk], region: str, today: date | str | None = None) -> list[dict]:
    """One row per document version, using the same rules as the retriever."""
    rows: dict[tuple[str, int], dict] = {}
    for c, reason in zip(chunks, exclusion(chunks, region, str(today or date.today()))):
        row = rows.setdefault((c.doc_id, c.version), {
            "doc_id": c.doc_id, "title": c.title, "version": c.version, "status": c.status,
            "effective_date": c.effective_date, "region": c.region, "source": c.source,
            "chunks": 0, "use_today": LABELS.get(reason, reason)})
        row["chunks"] += 1
    return sorted(rows.values(), key=lambda r: (r["doc_id"], r["version"]))


@functools.cache
def get_retriever() -> Retriever:
    """Ingest once per server process; restart the server after editing data/corpus/."""
    embedder = OpenAIEmbedder() if settings.SUPPORT_RETRIEVAL == "hybrid" else None
    return Retriever(ingest(load_corpus()), embedder)
