"""Provider-neutral router with strict JSON boundary and optional OpenAI adapter."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from .state import ALLOWED_FACTS, ALLOWED_ROUTES, ConversationState, FactUpdate, Proposal

ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "state_router_v1.txt"
REQUIRED = {
    "intent", "route", "missing_information", "pending_question",
    "response_draft", "needs_human_review", "fact_updates",
}


class Generator(Protocol):
    def generate(self, *, instructions: str, user_input: str) -> str: ...


def parse_proposal(raw: str) -> Proposal:
    try:
        obj = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Invalid model JSON") from exc
    if not isinstance(obj, dict) or set(obj) != REQUIRED:
        raise ValueError("Model response has incorrect keys")
    if not isinstance(obj["route"], str) or obj["route"] not in ALLOWED_ROUTES:
        raise ValueError("Invalid route")
    if any(not isinstance(obj[k], str) for k in ("intent", "pending_question", "response_draft")):
        raise ValueError("Invalid text field")
    if not isinstance(obj["needs_human_review"], bool):
        raise ValueError("Invalid review flag")
    missing = obj["missing_information"]
    if not isinstance(missing, list) or not all(isinstance(x, str) for x in missing):
        raise ValueError("Invalid missing_information")
    raw_updates = obj["fact_updates"]
    if not isinstance(raw_updates, list):
        raise ValueError("Invalid fact_updates")
    updates = []
    for item in raw_updates:
        if not isinstance(item, dict) or set(item) != {"key", "value", "operation"}:
            raise ValueError("Invalid fact update shape")
        if not isinstance(item["key"], str) or item["key"] not in ALLOWED_FACTS:
            raise ValueError("Invalid fact key")
        if (not isinstance(item["value"], str) or not isinstance(item["operation"], str)
                or item["operation"] not in {"set", "correct"}):
            raise ValueError("Invalid fact value or operation")
        updates.append(FactUpdate(**item))
    return Proposal(
        intent=obj["intent"], route=obj["route"], missing_information=tuple(missing),
        pending_question=obj["pending_question"], response_draft=obj["response_draft"],
        needs_human_review=obj["needs_human_review"], fact_updates=tuple(updates),
    )


class SupportRouter:
    def __init__(self, generator: Generator) -> None:
        self.generator = generator
        self.instructions = PROMPT_PATH.read_text(encoding="utf-8").strip()

    def propose(self, *, message: str, state: ConversationState, approved_policy: str = "") -> Proposal:
        if not message.strip() or len(message) > 4000 or len(approved_policy) > 8000:
            raise ValueError("Invalid message or policy length")
        # This is a working-state snapshot, not a raw transcript or trusted policy.
        context = {
            "active_intent": state.current_intent,
            "reported_facts": {k: v.value for k, v in state.current_facts.items()},
            "missing_information": list(state.missing_information),
            "pending_question": state.pending_question,
        }
        raw = self.generator.generate(
            instructions=self.instructions,
            user_input=json.dumps({"state": context, "approved_policy": approved_policy,
                                   "customer_message": message}, ensure_ascii=False),
        )
        return parse_proposal(raw)


class OpenAITextGenerator:
    def __init__(self) -> None:
        try:
            from dotenv import load_dotenv
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError('Install live extras with: pip install -e ".[live]"') from exc
        load_dotenv(ROOT / ".env")
        key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "").strip()
        if not key or not model:
            raise RuntimeError("Set OPENAI_API_KEY and OPENAI_MODEL in module-04/.env")
        self.client = OpenAI(api_key=key)
        self.model = model

    def generate(self, *, instructions: str, user_input: str) -> str:
        try:
            response = self.client.responses.create(
                model=self.model, instructions=instructions,
                input=[{"role": "user", "content": user_input}],
            )
            if not response.output_text.strip():
                raise ValueError("Empty model response")
            return response.output_text
        except Exception as exc:
            raise RuntimeError("Model call failed; inspect provider logs") from exc
