"""Application-level chatbot orchestration."""

from __future__ import annotations

from .conversation import Conversation
from .llm import OpenAITextGenerator, TextGenerator


class HealthcareSupportBot:
    MAX_MESSAGE_CHARACTERS = 4_000

    def __init__(self, generator: TextGenerator | None = None) -> None:
        self.conversation = Conversation()
        self.generator = generator or OpenAITextGenerator()

    def chat(self, user_message: str) -> str:
        clean_message = user_message.strip()
        if not clean_message:
            return "Please enter a question."
        if len(clean_message) > self.MAX_MESSAGE_CHARACTERS:
            return (
                "Your message is too long. Please limit it to "
                f"{self.MAX_MESSAGE_CHARACTERS} characters."
            )

        # Build the request first. Commit the turn to history only after the
        # model succeeds, so a failed API request cannot corrupt the dialogue.
        request_messages = self.conversation.get_messages()
        request_messages.append({"role": "user", "content": clean_message})
        response = self.generator.generate(request_messages)

        self.conversation.add_user_message(clean_message)
        self.conversation.add_assistant_message(response)
        return response
