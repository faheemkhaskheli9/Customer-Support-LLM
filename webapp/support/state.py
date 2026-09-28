"""Module 4 working state; JSON-friendly for Django's server-side session store."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

ALLOWED_FACTS = {
    "order_reference", "delivery_status", "contact_channel",
    "reported_symptom", "duration", "medication_name_as_entered",
}
TTL = timedelta(minutes=30)


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def fresh_state(now: datetime | None = None) -> dict:
    now = now or now_utc()
    return {
        "created_at": now.isoformat(), "expires_at": (now + TTL).isoformat(),
        "event_number": 0, "current_intent": "", "current_facts": {},
        "superseded_facts": [], "missing_information": [], "pending_question": "",
        "last_route": "", "retention_choice": "session_only",
    }


def is_expired(state: dict, now: datetime | None = None) -> bool:
    return (now or now_utc()) >= datetime.fromisoformat(state["expires_at"])


def apply_proposal(state: dict, proposal: dict, policy: str) -> dict:
    """Reject the complete update before writing anything to the Django session."""
    from .routing import validate_route

    validate_route(proposal, policy, stage=4)
    updates = proposal["fact_updates"]
    if len(updates) > 6 or len(proposal["missing_information"]) > 6:
        raise ValueError("State update is too large")
    result = deepcopy(state)
    seen: set[str] = set()
    event = result["event_number"] + 1
    for update in updates:
        key, value, operation = update["key"], update["value"].strip(), update["operation"]
        if key not in ALLOWED_FACTS or key in seen or not value or len(value) > 200:
            raise ValueError("Invalid or duplicate fact")
        seen.add(key)
        previous = result["current_facts"].get(key)
        if operation == "correct":
            if not previous or previous["value"] == value:
                raise ValueError("Correction requires a different existing value")
            result["superseded_facts"].append({"key": key, **previous})
        elif operation == "set":
            if previous and previous["value"] != value:
                raise ValueError("Changed value requires an explicit correction")
        else:
            raise ValueError("Invalid fact operation")
        result["current_facts"][key] = {
            "value": value, "source": "reported_by_customer", "source_event_id": event,
        }
    result["superseded_facts"] = result["superseded_facts"][-10:]
    result["event_number"] = event
    result["current_intent"] = proposal["intent"]
    result["missing_information"] = proposal["missing_information"]
    result["pending_question"] = proposal["pending_question"] if proposal["route"] == "ask_clarifying_question" else ""
    result["last_route"] = proposal["route"]
    return result


def correct_fact(state: dict, key: str, value: str) -> dict:
    value = value.strip()
    if key not in ALLOWED_FACTS or key not in state["current_facts"]:
        raise ValueError("Fact is not present")
    if not value or len(value) > 200 or value == state["current_facts"][key]["value"]:
        raise ValueError("Correction needs a different value of at most 200 characters")
    result = deepcopy(state)
    result["superseded_facts"].append({"key": key, **result["current_facts"][key]})
    result["superseded_facts"] = result["superseded_facts"][-10:]
    result["event_number"] += 1
    result["current_facts"][key] = {
        "value": value, "source": "reported_by_customer",
        "source_event_id": result["event_number"],
    }
    result["missing_information"] = [item for item in result["missing_information"] if item != key]
    result["pending_question"] = ""
    return result
