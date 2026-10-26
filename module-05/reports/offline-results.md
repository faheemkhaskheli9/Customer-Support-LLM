# Module 5 offline evaluation

Run from `module-05/`:

~~~bash
python -m pytest -q
python -m rag_lab.run_eval
~~~

On 2026-10-26, 30 tests passed. The frozen evaluation (date pinned to 2026-09-29, keyword retrieval, `MIN_SCORE` 3.5, extractive generator) gave the same numbers as the web app:

| Metric | Result |
|---|---|
| Recall@3 | 23 / 24 |
| MRR | 0.958 |
| Fallback recall | 5 / 6 |
| Fallback precision | 5 / 6 |
| Forbidden passages retrieved | 0 |
| Answer-model calls with no evidence | 0 |
| Routes | 32 / 34 |
| Citation validity | 23 / 24 |

Two cases fail, both explained in the article: RAG-008 ("What is the delivery charge?" with no region) answers from the billing policy after a keyword collision on "charge", and RAG-034 (Roman Urdu) retrieves nothing in keyword mode.

RAG-019 ("Do gift cards expire?") passes every automated check but does not answer the question. Citation validity measures where an answer came from, not whether it is right.

These 34 synthetic cases are a regression harness for this code. They do **not** measure live-model accuracy, multilingual quality, clinical safety, or resistance to determined prompt injection.
