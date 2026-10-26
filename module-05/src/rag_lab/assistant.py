"""Retrieve first, answer only from retrieved passages, cite from metadata."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date

from .grounding import PROMPT_PATH, Generator, parse_grounded
from .retrieval import Retriever, citation

MAX_MESSAGE = 4000
NO_EVIDENCE = "I do not have approved information to answer that request."
REGION_REPLY = "The answer depends on your delivery region. Choose your region and ask again."
HANDOFF = "A support professional needs to review this. No action has been completed."
UNCONFIRMED = "I could not confirm that from approved information. A support professional can help."
# A small keyword guard in place of the Module 3-4 model router: actions, account changes,
# instruction overrides and clinical questions always go to a person.
HANDOFF_WORDS = ("refund", "cancel", "change my account", "dose", "diagnos", "treatment", "symptom",
                 "headache", "fever", "prescribe")


@dataclass(frozen=True)
class Answer:
    route: str
    response: str
    grounding: str  # cited, declined, invalid_output, no_evidence, region_needed or guarded
    sources: tuple = ()
    retrieval: dict = field(default_factory=dict)  # IDs, scores and counts only


def guarded(message: str) -> bool:
    lower = message.lower()
    return any(word in lower for word in HANDOFF_WORDS) or ("ignore" in lower and "instruction" in lower)


class GroundedAssistant:
    def __init__(self, retriever: Retriever, generator: Generator) -> None:
        self.retriever = retriever
        self.generator = generator
        self.instructions = PROMPT_PATH.read_text(encoding="utf-8").strip()

    def answer(self, message: str, *, region: str = "", today: date | str | None = None) -> Answer:
        message = message.strip()
        if not message or len(message) > MAX_MESSAGE:
            raise ValueError("Enter a message of at most 4,000 characters")
        if guarded(message):
            return Answer("handoff", HANDOFF, "guarded")
        retrieval = self.retriever.retrieve(message, region=region, today=today)
        info = retrieval.summary()
        if not retrieval.passages:  # a miss never calls the model
            if retrieval.reason == "region_needed":
                return Answer("unsupported", REGION_REPLY, "region_needed", retrieval=info)
            return Answer("unsupported", NO_EVIDENCE, "no_evidence", retrieval=info)
        user_input = json.dumps({
            "customer_message": message,
            "passages": [{"n": n, "source": f"{c.doc_id} v{c.version} — {c.title}: {c.heading}", "text": c.text}
                         for n, c in enumerate(retrieval.passages, 1)],
        }, ensure_ascii=False)
        try:
            text, used = parse_grounded(self.generator.generate(instructions=self.instructions,
                                                                user_input=user_input),
                                        len(retrieval.passages))
        except (ValueError, RuntimeError):
            return Answer("handoff", UNCONFIRMED, "invalid_output", retrieval=info)
        if not text:
            return Answer("handoff", UNCONFIRMED, "declined", retrieval=info)
        return Answer("answer_from_approved_info", text, "cited",
                      tuple(citation(n, retrieval.passages[n - 1]) for n in used), info)
