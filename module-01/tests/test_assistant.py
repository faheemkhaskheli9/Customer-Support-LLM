from types import SimpleNamespace

import pytest

from support_basics.assistant import Settings, SupportAssistant


class FakeResponses:
    def __init__(self, output="How can I help?"):
        self.output = output
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            output_text=self.output,
            usage=SimpleNamespace(input_tokens=12, output_tokens=5),
        )


class FakeClient:
    def __init__(self):
        self.responses = FakeResponses()


def test_sends_message_with_trusted_instructions_and_returns_metrics():
    client = FakeClient()
    assistant = SupportAssistant(
        Settings(api_key="test-key", model="test-model"),
        client=client,
    )

    answer, metrics = assistant.respond(" Where is my order? ")

    assert answer == "How can I help?"
    assert client.responses.calls[0]["input"] == "Where is my order?"
    assert "Never claim" in client.responses.calls[0]["instructions"]
    assert metrics["model"] == "test-model"
    assert metrics["input_tokens"] == 12
    assert metrics["output_tokens"] == 5
    assert metrics["latency_ms"] >= 0


def test_rejects_empty_message_before_calling_model():
    client = FakeClient()
    assistant = SupportAssistant(Settings("test-key", "test-model"), client=client)

    with pytest.raises(ValueError, match="empty"):
        assistant.respond("  ")

    assert client.responses.calls == []
