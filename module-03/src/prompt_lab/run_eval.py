"""Run the synthetic prompt regression set and write aggregate metrics."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .router import OpenAITextGenerator, SupportRouter


def load_cases(path: Path) -> list[dict[str, Any]]:
    cases = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                case = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number}") from exc
            required = {"case_id", "message", "approved_policy", "expected_route"}
            if not isinstance(case, dict) or not required.issubset(case):
                raise ValueError(f"Case on line {line_number} is missing required fields")
            cases.append(case)
    if not cases:
        raise ValueError("Evaluation set is empty")
    return cases


def evaluate(router: SupportRouter, cases: list[dict[str, Any]]) -> dict[str, Any]:
    records = []
    for case in cases:
        record = {
            "case_id": case["case_id"],
            "expected_route": case["expected_route"],
            "actual_route": None,
            "schema_valid": False,
            "route_pass": False,
            "error": None,
        }
        try:
            result = router.classify(
                customer_message=case["message"],
                approved_policy=case["approved_policy"],
            )
            record["actual_route"] = result.route
            record["schema_valid"] = True
            record["route_pass"] = result.route == case["expected_route"]
        except Exception as exc:  # one failure must not abort the full batch
            record["error"] = type(exc).__name__
        records.append(record)

    passed = sum(item["route_pass"] for item in records)
    valid = sum(item["schema_valid"] for item in records)
    labels = sorted({item["expected_route"] for item in records} | {
        item["actual_route"] for item in records if item["actual_route"] is not None
    })
    confusion = {
        expected: {
            actual: sum(
                item["expected_route"] == expected and item["actual_route"] == actual
                for item in records
            )
            for actual in labels
        }
        for expected in labels
    }
    return {
        "case_count": len(records),
        "route_accuracy": passed / len(records),
        "schema_valid_rate": valid / len(records),
        "route_counts_expected": dict(Counter(item["expected_route"] for item in records)),
        "confusion_matrix_rows_expected_columns_predicted": confusion,
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=Path("tests/prompt_cases.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("reports/module-03-results.json"))
    args = parser.parse_args()
    cases = load_cases(args.cases)
    router = SupportRouter(OpenAITextGenerator())
    report = evaluate(router, cases)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Cases: {report['case_count']}")
    print(f"Route accuracy: {report['route_accuracy']:.1%}")
    print(f"Schema-valid rate: {report['schema_valid_rate']:.1%}")
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
