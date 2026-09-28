"""Modules 3 and 4: strict model JSON validation and application-owned routes."""

from __future__ import annotations

import json

from .gateway import ROUTES
from .state import ALLOWED_FACTS

COMMON = {"intent", "route", "missing_information", "response_draft", "needs_human_review"}
STAGE3 = COMMON | {"summary"}
STAGE4 = COMMON | {"pending_question", "fact_updates"}


def parse_route(raw: str, policy: str, stage: int) -> dict:
    try:
        result = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Model did not return valid JSON") from exc
    validate_route(result, policy, stage)
    return result


def validate_route(result: dict, policy: str, stage: int) -> None:
    required = STAGE3 if stage == 3 else STAGE4
    if not isinstance(result, dict) or set(result) != required:
        raise ValueError("Route schema keys differ")
    if not isinstance(result["route"], str) or result["route"] not in ROUTES:
        raise ValueError("Unknown route")
    text_keys = ("intent", "response_draft", "summary") if stage == 3 else ("intent", "response_draft", "pending_question")
    if any(not isinstance(result[k], str) or len(result[k]) > 500 for k in text_keys):
        raise ValueError("Invalid text field")
    missing = result["missing_information"]
    if not isinstance(missing, list) or len(missing) > 6 or any(not isinstance(x, str) or not x.strip() or len(x) > 100 for x in missing):
        raise ValueError("Invalid missing information")
    if not isinstance(result["needs_human_review"], bool) or result["needs_human_review"] != (result["route"] == "handoff"):
        raise ValueError("Inconsistent handoff flag")
    if result["route"] == "answer_from_approved_info" and not policy.strip():
        raise ValueError("Policy answer without approved evidence")
    if stage == 4:
        if result["route"] == "ask_clarifying_question" and not result["pending_question"].strip():
            raise ValueError("Clarification requires a question")
        updates = result["fact_updates"]
        if not isinstance(updates, list) or len(updates) > 6:
            raise ValueError("Invalid fact updates")
        for item in updates:
            if not isinstance(item, dict) or set(item) != {"key", "value", "operation"}:
                raise ValueError("Invalid fact shape")
            if (not isinstance(item["key"], str) or item["key"] not in ALLOWED_FACTS
                    or not isinstance(item["value"], str) or not isinstance(item["operation"], str)
                    or item["operation"] not in {"set", "correct"}):
                raise ValueError("Invalid fact update")


def customer_response(route: dict) -> str:
    if route["route"] == "handoff":
        return "A support professional needs to review this. No action has been completed."
    if route["route"] == "unsupported":
        return "I do not have approved information to answer that request."
    if route["route"] == "ask_clarifying_question":
        if route.get("pending_question"):
            return route["pending_question"]
        if "order_reference" in route["missing_information"]:
            return "What is the order number?"
        return "Please share the missing information so support can continue."
    return route["response_draft"]
