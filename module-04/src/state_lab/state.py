"""Pure state transitions. Model output is a proposal, never an authority."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Literal

FactKey = Literal[
    "order_reference", "delivery_status", "contact_channel",
    "reported_symptom", "duration", "medication_name_as_entered",
]
ALLOWED_FACTS = frozenset(FactKey.__args__)
ALLOWED_ROUTES = frozenset({
    "answer_from_approved_info", "ask_clarifying_question", "handoff", "unsupported",
})


@dataclass(frozen=True)
class Fact:
    value: str
    source_event_id: int
    source: str = "reported_by_customer"


@dataclass(frozen=True)
class FactUpdate:
    key: str
    value: str
    operation: Literal["set", "correct"] = "set"


@dataclass(frozen=True)
class Proposal:
    intent: str
    route: str
    missing_information: tuple[str, ...]
    pending_question: str
    response_draft: str
    needs_human_review: bool
    fact_updates: tuple[FactUpdate, ...]


@dataclass(frozen=True)
class ConversationState:
    session_id: str
    created_at: datetime
    expires_at: datetime
    event_number: int = 0
    current_intent: str = ""
    current_facts: dict[str, Fact] = field(default_factory=dict)
    superseded_facts: tuple[tuple[str, Fact], ...] = ()
    missing_information: tuple[str, ...] = ()
    pending_question: str = ""
    last_route: str = ""
    retention_choice: Literal["session_only", "until_expiry"] = "session_only"

    def snapshot(self) -> dict:
        """Return a defensive, customer-reviewable copy (no raw transcript)."""
        return {
            "session_id": self.session_id,
            "current_intent": self.current_intent,
            "current_facts": {
                key: {"value": fact.value, "source": fact.source,
                      "source_event_id": fact.source_event_id}
                for key, fact in self.current_facts.items()
            },
            "missing_information": list(self.missing_information),
            "pending_question": self.pending_question,
            "last_route": self.last_route,
            "retention_choice": self.retention_choice,
            "expires_at": self.expires_at.isoformat(),
        }


def apply_proposal(state: ConversationState, proposal: Proposal, *, approved_policy: str) -> ConversationState:
    """Validate the entire proposal before producing a new immutable state."""
    if proposal.route not in ALLOWED_ROUTES:
        raise ValueError("Unknown route")
    if proposal.needs_human_review != (proposal.route == "handoff"):
        raise ValueError("Handoff and human review disagree")
    if proposal.route == "answer_from_approved_info" and not approved_policy.strip():
        raise ValueError("No approved policy was supplied")
    if proposal.route == "ask_clarifying_question" and not proposal.pending_question.strip():
        raise ValueError("Clarification route needs a question")
    if len(proposal.fact_updates) > 6 or len(proposal.missing_information) > 6:
        raise ValueError("Proposal exceeds state bounds")
    if any(len(s) > 500 for s in (proposal.intent, proposal.pending_question, proposal.response_draft)):
        raise ValueError("Proposal text exceeds bounds")

    facts = state.current_facts.copy()
    superseded = list(state.superseded_facts)
    seen: set[str] = set()
    next_event = state.event_number + 1
    for update in proposal.fact_updates:
        if update.key not in ALLOWED_FACTS or update.key in seen:
            raise ValueError("Unknown or duplicate fact key")
        seen.add(update.key)
        value = update.value.strip()
        if not value or len(value) > 200:
            raise ValueError("Fact value is empty or too long")
        previous = facts.get(update.key)
        if update.operation == "correct":
            if previous is None or previous.value == value:
                raise ValueError("Correction needs a different existing value")
            superseded.append((update.key, previous))
        elif update.operation == "set":
            if previous is not None and previous.value != value:
                raise ValueError("Changed value needs an explicit correction")
        else:
            raise ValueError("Unknown fact operation")
        facts[update.key] = Fact(value=value, source_event_id=next_event)

    if any(not item.strip() or len(item) > 100 for item in proposal.missing_information):
        raise ValueError("Invalid missing information")
    # The superseded list is bounded for the lesson; it is never sent to the model.
    return replace(
        state, event_number=next_event, current_intent=proposal.intent,
        current_facts=facts, superseded_facts=tuple(superseded[-10:]),
        missing_information=proposal.missing_information,
        pending_question=proposal.pending_question if proposal.route == "ask_clarifying_question" else "",
        last_route=proposal.route,
    )


def correct_fact(state: ConversationState, *, key: str, value: str) -> ConversationState:
    """Explicit customer correction, independent of a model call."""
    if key not in ALLOWED_FACTS or key not in state.current_facts:
        raise ValueError("Fact is not present")
    new_value = value.strip()
    if not new_value or len(new_value) > 200 or new_value == state.current_facts[key].value:
        raise ValueError("Correction needs a different, bounded value")
    old = state.current_facts[key]
    facts = state.current_facts.copy()
    facts[key] = Fact(new_value, state.event_number + 1)
    return replace(
        state, event_number=state.event_number + 1, current_facts=facts,
        superseded_facts=(*(state.superseded_facts[-9:]), (key, old)),
        pending_question="", missing_information=tuple(x for x in state.missing_information if x != key),
    )


def choose_retention(state: ConversationState, choice: str) -> ConversationState:
    if choice not in {"session_only", "until_expiry"}:
        raise ValueError("Unknown retention choice")
    return replace(state, retention_choice=choice)
