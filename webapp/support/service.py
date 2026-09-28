"""One application that gains a capability at each course module."""

from __future__ import annotations

import time
from dataclasses import dataclass

from .gateway import Gateway
from .routing import customer_response, parse_route
from .state import apply_proposal, fresh_state, is_expired

MAX_MESSAGE = 4000
MAX_HISTORY = 8


@dataclass(frozen=True)
class Turn:
    status: str
    response: str
    route: str
    model: str
    latency_ms: float
    input_tokens: int | None
    output_tokens: int | None

    def as_dict(self) -> dict:
        return vars(self).copy()


def active_state(session) -> dict:
    state = session.get("m4_state")
    if not state or is_expired(state):
        state = fresh_state()
        session["m4_state"] = state
    return state


def process_turn(*, stage: int, message: str, session, gateway: Gateway,
                 policy: str = "") -> Turn:
    if stage not in (1, 2, 3, 4):
        raise ValueError("Unknown module")
    message = message.strip()
    if not message or len(message) > MAX_MESSAGE:
        raise ValueError("Enter a message of at most 4,000 characters")
    if len(policy) > 8000:
        raise ValueError("Approved policy is too long")
    started = time.perf_counter()
    history_key = "m2_history" if stage == 2 else "m3_history" if stage == 3 else None
    history = list(session.get(history_key, []))[-MAX_HISTORY:] if history_key else []
    messages = history + [{"role": "user", "content": message}]
    state = active_state(session) if stage == 4 else None
    if stage == 4:
        # Module 4 does not retain earlier raw transcript history.
        session.pop("m2_history", None)
        session.pop("m3_history", None)

    try:
        generated = gateway.generate(stage=stage, messages=messages, policy=policy, state=state)
        if not generated.text.strip():
            raise ValueError("Empty model response")
        if stage in (1, 2):
            answer, route = generated.text.strip(), "text"
            if stage == 2:
                session["m2_history"] = (messages + [{"role": "assistant", "content": answer}])[-MAX_HISTORY:]
        else:
            proposal = parse_route(generated.text, policy, stage)
            if stage == 4:
                updated = apply_proposal(state, proposal, policy)
                session["m4_state"] = updated
            answer, route = customer_response(proposal), proposal["route"]
            if stage == 3:
                session["m3_history"] = (messages + [{"role": "assistant", "content": answer}])[-MAX_HISTORY:]
        return Turn("ok", answer, route, generated.model,
                    round((time.perf_counter() - started) * 1000, 2),
                    generated.input_tokens, generated.output_tokens)
    except (ValueError, RuntimeError):
        return Turn("error", "I cannot process that safely right now. Please contact support.",
                    "handoff", "unavailable", round((time.perf_counter() - started) * 1000, 2),
                    None, None)
