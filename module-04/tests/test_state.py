import json
from datetime import datetime, timedelta, timezone

import pytest

from state_lab.router import SupportRouter, parse_proposal
from state_lab.service import SupportService
from state_lab.state import FactUpdate, Proposal, apply_proposal
from state_lab.store import MemoryStore, SessionNotFound


class ScriptedGenerator:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.inputs = []

    def generate(self, *, instructions, user_input):
        self.inputs.append(json.loads(user_input))
        return next(self.responses)


def payload(*, route="ask_clarifying_question", updates=None, question="What is the order number?",
            missing=None, response="", intent="order_status"):
    return json.dumps({
        "intent": intent, "route": route,
        "missing_information": missing if missing is not None else (["order_reference"] if route == "ask_clarifying_question" else []),
        "pending_question": question if route == "ask_clarifying_question" else "",
        "response_draft": response, "needs_human_review": route == "handoff",
        "fact_updates": updates or [],
    })


def service_with(*responses, clock=None):
    store = MemoryStore(clock=clock)
    generator = ScriptedGenerator(*responses)
    return SupportService(store, SupportRouter(generator)), generator


def test_multiturn_clarification_and_bounded_context():
    service, generator = service_with(
        payload(),
        payload(route="handoff", updates=[{"key": "order_reference", "value": "B456", "operation": "set"}]),
    )
    sid = service.start(owner_id="alice")["session_id"]
    first = service.turn(owner_id="alice", session_id=sid, message="Where is my order?")
    assert first.response == "What is the order number?"
    second = service.turn(owner_id="alice", session_id=sid, message="It is B456")
    assert second.state["current_facts"]["order_reference"]["value"] == "B456"
    assert generator.inputs[1]["state"]["pending_question"] == "What is the order number?"
    assert "customer_message" not in generator.inputs[1]["state"]
    assert second.response.endswith("No action has been completed.")


def test_explicit_correction_supersedes_old_value():
    service, _ = service_with(payload(route="handoff", updates=[
        {"key": "order_reference", "value": "A123", "operation": "set"}]))
    sid = service.start(owner_id="alice")["session_id"]
    service.turn(owner_id="alice", session_id=sid, message="Order A123")
    changed = service.correct(owner_id="alice", session_id=sid, key="order_reference", value="B456")
    assert changed["current_facts"]["order_reference"]["value"] == "B456"
    internal = service.store.get("alice", sid)
    assert internal.superseded_facts[-1][1].value == "A123"


def test_model_correction_requires_explicit_operation():
    service, _ = service_with(
        payload(route="handoff", updates=[{"key": "order_reference", "value": "A123", "operation": "set"}]),
        payload(route="handoff", updates=[{"key": "order_reference", "value": "B456", "operation": "set"}]),
        payload(route="handoff", updates=[{"key": "order_reference", "value": "B456", "operation": "correct"}]),
    )
    sid = service.start(owner_id="alice")["session_id"]
    service.turn(owner_id="alice", session_id=sid, message="A123")
    invalid = service.turn(owner_id="alice", session_id=sid, message="Actually B456")
    assert invalid.status == "error"
    assert service.review(owner_id="alice", session_id=sid)["current_facts"]["order_reference"]["value"] == "A123"
    valid = service.turn(owner_id="alice", session_id=sid, message="Correction: B456")
    assert valid.state["current_facts"]["order_reference"]["value"] == "B456"


def test_no_cross_owner_read_write_or_delete():
    service, _ = service_with()
    sid = service.start(owner_id="alice")["session_id"]
    with pytest.raises(SessionNotFound):
        service.review(owner_id="bob", session_id=sid)
    with pytest.raises(SessionNotFound):
        service.correct(owner_id="bob", session_id=sid, key="order_reference", value="X")
    assert service.delete(owner_id="bob", session_id=sid) is False
    assert service.review(owner_id="alice", session_id=sid)["session_id"] == sid


