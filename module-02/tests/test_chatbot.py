from collections.abc import Sequence

from customer_support.chatbot import HealthcareSupportBot
from customer_support.llm import LLMError


class FakeGenerator:
    def __init__(self, response: str = "Test response") -> None:
        self.response = response
        self.calls: list[list[dict[str, str]]] = []

    def generate(self, messages: Sequence[dict[str, str]]) -> str:
        self.calls.append(list(messages))
        return self.response


class FailingGenerator:
    def generate(self, messages: Sequence[dict[str, str]]) -> str:
        raise LLMError("Simulated API failure")


def test_empty_message_does_not_call_model():
    generator = FakeGenerator()
    bot = HealthcareSupportBot(generator=generator)

    assert bot.chat("   ") == "Please enter a question."
    assert generator.calls == []


def test_chat_stores_user_and_assistant_messages():
    generator = FakeGenerator("How may I help?")
    bot = HealthcareSupportBot(generator=generator)

    assert bot.chat("Hello") == "How may I help?"
    assert bot.conversation.messages[-2:] == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "How may I help?"},
    ]


def test_follow_up_includes_previous_context():
    generator = FakeGenerator()
    bot = HealthcareSupportBot(generator=generator)

    bot.chat("How should I prepare for an appointment?")
    bot.chat("Should I bring my previous reports?")

    second_call = generator.calls[1]
    assert len(second_call) == 3
    assert second_call[-1]["content"] == "Should I bring my previous reports?"


def test_each_conversation_has_a_unique_id():
    first = HealthcareSupportBot(generator=FakeGenerator())
    second = HealthcareSupportBot(generator=FakeGenerator())

    assert first.conversation.id != second.conversation.id


def test_failed_request_does_not_corrupt_conversation_history():
    bot = HealthcareSupportBot(generator=FailingGenerator())

    try:
        bot.chat("Will this failed request remain in history?")
    except LLMError:
        pass

    assert bot.conversation.messages == []


def test_message_length_limit_does_not_call_model():
    generator = FakeGenerator()
    bot = HealthcareSupportBot(generator=generator)

    response = bot.chat("x" * (bot.MAX_MESSAGE_CHARACTERS + 1))

    assert "too long" in response.lower()
    assert generator.calls == []
