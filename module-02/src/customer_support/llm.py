"""Small provider boundary around the OpenAI Responses API."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from .config import Settings
from .prompts import SYSTEM_PROMPT


class LLMError(RuntimeError):
    """Raised when a model response cannot be generated safely."""


class TextGenerator(Protocol):
    def generate(self, messages: Sequence[dict[str, str]]) -> str: ...


class OpenAITextGenerator:
    def __init__(self, settings: Settings | None = None) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError(
                "The openai package is missing. Run: pip install -e ."
            ) from exc

        self.settings = settings or Settings.from_env()
        self.client = OpenAI(api_key=self.settings.api_key)

    def generate(self, messages: Sequence[dict[str, str]]) -> str:
        try:
            response = self.client.responses.create(
                model=self.settings.model,
                instructions=SYSTEM_PROMPT,
                input=list(messages),
            )
            text = response.output_text.strip()
        except Exception as exc:
            raise LLMError("Unable to generate an LLM response.") from exc

        if not text:
            raise LLMError("The model returned an empty response.")
        return text
