"""Fictional terminal demo. Live mode is optional and may incur API charges."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .router import OpenAITextGenerator, SupportRouter
from .service import SupportService
from .store import MemoryStore, SessionNotFound


class DemoGenerator:
    """Small deterministic script for exploring state without an API key."""

    def generate(self, *, instructions: str, user_input: str) -> str:
        obj = json.loads(user_input)
        text = obj["customer_message"].strip()
        state = obj["state"]
        facts = []
        route = "unsupported"
        question = ""
        missing = []
        answer = ""
        if obj["approved_policy"] and "return" in text.lower() and "policy" in text.lower():
            route = "answer_from_approved_info"
            answer = "The supplied policy says: " + obj["approved_policy"].strip()
        elif text.lower().startswith("order "):
            value = text[6:].strip()
            if value:
                previous = state["reported_facts"].get("order_reference")
                facts = [{"key": "order_reference", "value": value,
                          "operation": "correct" if previous and previous != value else "set"}]
                route = "handoff"
        elif "order" in text.lower():
            route = "ask_clarifying_question"
            question = "What is the order number?"
            missing = ["order_reference"]
        return json.dumps({
            "intent": "order_status", "route": route,
            "missing_information": missing, "pending_question": question,
            "response_draft": answer, "needs_human_review": route == "handoff",
            "fact_updates": facts,
        })


def main() -> None:
    parser = argparse.ArgumentParser(description="Module 4 fictional state lab")
    parser.add_argument("--live", action="store_true", help="Call configured model; costs may apply")
    parser.add_argument("--policy-file", type=Path, default=None,
                        help="Path to approved training policy; supply only trusted application data")
    args = parser.parse_args()
    approved_policy = args.policy_file.read_text(encoding="utf-8") if args.policy_file else ""
    if len(approved_policy) > 8000:
        parser.error("Policy must be at most 8,000 characters")
    generator = OpenAITextGenerator() if args.live else DemoGenerator()
    service = SupportService(MemoryStore(), SupportRouter(generator))
    owner = "local-demo-user"  # A real application obtains this from authentication.
    session = service.start(owner_id=owner)["session_id"]
    print("Fictional demo. Messages stay in process memory for this session; /quit clears the default session.")
    print("Commands: /state, /correct KEY VALUE, /retain, /session-only, /delete, /quit")
    try:
        while True:
            line = input("> ").strip()
            if line == "/quit":
                break
            try:
                if line == "/state":
                    print(json.dumps(service.review(owner_id=owner, session_id=session), indent=2))
                elif line.startswith("/correct "):
                    parts = line.split(" ", 2)
                    if len(parts) != 3:
                        print("Usage: /correct KEY VALUE")
                        continue
                    _, key, value = parts
                    print(service.correct(owner_id=owner, session_id=session, key=key, value=value)["current_facts"])
                elif line == "/retain":
                    service.set_retention(owner_id=owner, session_id=session, choice="until_expiry")
                    print("Opted in until expiry, in this process only.")
                elif line == "/session-only":
                    service.set_retention(owner_id=owner, session_id=session, choice="session_only")
                    print("This session will be cleared at close.")
                elif line == "/delete":
                    service.delete(owner_id=owner, session_id=session)
                    print("Deleted this demo session from memory.")
                    break
                elif line:
                    result = service.turn(owner_id=owner, session_id=session,
                                          message=line, approved_policy=approved_policy)
                    print(f"[{result.status}/{result.route}] {result.response}")
            except (ValueError, SessionNotFound) as exc:
                print(f"Request could not be applied: {exc}")
    finally:
        try:
            service.close(owner_id=owner, session_id=session)
        except KeyError:
            pass


if __name__ == "__main__":
    main()
