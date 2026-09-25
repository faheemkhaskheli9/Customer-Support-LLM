"""Interactive command-line entry point."""

from .assistant import Settings, SupportAssistant


def main() -> None:
    try:
        assistant = SupportAssistant()
    except RuntimeError as exc:
        print(f"Configuration error: {exc}")
        return

    print("Customer Support Assistant — Module 1")
    print("Use fictional examples. Type 'quit' to stop.\n")
    while True:
        try:
            message = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            return
        if message.lower() in {"quit", "exit"}:
            print("Goodbye.")
            return
        if not message:
            print("Enter a question first.\n")
            continue
        try:
            answer, metrics = assistant.respond(message)
            print(f"Assistant: {answer}")
            print(f"(latency {metrics['latency_ms']} ms; tokens: "
                  f"{metrics['input_tokens']} in / {metrics['output_tokens']} out)\n")
        except Exception as exc:
            # Learning-stage fallback: show a safe message, not provider details.
            print("The assistant is temporarily unavailable. Please try again.\n")
