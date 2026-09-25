"""Small provider boundary for the Module 1 support assistant."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from .prompts import SYSTEM_INSTRUCTIONS


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing. Add it to your local .env file.")
        if not model:
            raise RuntimeError("OPENAI_MODEL must not be empty.")
        return cls(api_key=api_key, model=model)


class SupportAssistant:
    """Call the model and return its text with basic usage measurements."""

    def __init__(self, settings: Settings | None = None, client: Any | None = None):
        self.settings = settings or Settings.from_env()
        self.client = client or OpenAI(api_key=self.settings.api_key)

    def respond(self, message: str) -> tuple[str, dict[str, Any]]:
        clean_message = message.strip()
        if not clean_message:
            raise ValueError("Message must not be empty.")

        started = time.perf_counter()
        response = self.client.responses.create(
            model=self.settings.model,
            instructions=SYSTEM_INSTRUCTIONS,
            input=clean_message,
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        usage = getattr(response, "usage", None)
        metrics = {
            "model": self.settings.model,
            "latency_ms": latency_ms,
            "input_tokens": getattr(usage, "input_tokens", None),
            "output_tokens": getattr(usage, "output_tokens", None),
        }
        return response.output_text.strip(), metrics
