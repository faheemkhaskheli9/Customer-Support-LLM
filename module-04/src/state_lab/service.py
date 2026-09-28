"""The application boundary: owner scoping, validation, fallback, and state commits."""

from __future__ import annotations

from dataclasses import dataclass

from .router import SupportRouter
from .state import apply_proposal, choose_retention, correct_fact
from .store import MemoryStore


@dataclass(frozen=True)
class TurnResult:
    status: str
    route: str
    response: str
    state: dict


class SupportService:
    def __init__(self, store: MemoryStore, router: SupportRouter) -> None:
        self.store = store
        self.router = router

    def start(self, *, owner_id: str) -> dict:
        return self.store.create(owner_id).snapshot()

    def review(self, *, owner_id: str, session_id: str) -> dict:
        return self.store.get(owner_id, session_id).snapshot()

    def turn(self, *, owner_id: str, session_id: str, message: str,
             approved_policy: str = "") -> TurnResult:
        state = self.store.get(owner_id, session_id)
        if not message.strip() or len(message) > 4000 or len(approved_policy) > 8000:
            raise ValueError("Invalid message or policy length")
        try:
            proposal = self.router.propose(message=message, state=state, approved_policy=approved_policy)
            updated = apply_proposal(state, proposal, approved_policy=approved_policy)
        except (ValueError, RuntimeError):
            # Invalid output is an error; never commit a partial state change.
            return TurnResult("error", "handoff",
                              "I can't process that safely right now. Please contact support.",
                              state.snapshot())
        self.store.save(owner_id, updated)
        if proposal.route == "handoff":
            response = "This needs a support professional to review it. No action has been completed."
        elif proposal.route == "unsupported":
            response = "I don't have approved information to answer that request."
        elif proposal.route == "ask_clarifying_question":
            response = proposal.pending_question
        else:
            response = proposal.response_draft
        return TurnResult("ok", proposal.route, response, updated.snapshot())

    def correct(self, *, owner_id: str, session_id: str, key: str, value: str) -> dict:
        state = self.store.get(owner_id, session_id)
        updated = correct_fact(state, key=key, value=value)
        self.store.save(owner_id, updated)
        return updated.snapshot()

    def set_retention(self, *, owner_id: str, session_id: str, choice: str) -> dict:
        state = self.store.get(owner_id, session_id)
        updated = choose_retention(state, choice)
        self.store.save(owner_id, updated)
        return updated.snapshot()

    def delete(self, *, owner_id: str, session_id: str) -> bool:
        return self.store.delete(owner_id, session_id)

    def close(self, *, owner_id: str, session_id: str) -> bool:
        """End a session; only an explicit opt-in stays in this process until TTL."""
        state = self.store.get(owner_id, session_id)
        if state.retention_choice == "session_only":
            return self.store.delete(owner_id, session_id)
        return False
