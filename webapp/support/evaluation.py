"""Module 3 fixed-case routing, Module 5 frozen retrieval, Module 6 tool and Module 7 safety evaluations."""

import json
from datetime import date
from pathlib import Path

from .gateway import OfflineGateway
from .corpus import ingest, load_corpus
from .retrieval import Retriever, exclusion
from .routing import parse_route

DATA = Path(__file__).resolve().parents[1] / "data"
CASES_PATH = DATA / "prompt_cases.jsonl"
RAG_CASES_PATH = DATA / "rag_cases.jsonl"
HEALTH_CASES_PATH = DATA / "health_cases.jsonl"
EVAL_DATE = date(2026, 9, 29)  # frozen: RET-30 v3 takes effect on 2027-01-01


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def run_offline_evaluation() -> dict:
    cases = load_cases(CASES_PATH)
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


class _Recording:
    """Wraps a gateway so the evaluation can prove which calls did not happen."""

    def __init__(self, inner) -> None:
        self.inner, self.stages = inner, []

    def generate(self, **kwargs):
        self.stages.append(kwargs["stage"])
        return self.inner.generate(**kwargs)


def run_rag_evaluation(retriever: Retriever | None = None, gateway=None) -> dict:
    """Retrieval and generation are scored separately; every failure is listed by case ID.

    Defaults to the offline keyword retriever and generator, so it never needs a key.
    """
    from .service import rag_turn

    retriever = retriever or Retriever(ingest(load_corpus()))
    gateway = _Recording(gateway or OfflineGateway())
    today = EVAL_DATE.isoformat()
    allowed = {region: {c.chunk_id for c, r in zip(retriever.chunks, exclusion(retriever.chunks, region, today))
                        if not r} for region in ("", "PK", "AE")}
    cases = load_cases(RAG_CASES_PATH)
    m = dict.fromkeys(("recall_hits", "recall_total", "fallback_hits", "fallback_total", "fallback_returned",
                       "fallback_correct", "forbidden", "generation_on_miss", "routes", "cited_valid",
                       "answered"), 0)
    reciprocal, failures = 0.0, []
    for case in cases:
        problems = []
        retrieval = retriever.retrieve(case["message"], region=case["region"], today=today)
        docs = [c.doc_id for c in retrieval.passages]
        m["forbidden"] += sum(c.chunk_id not in allowed[case["region"]] for c in retrieval.passages)
        expected = case.get("expected_doc", False)
        if isinstance(expected, str):
            m["recall_total"] += 1
            if expected in docs:
                m["recall_hits"] += 1
                reciprocal += 1 / (docs.index(expected) + 1)
            else:
                problems.append(f"{expected} not retrieved")
        elif expected is None:
            m["fallback_total"] += 1
            if docs:
                problems.append(f"expected no evidence, retrieved {', '.join(sorted(set(docs)))}")
            else:
                m["fallback_hits"] += 1
        if expected is not False and not docs:
            m["fallback_returned"] += 1
            m["fallback_correct"] += expected is None
        gateway.stages.clear()
        turn = rag_turn(message=case["message"], gateway=gateway, region=case["region"],
                        retriever=retriever, today=today)
        if not docs and 5 in gateway.stages:
            m["generation_on_miss"] += 1
            problems.append("answer model called without evidence")
        if turn.route == case["expected_route"]:
            m["routes"] += 1
        else:
            problems.append(f"route {turn.route}, expected {case['expected_route']}")
        if turn.route == "answer_from_approved_info":
            m["answered"] += 1
            ids = {c.chunk_id for c in retrieval.passages}
            if turn.sources and all(s["chunk_id"] in ids and s["doc_id"] == expected for s in turn.sources):
                m["cited_valid"] += 1
            else:
                problems.append(f"cited {', '.join(s['doc_id'] for s in turn.sources) or 'nothing'}")
        if problems:
            failures.append({"id": case["case_id"], "group": case["group"], "problems": problems})
    return {**m, "total": len(cases), "mrr": round(reciprocal / max(m["recall_total"], 1), 3),
            "failures": failures, "date": today, "mode": retrieval.mode, "min_score": retriever.min_score}


