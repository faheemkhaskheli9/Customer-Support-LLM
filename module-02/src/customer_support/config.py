"""Environment-based application configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            from dotenv import load_dotenv
        except ImportError as exc:
            raise RuntimeError(
                "The python-dotenv package is missing. Run: pip install -e ."
            ) from exc

        load_dotenv()
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        model = os.getenv("OPENAI_MODEL", "gpt-5-mini").strip()

        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY is missing. Copy .env.example to .env and add your key."
            )
        if not model:
            raise RuntimeError("OPENAI_MODEL must not be empty.")

        return cls(api_key=api_key, model=model)
