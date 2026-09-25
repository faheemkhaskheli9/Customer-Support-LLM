"""Prompt assembly, model adapter, and response validation for Module 3."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
PROMPT_PATH = ROOT / "prompts" / "support_router_v1.txt"
ALLOWED_ROUTES = {
    "answer_from_approved_info",
    "ask_clarifying_question",
    "handoff",
    "unsupported",
}
REQUIRED_KEYS = {
    "intent", "route", "summary", "missing_information",
    "response_draft", "needs_human_review",
}


class ModelGenerator(Protocol):
    def generate(self, *, instructions: str, user_input: str) -> str: ...


@dataclass(frozen=True)
class RouteResult:
    intent: str
    route: str
    summary: str
    missing_information: list[str]
    response_draft: str
    needs_human_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "route": self.route,
            "summary": self.summary,
            "missing_information": self.missing_information,
            "response_draft": self.response_draft,
            "needs_human_review": self.needs_human_review,
        }


def load_instructions(path: Path = PROMPT_PATH) -> str:
    instructions = path.read_text(encoding="utf-8").strip()
    if not instructions:
        raise ValueError("Prompt instructions are empty")
    return instructions


def serialize_user_input(*, approved_policy: str, customer_message: str) -> str:
    """Serialize values once; inserted text cannot become template syntax."""
    return json.dumps(
        {"approved_policy": approved_policy, "customer_message": customer_message},
        ensure_ascii=False,
    )


def parse_and_validate(raw_text: str) -> RouteResult:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError("Model response is not valid JSON") from exc

    if not isinstance(data, dict):
        raise ValueError("Model response must be a JSON object")
    missing = REQUIRED_KEYS - data.keys()
    extra = data.keys() - REQUIRED_KEYS
    if missing or extra:
        raise ValueError(
            f"Response keys differ from schema; missing={sorted(missing)}, extra={sorted(extra)}"
        )
    if not isinstance(data["route"], str) or data["route"] not in ALLOWED_ROUTES:
        raise ValueError("route must be one of the allowed strings")
    for key in ("intent", "summary", "response_draft"):
        if not isinstance(data[key], str):
            raise ValueError(f"{key} must be a string")
    if not isinstance(data["missing_information"], list):
        raise ValueError("missing_information must be a list")
    if not all(isinstance(item, str) for item in data["missing_information"]):
        raise ValueError("Every missing_information item must be a string")
    if not isinstance(data["needs_human_review"], bool):
        raise ValueError("needs_human_review must be a boolean")
    if data["route"] == "handoff" and not data["needs_human_review"]:
        raise ValueError("handoff must require human review")
    if data["route"] != "handoff" and data["needs_human_review"]:
        raise ValueError("human review must use the handoff route")
    return RouteResult(**data)


class OpenAITextGenerator:
    """Adapter using separate trusted instructions and user input fields."""

    def __init__(self, model: str | None = None) -> None:
        load_dotenv(ROOT / ".env")
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model = (model or os.getenv("OPENAI_MODEL", "gpt-5-mini")).strip()
        if not api_key:
            raise RuntimeError("Set OPENAI_API_KEY in module-03/.env")
        if not self.model:
            raise RuntimeError("OPENAI_MODEL must not be empty")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install dependencies with: pip install -e .") from exc
        self.client = OpenAI(api_key=api_key)

    def generate(self, *, instructions: str, user_input: str) -> str:
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=instructions,
                input=[{"role": "user", "content": user_input}],
            )
        except Exception as exc:
            # Avoid propagating provider details or request contents to the UI.
            raise RuntimeError("Model request failed; check configuration and provider logs") from exc
        output = response.output_text.strip()
        if not output:
            raise RuntimeError("Model returned an empty response")
        return output


class SupportRouter:
    def __init__(self, generator: ModelGenerator) -> None:
        self.generator = generator
        self.instructions = load_instructions()

    def classify(self, *, customer_message: str, approved_policy: str = "") -> RouteResult:
        message = customer_message.strip()
        if not message:
            raise ValueError("customer_message must not be empty")
        if len(message) > 4_000:
            raise ValueError("customer_message must be 4,000 characters or fewer")
        if len(approved_policy) > 8_000:
            raise ValueError("approved_policy must be 8,000 characters or fewer")
        user_input = serialize_user_input(
            approved_policy=approved_policy,
            customer_message=message,
        )
        raw = self.generator.generate(instructions=self.instructions, user_input=user_input)
        return parse_and_validate(raw)
