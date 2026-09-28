"""Optional live, synthetic-only model run. Reports route and fact outcomes."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .router import OpenAITextGenerator, SupportRouter
from .service import SupportService
from .store import MemoryStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Run synthetic multi-turn cases against a configured model")
    parser.add_argument("--cases", type=Path, default=Path("tests/conversation_cases.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("reports/module-04-live-results.json"))
    args = parser.parse_args()
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    router = SupportRouter(OpenAITextGenerator())
    reports = []
    for case in cases:
        # The scripted invalid-output fixtures have no meaningful live expectation.
        if any(turn["expected_status"] == "error" for turn in case["turns"]):
            continue
        service = SupportService(MemoryStore(), router)
        session = service.start(owner_id="synthetic-evaluation")["session_id"]
        turns = []
        for turn in case["turns"]:
            result = service.turn(owner_id="synthetic-evaluation", session_id=session,
                                  message=turn["message"])
            turns.append({"expected_route": turn["expected_route"], "actual_route": result.route,
                          "route_pass": result.status == "ok" and result.route == turn["expected_route"],
                          "status": result.status})
        actual_facts = {k: v["value"] for k, v in service.review(
            owner_id="synthetic-evaluation", session_id=session)["current_facts"].items()}
        reports.append({"id": case["id"], "turns": turns,
                        "facts_pass": actual_facts == case["expected_facts"]})
    total = sum(len(row["turns"]) for row in reports)
    correct = sum(sum(turn["route_pass"] for turn in row["turns"]) for row in reports)
    report = {"case_count": len(reports), "turn_count": total,
              "route_pass_count": correct, "route_accuracy": correct / total if total else None,
              "facts_pass_count": sum(row["facts_pass"] for row in reports), "cases": reports,
              "limitations": "Synthetic cases only; no clinical or production validation."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"{correct}/{total} route checks passed; report: {args.output}")


if __name__ == "__main__":
    main()
