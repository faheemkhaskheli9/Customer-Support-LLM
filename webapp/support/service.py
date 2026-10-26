"""One application that gains a capability at each course module."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace

from .gateway import Gateway
from .retrieval import Retrieval, Retriever, citation, evidence_text, get_retriever
from .routing import customer_response, parse_grounded, parse_route
from .state import apply_proposal, fresh_state, is_expired

MAX_MESSAGE = 4000
MAX_HISTORY = 8
REGION_REPLY = "The answer depends on your delivery region. Choose your region and ask again."
UNCONFIRMED = "I could not confirm that from approved information. A support professional can help."
FAILED = "I cannot process that safely right now. Please contact support."


@dataclass(frozen=True)
class Turn:
    status: str
    response: str
    route: str
    model: str
    latency_ms: float
    input_tokens: int | None
    output_tokens: int | None
    sources: tuple = ()            # Module 5: citations built from retrieval metadata
    retrieval: dict | None = None  # Module 5: why evidence was or was not used

    def as_dict(self) -> dict:
        return vars(self).copy()


def active_state(session) -> dict:
    state = session.get("m4_state")
    if not state or is_expired(state):
        state = fresh_state()
        session["m4_state"] = state
    return state


def clean(message: str) -> str:
    message = message.strip()
    if not message or len(message) > MAX_MESSAGE:
        raise ValueError("Enter a message of at most 4,000 characters")
    return message


def process_turn(*, stage: int, message: str, session, gateway: Gateway,
                 policy: str = "") -> Turn:
    if stage not in (1, 2, 3, 4):
        raise ValueError("Unknown module")
    message = clean(message)
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
        return Turn("error", FAILED, "handoff", "unavailable", round((time.perf_counter() - started) * 1000, 2),
                    None, None)


def _add(a: int | None, b: int | None) -> int | None:
    return None if a is None or b is None else a + b


def ground(turn: Turn, *, gateway: Gateway, message: str, retrieval: Retrieval,
           history: list | None = None, facts: dict | None = None) -> Turn:
    """Module 5: cite retrieved passages, or reply from code. Only an answer route calls the model."""
    info = retrieval.summary()
    if turn.route != "answer_from_approved_info":
        if turn.route == "unsupported" and retrieval.reason == "region_needed":
            return replace(turn, response=REGION_REPLY, retrieval={**info, "grounding": "region_needed"})
        grounding = "no_evidence" if turn.route == "unsupported" and not retrieval.passages else "not_answered"
        return replace(turn, retrieval={**info, "grounding": grounding})
    latest = json.dumps({
        "customer_message": message, "reported_facts": facts or {},
        "passages": [{"n": n, "source": f"{c.doc_id} v{c.version} — {c.title}: {c.heading}", "text": c.text}
                     for n, c in enumerate(retrieval.passages, 1)],
    }, ensure_ascii=False)
    try:
        generated = gateway.generate(stage=5, messages=list(history or []) + [{"role": "user", "content": latest}])
        answer, used = parse_grounded(generated.text, len(retrieval.passages))
    except (ValueError, RuntimeError):
        return replace(turn, response=UNCONFIRMED, route="handoff",
                       retrieval={**info, "grounding": "invalid_output"})
    turn = replace(turn, model=generated.model,
                   input_tokens=_add(turn.input_tokens, generated.input_tokens),
                   output_tokens=_add(turn.output_tokens, generated.output_tokens))
    if not answer:
        return replace(turn, response=UNCONFIRMED, route="handoff", retrieval={**info, "grounding": "declined"})
    return replace(turn, response=answer,
                   sources=tuple(citation(n, retrieval.passages[n - 1]) for n in used),
                   retrieval={**info, "grounding": "cited"})


def rag_turn(*, message: str, gateway: Gateway, region: str = "",
             retriever: Retriever | None = None, today=None) -> Turn:
    """The Module 5 page: retrieve, route with the Module 3 contract, then ground."""
    started = time.perf_counter()
    message = clean(message)
    retrieval = (retriever or get_retriever()).retrieve(message, region=region, today=today)
    evidence = evidence_text(retrieval.passages)
    try:
        generated = gateway.generate(stage=3, messages=[{"role": "user", "content": message}], policy=evidence)
        route = parse_route(generated.text, evidence, 3)
    except (ValueError, RuntimeError):
        return Turn("error", FAILED, "handoff", "unavailable",
                    round((time.perf_counter() - started) * 1000, 2), None, None,
                    retrieval={**retrieval.summary(), "grounding": "router_error"})
    turn = Turn("ok", customer_response(route), route["route"], generated.model, 0.0,
                generated.input_tokens, generated.output_tokens)
    turn = ground(turn, gateway=gateway, message=message, retrieval=retrieval)
    return replace(turn, latency_ms=round((time.perf_counter() - started) * 1000, 2))


def agent_turn(*, message: str, session, gateway: Gateway, region: str = "",
               retriever: Retriever | None = None) -> Turn:
    """The main support agent: every module's feature in one conversation.

    Module 5 retrieves approved passages. Modules 3-4 route the message with only those
    passages as evidence and update reported facts (invalid output commits nothing).
    Module 5 grounds an approved-information route, with Module 2 context and Module 4
    facts in the request. Module 1 metrics cover both model calls.
    """
    started = time.perf_counter()
    message = clean(message)
    retrieval = (retriever or get_retriever()).retrieve(message, region=region)
    turn = process_turn(stage=4, message=message, session=session, gateway=gateway,
                        policy=evidence_text(retrieval.passages))
    if turn.status != "ok":
        return turn  # failed turns are not committed to history
    history = list(session.get("agent_history", []))[-MAX_HISTORY:]
    facts = {k: v["value"] for k, v in session["m4_state"]["current_facts"].items()}
    turn = ground(turn, gateway=gateway, message=message, retrieval=retrieval, history=history, facts=facts)
    session["agent_history"] = (history + [{"role": "user", "content": message},
                                           {"role": "assistant", "content": turn.response}])[-MAX_HISTORY:]
    return replace(turn, latency_ms=round((time.perf_counter() - started) * 1000, 2))
