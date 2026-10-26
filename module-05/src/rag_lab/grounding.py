"""The grounded-answer boundary, an extractive offline generator and an optional OpenAI adapter."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Protocol

ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "grounded_answer_v1.txt"
MAX_ANSWER = 1200
# Heuristic with a known limit: it catches common completed-action phrasing, not every paraphrase.
ACTIONS = r"(?:approved|refunded|cancell?ed|processed|issued|reversed|booked|rescheduled|prescribed|changed|completed)"
ACTION_CLAIM = re.compile(rf"\b(?:(?:has|have|had)\s+been|was|were|I(?:'ve|\s+have)?)\s+{ACTIONS}\b", re.I)
SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
WORD_RE = re.compile(r"[a-z0-9]+")


class Generator(Protocol):
    def generate(self, *, instructions: str, user_input: str) -> str: ...


def parse_grounded(raw: str, passage_count: int) -> tuple[str, list[int]]:
    """The model may only point at passage numbers it was given."""
    try:
        result = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Model did not return valid JSON") from exc
    if not isinstance(result, dict) or set(result) != {"answer", "used_passages"}:
        raise ValueError("Grounded answer keys differ")
    answer, used = result["answer"], result["used_passages"]
    if not isinstance(answer, str) or len(answer) > MAX_ANSWER:
        raise ValueError("Invalid answer text")
    if (not isinstance(used, list) or len(set(map(str, used))) != len(used)
            or any(type(n) is not int or not 1 <= n <= passage_count for n in used)):
        raise ValueError("Citation refers to a passage that was not retrieved")
    answer = answer.strip()
    if not answer:
        return "", []  # a decline: the passages do not answer the question
    if not used:
        raise ValueError("Answer has no citation")
    if ACTION_CLAIM.search(answer):
        raise ValueError("Answer claims an action was completed")
    return answer, used


def _words(text: str) -> set[str]:
    return {w[:5] for w in WORD_RE.findall(text.lower()) if len(w) > 2} - {"the", "and", "you", "can", "what", "your", "for"}


class ExtractiveGenerator:
    """Offline stand-in for a model: quote the best-overlapping passage, cite it.

    Passages rank by their best sentence's overlap with the question; only when no sentence
    overlaps does the passage source (code, title, heading) decide. A tie keeps the
    higher-ranked passage.
    """

    model = "offline-extractive"

    def generate(self, *, instructions: str, user_input: str) -> str:
        request = json.loads(user_input)
        question = _words(request["customer_message"])
        best = None
        for passage in request["passages"]:
            sentences = SENTENCE_RE.split(passage["text"])
            scores = [len(question & _words(s)) for s in sentences]
            rank = (max(scores), 0 if max(scores) else len(question & _words(passage["source"])))
            if rank > (0, 0) and (best is None or rank > best[0]):
                best = (rank, passage["n"], sentences, scores)
        if best is None:
            return json.dumps({"answer": "", "used_passages": []})
        _, n, sentences, scores = best
        keep = sorted(sorted(range(len(sentences)), key=lambda i: -scores[i])[:2])
        answer = " ".join(sentences[i] for i in keep if scores[i] > 0 or not any(scores))
        return json.dumps({"answer": answer, "used_passages": [n]})


class OpenAITextGenerator:
    def __init__(self) -> None:
        try:
            from dotenv import load_dotenv
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError('Install live extras with: pip install -e ".[live]"') from exc
        load_dotenv(ROOT / ".env")
        key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip()
        if not key or not model:
            raise RuntimeError("Set OPENAI_API_KEY and OPENAI_MODEL in module-05/.env")
        self.client = OpenAI(api_key=key)
        self.model = model

    def generate(self, *, instructions: str, user_input: str) -> str:
        try:
            response = self.client.responses.create(
                model=self.model, instructions=instructions,
                input=[{"role": "user", "content": user_input}],
            )
        except Exception as exc:
            raise RuntimeError("Model call failed; inspect provider logs") from exc
        if not response.output_text.strip():
            raise RuntimeError("Empty model response")
        return response.output_text
