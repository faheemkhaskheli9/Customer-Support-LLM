"""Command-line interface for the Module 2 chatbot."""

from __future__ import annotations

from .chatbot import HealthcareSupportBot
from .llm import LLMError


def main() -> None:
    try:
        bot = HealthcareSupportBot()
    except RuntimeError as exc:
        print(f"Configuration error: {exc}")
        return

    print("Healthcare Support Assistant")
    print(f"Conversation ID: {bot.conversation.id}")
    print("Type 'exit' to stop.\n")

    while True:
        user_message = input("You: ").strip()
        if user_message.lower() in {"exit", "quit"}:
            print("Assistant: Goodbye.")
            break

        try:
            response = bot.chat(user_message)
        except LLMError:
            response = "The assistant is temporarily unavailable. Please try again."

        print(f"Assistant: {response}\n")


if __name__ == "__main__":
    main()