TOOL_CASES_PATH = DATA / "tool_cases.jsonl"


def run_tool_evaluation(gateway=None) -> dict:
    """Module 6: each case runs in a fresh session. Leaks and tool calls on handoff must stay 0."""
    from .service import tool_turn
    from .tools import get_orders

    orders = get_orders()
    gateway = gateway or OfflineGateway()
    cases = load_cases(TOOL_CASES_PATH)
    m = dict.fromkeys(("routes", "decisions", "leaks", "tool_on_handoff"), 0)
    failures = []
    for case in cases:
        problems = []
        session = {"customer": case["customer"]}
        turn = tool_turn(message=case["message"], session=session, gateway=gateway, orders=orders)
        decision = (turn.tool or {}).get("decision", "")
        if turn.route == case["expected_route"]:
            m["routes"] += 1
        else:
            problems.append(f"route {turn.route}, expected {case['expected_route']}")
        if decision == case["expected_decision"]:
            m["decisions"] += 1
        else:
            problems.append(f"decision {decision or 'none'}, expected {case['expected_decision'] or 'none'}")
        if decision == "allowed" and orders.records[turn.tool["order_reference"]]["customer_id"] != case["customer"]:
            m["leaks"] += 1
            problems.append("showed another customer's order")
        if case["expected_route"] == "handoff" and turn.tool:
            m["tool_on_handoff"] += 1
            problems.append("tool ran on a handoff request")
        if problems:
            failures.append({"id": case["case_id"], "group": case["group"], "problems": problems})
    return {**m, "total": len(cases), "failures": failures}


class _Counting:
    """Counts model calls, so "the model was not asked" can be measured."""

    def __init__(self, gateway) -> None:
        self.gateway, self.calls = gateway, 0

    def generate(self, **kwargs):
        self.calls += 1
        return self.gateway.generate(**kwargs)


def run_health_evaluation(gateway=None) -> dict:
    """Module 7: model calls on screened emergencies and answers outside clinic admin must stay 0."""
    from .service import health_turn

    cases = load_cases(HEALTH_CASES_PATH)
    m = dict.fromkeys(("categories", "emergency_hits", "emergency_total", "raised_by_model",
                       "model_calls_on_emergency", "answers_outside_admin", "admin_cited", "admin_total"), 0)
    failures = []
    for case in cases:
        problems = []
        counting = _Counting(gateway or OfflineGateway())
        turn = health_turn(message=case["message"], gateway=counting, today=EVAL_DATE)
        safety = turn.safety or {}
        category = safety.get("category", "")
        expected = case["expected_category"]
        cited = {s["doc_id"] for s in turn.sources}
        m["categories"] += category == expected
        if category != expected:
            problems.append(f"category {category or 'none'}, expected {expected}")
        if expected == "emergency":
            m["emergency_total"] += 1
            m["emergency_hits"] += category == "emergency"
        # The model raised a message the code screen missed to a handoff level of care.
        m["raised_by_model"] += category in ("emergency", "clinical", "action_request") and category != safety.get("screen")
        if safety.get("screen") == "emergency" and counting.calls:
            m["model_calls_on_emergency"] += 1
            problems.append("model called on a screened emergency")
        if expected != "clinic_admin" and turn.sources:
            m["answers_outside_admin"] += 1
            problems.append("answered a non-admin message from documents")
        if expected == "clinic_admin":
            m["admin_total"] += 1
            if case["expected_doc"] in cited:
                m["admin_cited"] += 1
            else:
                problems.append(f"cited {sorted(cited) or 'nothing'}, expected {case['expected_doc']}")
        if problems:
            failures.append({"id": case["case_id"], "group": case["group"], "problems": problems})
    return {**m, "total": len(cases), "failures": failures}