def test_expiry_is_fixed_and_deletion_is_verifiable():
    now = [datetime(2026, 9, 26, tzinfo=timezone.utc)]
    service, _ = service_with(clock=lambda: now[0])
    sid = service.start(owner_id="alice")["session_id"]
    service.set_retention(owner_id="alice", session_id=sid, choice="until_expiry")
    assert service.delete(owner_id="alice", session_id=sid)
    with pytest.raises(SessionNotFound):
        service.review(owner_id="alice", session_id=sid)
    sid2 = service.start(owner_id="alice")["session_id"]
    now[0] += timedelta(minutes=30)
    with pytest.raises(SessionNotFound):
        service.review(owner_id="alice", session_id=sid2)


@pytest.mark.parametrize("bad", [
    "not-json", "[]", json.dumps({"route": "handoff"}),
    payload(route="handoff").replace('"needs_human_review": true', '"needs_human_review": "yes"'),
    payload(route="handoff", updates=[{"key": "order_reference", "value": "A", "operation": "bad"}]),
    payload(route="handoff", updates=[{"key": "bad", "value": "A", "operation": "set"}]),
])
def test_bad_model_shapes_do_not_mutate_state(bad):
    service, _ = service_with(bad)
    sid = service.start(owner_id="alice")["session_id"]
    result = service.turn(owner_id="alice", session_id=sid, message="hello")
    assert result.status == "error"
    assert service.store.get("alice", sid).event_number == 0


def test_no_policy_answer_and_handoff_response_is_app_owned():
    service, _ = service_with(
        payload(route="answer_from_approved_info", response="Warranty is 9 years."),
        payload(route="handoff", response="Your order has been cancelled."),
    )
    sid = service.start(owner_id="alice")["session_id"]
    assert service.turn(owner_id="alice", session_id=sid, message="Warranty?").status == "error"
    result = service.turn(owner_id="alice", session_id=sid, message="Cancel it")
    assert result.route == "handoff"
    assert "cancelled" not in result.response


def test_snapshot_cannot_mutate_store():
    service, _ = service_with()
    sid = service.start(owner_id="alice")["session_id"]
    snapshot = service.review(owner_id="alice", session_id=sid)
    snapshot["current_facts"]["order_reference"] = {"value": "fake"}
    assert service.review(owner_id="alice", session_id=sid)["current_facts"] == {}


def test_rejects_duplicate_update_and_atomicity():
    service, _ = service_with(payload(route="handoff", updates=[
        {"key": "order_reference", "value": "A", "operation": "set"},
        {"key": "order_reference", "value": "B", "operation": "correct"},
    ]))
    sid = service.start(owner_id="alice")["session_id"]
    assert service.turn(owner_id="alice", session_id=sid, message="A or B").status == "error"
    assert service.review(owner_id="alice", session_id=sid)["current_facts"] == {}


def test_retention_choice_is_explicit_and_invalid_choice_rejected():
    service, _ = service_with()
    sid = service.start(owner_id="alice")["session_id"]
    assert service.set_retention(owner_id="alice", session_id=sid, choice="until_expiry")["retention_choice"] == "until_expiry"
    with pytest.raises(ValueError):
        service.set_retention(owner_id="alice", session_id=sid, choice="forever")


def test_close_clears_default_session_but_opted_in_lives_until_ttl():
    service, _ = service_with()
    transient = service.start(owner_id="alice")["session_id"]
    retained = service.start(owner_id="alice")["session_id"]
    service.set_retention(owner_id="alice", session_id=retained, choice="until_expiry")
    assert service.close(owner_id="alice", session_id=transient) is True
    assert service.close(owner_id="alice", session_id=retained) is False
    with pytest.raises(SessionNotFound):
        service.review(owner_id="alice", session_id=transient)
    assert service.review(owner_id="alice", session_id=retained)["session_id"] == retained


def test_parser_rejects_non_string_fact_value_and_route_list():
    with pytest.raises(ValueError):
        parse_proposal(payload(route="handoff", updates=[{"key": "order_reference", "value": 123, "operation": "set"}]))
    bad = json.loads(payload())
    bad["route"] = []
    with pytest.raises(ValueError):
        parse_proposal(json.dumps(bad))
