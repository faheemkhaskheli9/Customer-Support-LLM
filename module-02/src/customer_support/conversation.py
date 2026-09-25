"""Short-term, in-memory conversation state."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import uuid4

@dataclass
class Conversation:
    id: str = field(default_factory=lambda: str(uuid4()))
    messages: list[dict[str, str]] = field(default_factory=list)

    def add_user_message(self, message: str) -> None:
        self.messages.append({"role": "user", "content": message})

    def add_assistant_message(self, message: str) -> None:
        self.messages.append({"role": "assistant", "content": message})

    def get_messages(self) -> list[dict[str, str]]:
        return [message.copy() for message in self.messages]
