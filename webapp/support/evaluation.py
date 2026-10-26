"""Module 3 fixed-case routing and Module 5 frozen retrieval evaluations."""

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
