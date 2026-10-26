"""Frozen retrieval evaluation. Offline by default; --live and --hybrid may incur API charges."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from .assistant import GroundedAssistant
from .corpus import ingest, load_corpus
from .grounding import ExtractiveGenerator, OpenAITextGenerator
from .retrieval import OpenAIEmbedder, Retriever, exclusion

ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "tests" / "rag_cases.jsonl"
EVAL_DATE = date(2026, 9, 29)  # frozen: RET-30 v3 takes effect on 2027-01-01


class Recording:
    """Wraps a generator so the evaluation can prove which calls did not happen."""

    def __init__(self, inner) -> None:
        self.inner, self.calls = inner, 0

    def generate(self, **kwargs) -> str:
        self.calls += 1
        return self.inner.generate(**kwargs)


def load_cases(path: Path = CASES_PATH) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate(retriever: Retriever, generator, cases: list[dict], today: date | str = EVAL_DATE) -> dict:
    """Retrieval and generation are scored separately; every failure is listed by case ID."""
    today = str(today)
    generator = Recording(generator)
    assistant = GroundedAssistant(retriever, generator)
    allowed = {region: {c.chunk_id for c, r in zip(retriever.chunks, exclusion(retriever.chunks, region, today))
                        if not r} for region in ("", "PK", "AE")}
    m = dict.fromkeys(("recall_hits", "recall_total", "fallback_hits", "fallback_total", "fallback_returned",
                       "fallback_correct", "forbidden", "generation_on_miss", "routes", "cited_valid",
                       "answered"), 0)
    reciprocal, failures, rows = 0.0, [], []
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
        before = generator.calls
        result = assistant.answer(case["message"], region=case["region"], today=today)
        if not docs and generator.calls > before:
            m["generation_on_miss"] += 1
            problems.append("answer model called without evidence")
        if result.route == case["expected_route"]:
            m["routes"] += 1
        else:
            problems.append(f"route {result.route}, expected {case['expected_route']}")
        if result.route == "answer_from_approved_info":
            m["answered"] += 1
            ids = {c.chunk_id for c in retrieval.passages}
            if result.sources and all(s["chunk_id"] in ids and s["doc_id"] == expected for s in result.sources):
                m["cited_valid"] += 1
            else:
                problems.append(f"cited {', '.join(s['doc_id'] for s in result.sources) or 'nothing'}")
        if problems:
            failures.append({"id": case["case_id"], "group": case["group"], "problems": problems})
        # IDs and labels only, never message or answer text.
        rows.append({"id": case["case_id"], "expected_route": case["expected_route"], "route": result.route,
                     "grounding": result.grounding, "retrieved": docs,
                     "cited": [s["doc_id"] for s in result.sources]})
    return {**m, "total": len(cases), "mrr": round(reciprocal / max(m["recall_total"], 1), 3),
            "failures": failures, "cases": rows, "date": today,
            "mode": "hybrid" if retriever.embedder else "keyword", "min_score": retriever.min_score}


def summary(result: dict) -> str:
    lines = [
        f"Frozen evaluation on {result['date']} ({result['mode']}, MIN_SCORE {result['min_score']}), {result['total']} cases",
        f"Recall@3            {result['recall_hits']} / {result['recall_total']}",
        f"MRR                 {result['mrr']}",
        f"Fallback recall     {result['fallback_hits']} / {result['fallback_total']}",
        f"Fallback precision  {result['fallback_correct']} / {result['fallback_returned']}",
        f"Forbidden passages  {result['forbidden']}",
        f"Generation on miss  {result['generation_on_miss']}",
        f"Routes              {result['routes']} / {result['total']}",
        f"Citation validity   {result['cited_valid']} / {result['answered']}",
    ]
    lines += [f"FAIL {f['id']} ({f['group']}): {'; '.join(f['problems'])}" for f in result["failures"]]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Run the frozen Module 5 retrieval evaluation")
    parser.add_argument("--cases", type=Path, default=CASES_PATH)
    parser.add_argument("--date", default=EVAL_DATE.isoformat(), help="evaluation date, YYYY-MM-DD")
    parser.add_argument("--live", action="store_true", help="answer with OPENAI_MODEL (costs money)")
    parser.add_argument("--hybrid", action="store_true", help="add OpenAI embeddings (costs money)")
    parser.add_argument("--output", type=Path, default=Path("reports/module-05-offline-results.json"))
    args = parser.parse_args(argv)
    retriever = Retriever(ingest(load_corpus()), OpenAIEmbedder() if args.hybrid else None)
    generator = OpenAITextGenerator() if args.live else ExtractiveGenerator()
    result = evaluate(retriever, generator, load_cases(args.cases), date.fromisoformat(args.date))
    result["generator"] = getattr(generator, "model", "unknown")
    result["limitations"] = "Synthetic cases only; no production, clinical or security validation."
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(summary(result))
    print(f"Report: {args.output}")


if __name__ == "__main__":
    main()
