"""Fictional terminal chat. Live and hybrid modes are optional and may incur API charges."""

from __future__ import annotations

import argparse
import json
from datetime import date

from .assistant import GroundedAssistant
from .corpus import REGIONS, ingest, load_corpus
from .grounding import ExtractiveGenerator, OpenAITextGenerator
from .retrieval import OpenAIEmbedder, Retriever

HELP = "Commands: /region PK|AE|none, /retrieval, /quit"


def show(result) -> None:
    print(f"[{result.route} · {result.grounding}] {result.response}")
    for s in result.sources:
        print(f"  [{s['n']}] {s['doc_id']} v{s['version']} ({s['effective_date']}) {s['source']} — "
              f"{s['heading']} · chunk {s['chunk_id']}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Chat with the fictional approved corpus")
    parser.add_argument("--date", default=None, help="pretend today is YYYY-MM-DD")
    parser.add_argument("--region", default="", choices=["", "PK", "AE"])
    parser.add_argument("--live", action="store_true", help="answer with OPENAI_MODEL (costs money)")
    parser.add_argument("--hybrid", action="store_true", help="add OpenAI embeddings (costs money)")
    args = parser.parse_args(argv)
    today = date.fromisoformat(args.date) if args.date else date.today()
    retriever = Retriever(ingest(load_corpus()), OpenAIEmbedder() if args.hybrid else None)
    assistant = GroundedAssistant(retriever, OpenAITextGenerator() if args.live else ExtractiveGenerator())
    region, last = args.region, None
    print(f"Fictional support lab · {len(retriever.chunks)} chunks · date {today} · region {region or 'not set'}")
    print("Nothing here performs refunds, order changes, bookings, diagnosis or prescribing.")
    print(HELP)
    while True:
        try:
            message = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not message:
            continue
        if message == "/quit":
            return
        if message.startswith("/region"):
            value = message.removeprefix("/region").strip().upper()
            value = "" if value in ("", "NONE") else value
            if value not in REGIONS - {"all"} | {""}:
                print("Region must be PK, AE or none.")
            else:
                region = value
                print(f"Region: {region or 'not set'}")
            continue
        if message == "/retrieval":
            print(json.dumps(last.retrieval, indent=2) if last else "Ask a question first.")
            continue
        if message.startswith("/"):
            print(HELP)
            continue
        try:
            last = assistant.answer(message, region=region, today=today)
        except (ValueError, RuntimeError) as exc:
            print(f"Error: {exc}")
            continue
        show(last)


if __name__ == "__main__":
    main()
