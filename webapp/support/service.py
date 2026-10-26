"""One application that gains a capability at each course module."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, replace

from .gateway import Gateway
from .health import REPLIES as HEALTH_REPLIES, ROUTES as HEALTH_ROUTES, get_clinic_retriever, more_cautious, parse_triage, screen
from .retrieval import Retrieval, Retriever, citation, evidence_text, get_retriever
from .routing import customer_response, parse_grounded, parse_route
from .state import apply_proposal, fresh_state, is_expired
from .tools import (CLARIFY, HANDOFF, MAX_AUDIT, UNSUPPORTED, Orders, audit_entry, describe,
                    parse_tool_request, run_tool)

MAX_MESSAGE = 4000
MAX_HISTORY = 8
REGION_REPLY = "The answer depends on your delivery region. Choose your region and ask again."
UNCONFIRMED = "I could not confirm that from approved information. A support professional can help."
FAILED = "I cannot process that safely right now. Please contact support."
AGENT_SCREENED = ("emergency", "clinical")  # clinic booking phrases do not apply to the shop agent


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
    tool: dict | None = None       # Module 6: the checked tool call and its record
    safety: dict | None = None     # Module 7: code screen, model proposal and final category

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
               retriever: Retriever | None = None, orders: Orders | None = None) -> Turn:
    """The main support agent: every module's feature in one conversation.

    Module 5 retrieves approved passages. Modules 3-4 route the message with only those
    passages as evidence and update reported facts (invalid output commits nothing).
    Module 6 looks up an order in play with the read-only tool. Otherwise Module 5 grounds an
    approved-information route, with Module 2 context and Module 4 facts in the request.
    Module 1 metrics cover every model call. Module 7 screens first: an emergency or clinical
    message gets the code-written reply, calls no model and is kept nowhere in the session.
    """
    started = time.perf_counter()
    message = clean(message)
    screened = screen(message)
    if screened in AGENT_SCREENED:
        return Turn("ok", HEALTH_REPLIES[screened], "handoff", "not called",
                    round((time.perf_counter() - started) * 1000, 2), None, None,
                    safety={"screen": screened, "proposed": "not asked", "category": screened})
    retrieval = (retriever or get_retriever()).retrieve(message, region=region)
    turn = process_turn(stage=4, message=message, session=session, gateway=gateway,
                        policy=evidence_text(retrieval.passages))
    if turn.status != "ok":
        return turn  # failed turns are not committed to history
    history = list(session.get("agent_history", []))[-MAX_HISTORY:]
    facts = {k: v["value"] for k, v in session["m4_state"]["current_facts"].items()}
    turn = order_lookup(turn, gateway=gateway, message=message, session=session, orders=orders)
    if turn.tool:
        turn = replace(turn, retrieval={**retrieval.summary(), "grounding": "order_tool"})
    else:
        turn = ground(turn, gateway=gateway, message=message, retrieval=retrieval, history=history, facts=facts)
    session["agent_history"] = (history + [{"role": "user", "content": message},
                                           {"role": "assistant", "content": turn.response}])[-MAX_HISTORY:]
    return replace(turn, latency_ms=round((time.perf_counter() - started) * 1000, 2))


def tool_turn(*, message: str, session, gateway: Gateway, orders: Orders | None = None,
              now=None) -> Turn:
    """The Module 6 page: the model proposes a read-only call; code authorizes, runs and replies.

    Invalid model output runs no tool and records nothing. Every executed decision is audited.
    """
    started = time.perf_counter()
    message = clean(message)
    try:
        generated = gateway.generate(stage=6, messages=[{"role": "user", "content": message}])
        request = parse_tool_request(generated.text)
    except (ValueError, RuntimeError):
        return Turn("error", FAILED, "handoff", "unavailable",
                    round((time.perf_counter() - started) * 1000, 2), None, None)
    turn = Turn("ok", "", request["route"], generated.model, 0.0,
                generated.input_tokens, generated.output_tokens)
    if request["route"] != "use_tool":
        reply = {"ask_clarifying_question": CLARIFY, "handoff": HANDOFF}.get(request["route"], UNSUPPORTED)
        return replace(turn, response=reply, latency_ms=round((time.perf_counter() - started) * 1000, 2))
    return replace(turn, **lookup(request, session=session, orders=orders, now=now),
                   latency_ms=round((time.perf_counter() - started) * 1000, 2))


def lookup(request: dict, *, session, orders: Orders | None = None, now=None) -> dict:
    """Run a validated tool request for the signed-in customer, count it and audit it."""
    customer = session.get("customer", "")
    result = run_tool(request, customer=customer, lookups=session.get("m6_lookups", 0),
                      orders=orders, now=now)
    if result.decision in ("allowed", "denied", "not_found"):
        session["m6_lookups"] = session.get("m6_lookups", 0) + 1
    session["tool_audit"] = (list(session.get("tool_audit", [])) + [audit_entry(result, customer, now)])[-MAX_AUDIT:]
    route = "use_tool" if result.decision == "allowed" else "handoff" if result.decision == "rate_limited" else "ask_clarifying_question"
    return {"response": describe(result), "route": route, "tool": result.as_dict()}


def health_turn(*, message: str, gateway: Gateway, retriever: Retriever | None = None,
                today=None) -> Turn:
    """The Module 7 page: code screens first; only clinic admin questions reach retrieval.

    An emergency never calls the model. The model's category can raise the level of care,
    never lower it. Nothing from the message is kept in the session.
    """
    started = time.perf_counter()
    message = clean(message)
    screened = screen(message)
    safety = {"screen": screened, "proposed": "not asked", "category": screened}

    def done(turn: Turn) -> Turn:
        return replace(turn, latency_ms=round((time.perf_counter() - started) * 1000, 2))

    if screened == "emergency":
        return done(Turn("ok", HEALTH_REPLIES["emergency"], "handoff", "not called", 0.0, None, None,
                         safety=safety))
    try:
        generated = gateway.generate(stage=7, messages=[{"role": "user", "content": message}])
        proposed = parse_triage(generated.text)
    except (ValueError, RuntimeError):
        return done(Turn("error", FAILED, "handoff", "unavailable", 0.0, None, None, safety=safety))
    category = more_cautious(screened, proposed)
    safety = {**safety, "proposed": proposed, "category": category}
    turn = Turn("ok", HEALTH_REPLIES.get(category, ""), HEALTH_ROUTES[category], generated.model, 0.0,
                generated.input_tokens, generated.output_tokens, safety=safety)
    if category != "clinic_admin":
        return done(turn)
    retrieval = (retriever or get_clinic_retriever()).retrieve(message, today=today)
    if not retrieval.passages:
        return done(replace(turn, response=HEALTH_REPLIES["no_evidence"], route="unsupported",
                            retrieval={**retrieval.summary(), "grounding": "no_evidence"}))
    return done(ground(turn, gateway=gateway, message=message, retrieval=retrieval))


def order_lookup(turn: Turn, *, gateway: Gateway, message: str, session, orders: Orders | None = None,
                 now=None) -> Turn:
    """Module 6 in the agent: only when an order reference is in play, and never on a handoff proposal.

    The tool proposer sees the message; a clarifying proposal is filled from the reported
    order_reference fact. The tool still checks sign-in and ownership, so a reported number
    can never show someone else's order. Invalid proposer output keeps the Module 4 reply.
    """
    state = session["m4_state"]
    fact = state["current_facts"].get("order_reference")
    if (turn.route == "answer_from_approved_info" or not fact
            or (fact["source_event_id"] != state["event_number"] and "order" not in message.lower())):
        return turn
    try:
        generated = gateway.generate(stage=6, messages=[{"role": "user", "content": message}])
        request = parse_tool_request(generated.text)
        if request["route"] == "ask_clarifying_question":
            request = parse_tool_request(json.dumps({"route": "use_tool", "tool": "order_status",
                                                     "arguments": {"order_reference": fact["value"]}}))
    except (ValueError, RuntimeError):
        return turn
    turn = replace(turn, input_tokens=_add(turn.input_tokens, generated.input_tokens),
                   output_tokens=_add(turn.output_tokens, generated.output_tokens))
    if request["route"] != "use_tool":
        return turn
    return replace(turn, **lookup(request, session=session, orders=orders, now=now))
