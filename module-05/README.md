# Module 5 — Approved Retrieval and Citations

> **Standalone companion.** The active course code is the [shared Django web app](../webapp/), where Module 5 is `/?stage=5`. This folder does the same retrieval and grounding without Django.

Code companion for the [Module 5 tutorial](../knowledge-base/modules/module-05.md). It does not import code from other module folders or from `webapp/`.

This is a fictional support lab. The corpus describes an imaginary store and clinic. Nothing here performs refunds, order changes, bookings, diagnosis or prescribing.

## Requirements

- Python 3.10+
- No API key for the chat, evaluation and offline tests
- An OpenAI API key and model only for optional live and hybrid modes

## Setup in VS Code or a terminal

Open the `module-05` folder, then:

~~~bash
python -m venv .venv
~~~

Activate it:

~~~text
Windows PowerShell: .venv\Scripts\Activate.ps1
Linux/macOS: source .venv/bin/activate
~~~

Then:

~~~bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m rag_lab.cli --date 2026-09-29
~~~

Try `Can I return an opened item?`, `Is cash on delivery available?` (then `/region PK` and ask again), `Do you price match?`, and `Cancel my order ORD-1001.`. `/retrieval` shows the scores, which passages were used and what was filtered out before ranking.

Run the frozen evaluation (34 cases, date pinned to 2026-09-29):

~~~bash
python -m rag_lab.run_eval
~~~

It prints the metrics and every failure by case ID, and writes `reports/module-05-offline-results.json`.

## Optional live and hybrid modes

Install the extras and copy `.env.example` to `.env` within this folder. Fill `OPENAI_API_KEY` and `OPENAI_MODEL`; `OPENAI_EMBEDDING_MODEL` defaults to `text-embedding-3-small`. Never commit `.env`.

~~~bash
python -m pip install -e ".[dev,live]"
python -m rag_lab.cli --live
python -m rag_lab.run_eval --live --output reports/module-05-live-results.json
python -m rag_lab.run_eval --live --hybrid --output reports/module-05-live-hybrid-results.json
~~~

`--live` swaps the extractive generator for your model. `--hybrid` adds embeddings with rank fusion. Live runs send only synthetic cases and may cost money. The report records case IDs, routes, grounding labels, and retrieved and cited document IDs, never message or answer text.

## Files

- `src/rag_lab/corpus.py`: strict front-matter loader, heading-first chunking, content-addressed chunk IDs.
- `src/rag_lab/retrieval.py`: eligibility filters (status, effective date, current version, region) before BM25, `MIN_SCORE` threshold, region fallback, optional `OpenAIEmbedder` with rank fusion, citations from metadata.
- `src/rag_lab/grounding.py`: the `parse_grounded` boundary, `ExtractiveGenerator` (offline) and `OpenAITextGenerator`.
- `src/rag_lab/assistant.py`: `GroundedAssistant`. A keyword guard hands off actions, account changes, instruction overrides and clinical questions; a miss replies from code without calling the model.
- `src/rag_lab/cli.py`: terminal chat.
- `src/rag_lab/run_eval.py`: `evaluate` and the evaluation command.
- `prompts/grounded_answer_v1.txt`: versioned model instructions.
- `data/corpus/`: copy of the web app's fictional corpus (19 document versions, 43 chunks).
- `tests/rag_cases.jsonl`: copy of the 34 synthetic retrieval cases.
- `tests/test_rag.py`: 30 offline tests.
- `notebooks/module_05_retrieval_and_citations.ipynb`: guided lab with four exercises.
- `reports/offline-results.md`: the offline results and what they do not establish.

## Boundaries and limitations

- The keyword guard stands in for the Module 3–4 model router so the package stays focused on retrieval. The web app's agent uses the full validated router. Both give the same evaluation numbers on the 34 cases at the default threshold.
- Chunks live in memory and are rebuilt on every run. There is no vector database.
- `parse_grounded` rejects citations to passages that were not retrieved and common completed-action phrasing. It cannot prove an answer is faithful to its passage; read the answers, not just the numbers.
- 34 synthetic cases are a regression harness, not a production, clinical, multilingual or security validation.
