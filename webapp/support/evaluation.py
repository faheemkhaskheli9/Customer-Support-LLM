"""Module 3 fixed-case routing exercise using the application's own router."""

import json
from pathlib import Path

from .gateway import OfflineGateway
from .routing import parse_route

CASES_PATH = Path(__file__).resolve().parents[1] / "data" / "prompt_cases.jsonl"


def run_offline_evaluation() -> dict:
    cases = [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    gateway = OfflineGateway()
    failures = []
    matched = valid = 0
    for case in cases:
        try:
            output = gateway.generate(stage=3, messages=[{"role": "user", "content": case["message"]}],
                                      policy=case["approved_policy"])
            result = parse_route(output.text, case["approved_policy"], 3)
            valid += 1
            if result["route"] == case["expected_route"]:
                matched += 1
            else:
                failures.append({"id": case["case_id"], "expected": case["expected_route"],
                                 "actual": result["route"]})
        except ValueError:
            failures.append({"id": case["case_id"], "expected": case["expected_route"],
                             "actual": "invalid_output"})
    return {"total": len(cases), "matched": matched, "schema_valid": valid,
            "failures": failures[:10], "backend": "offline-demo"}
