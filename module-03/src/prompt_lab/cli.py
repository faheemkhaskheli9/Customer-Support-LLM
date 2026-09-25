"""Small interactive demo using fictional messages only."""

from .router import OpenAITextGenerator, SupportRouter


def main() -> None:
    router = SupportRouter(OpenAITextGenerator())
    print("Module 3 support router. Use fictional examples only; type quit to exit.")
    while True:
        message = input("Customer message: ").strip()
        if message.lower() in {"quit", "exit"}:
            break
        try:
            result = router.classify(customer_message=message)
            print(result.to_dict())
        except (ValueError, RuntimeError) as exc:
            print(f"Could not classify safely: {exc}")
