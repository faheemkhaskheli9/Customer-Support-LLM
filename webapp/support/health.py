"""Module 7: a clinic support assistant. Code screens for urgent and clinical messages before the model."""

from __future__ import annotations

import functools
import json

from .retrieval import Retriever, get_retriever

# Ordered by level of care. The final category is the more cautious of the code screen and the model.
LEVELS = ("out_of_scope", "clinic_admin", "action_request", "clinical", "emergency")
CLINIC_PREFIX = "CLN-"
# Conservative phrase lists: a miss here is caught only if the model raises the level.
EMERGENCY_TERMS = (
    "chest pain", "can't breathe", "cannot breathe", "trouble breathing", "difficulty breathing",
    "unconscious", "passed out", "severe bleeding", "bleeding heavily", "overdose", "suicid",
    "kill myself", "end my life", "stroke", "face drooping", "seizure", "anaphyla",
)
CLINICAL_TERMS = (
    "dose", "dosage", "diagnos", "symptom", "side effect", "should i take", "prescribe", "fever",
    "pain", "rash", "infection", "headache", "treatment", "is it safe to take",
)
ACTION_TERMS = (
    "book me", "cancel my appointment", "reschedule my", "move my appointment", "refill my",
    "approve my", "renew my prescription",
)

REPLIES = {
    "emergency": ("This may be an emergency. Call your local emergency number now or go to the nearest "
                  "emergency department. This chat cannot help in an emergency."),
    "clinical": ("A clinician needs to answer health questions. I cannot assess symptoms, diagnose, "
                 "prescribe or advise on doses. Please contact the clinic, or your local emergency "
                 "number if it is urgent."),
    "action_request": ("I cannot book, change or cancel appointments or approve refills. The front desk "
                       "or the patient portal can help. No action has been completed."),
    "out_of_scope": "I can answer questions about clinic appointments, first visits and refill requests.",
    "no_evidence": "I do not have approved clinic information on that. The front desk can help.",
}
ROUTES = {"emergency": "handoff", "clinical": "handoff", "action_request": "handoff",
          "out_of_scope": "unsupported", "clinic_admin": "answer_from_approved_info"}


def screen(message: str) -> str:
    """Runs before any model call. Returns the level code alone can establish."""
    lower = message.lower().replace("’", "'")
    for level, terms in (("emergency", EMERGENCY_TERMS), ("clinical", CLINICAL_TERMS),
                         ("action_request", ACTION_TERMS)):
        if any(term in lower for term in terms):
            return level
    return "out_of_scope"


def parse_triage(raw: str) -> str:
    """The model may only name one known category."""
    try:
        result = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Model did not return valid JSON") from exc
    if not isinstance(result, dict) or set(result) != {"category"} or result["category"] not in LEVELS:
        raise ValueError("Invalid triage category")
    return result["category"]


def more_cautious(*categories: str) -> str:
    """The model can raise the level of care, never lower it."""
    return max(categories, key=LEVELS.index)


@functools.cache
def get_clinic_retriever() -> Retriever:
    """Clinic questions retrieve only from approved clinic documents, filtered before ranking."""
    base = get_retriever()
    return Retriever([c for c in base.chunks if c.doc_id.startswith(CLINIC_PREFIX)], base.embedder)
