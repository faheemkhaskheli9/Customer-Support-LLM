# Customer Support LLM — one evolving web app

This Django app is the active code for Modules 1–7. Select a module in the top navigation. Each stage adds a capability to the same application:

1. **Module 1:** one model call, support instructions, latency and token usage.
2. **Module 2:** bounded multi-turn context; failed calls do not corrupt history.
3. **Module 3:** four support routes on bounded context, strict JSON validation, and an offline regression button.
4. **Module 4:** reported facts, corrections, browser-session isolation, retention choice, expiry, and deletion.
5. **Module 5** (`/?stage=5`): retrieval from the fictional, versioned corpus in `data/corpus/` (19 document versions, 43 chunks). Eligibility filters (approved, in effect, current version, delivery region) run before BM25 ranking; a relevance threshold decides what counts as evidence. With no evidence, a fixed reply comes from code and the answer model is never called. Citations are built from retrieval metadata. The page shows Sources, a Retrieval panel, the corpus with each version's status, and a 34-case offline retrieval evaluation.
6. **Module 6** (`/?stage=6`): a read-only `order_status` tool over the fictional records in `data/orders.json`. The model only proposes a call as strict JSON (`parse_tool_request`); code checks a demo sign-in, that the order belongs to the signed-in customer, and a per-session lookup limit, then writes the reply from the record. Another customer's order gets the same reply as a missing one. Action, clinical and instruction-override requests are handed off without a tool call. Every decision goes to an audit trail holding IDs only. The page has a 16-case offline tool evaluation.
7. **Module 7** (`/?stage=7`): a fictional clinic's support chat. A code screen (`support/health.py`) checks every message for emergencies, clinical questions and action requests before any model call; an emergency gets a fixed urgent reply and the model is never called. The model then proposes one category as strict JSON (`parse_triage`), and the final category is the more cautious of the two, so the model can raise the level of care but never lower it. Clinical, action and out-of-scope replies come from code. Only clinic admin questions are answered, from approved clinic documents (`CLN-*`) with citations. The page keeps no history or reported facts. It has a 20-case offline safety evaluation.

The home page (`/?stage=0`) is the **Support agent**, which has every module's feature in one conversation (`agent_turn` in `support/service.py`). It works in four steps:

1. Module 5 retrieves approved passages for the message and the selected delivery region.
2. The message is routed through the Module 4 contract with only those passages as evidence. That step validates the JSON, updates reported facts, and returns fixed replies from code for handoff, unsupported and clarification.
3. When an order reference is in play (reported this turn, or a reported one and the message mentions an order) and the route is not a policy answer, the Module 6 proposer is asked for a tool call. A handoff proposal keeps the Module 4 reply; a clarifying proposal is filled from the reported `order_reference`. The lookup runs with the same sign-in, ownership and limit checks as the Module 6 page, and the reply comes from the order record. Invalid proposer output keeps the Module 4 reply.
4. Otherwise, when the route is an approved-information answer, a second model call returns `{"answer", "used_passages"}` from the passages, the recent agent conversation and the reported facts. The answer is validated and cited from retrieval metadata; an invalid answer becomes a fixed handoff reply.

Every reply shows its model metrics. Fact corrections, retention, the demo sign-in and the tool audit trail are on the same page, and deletion also clears the region, sign-in and audit trail. The order record is shown in the tool panel and never becomes a reported fact.

The older `module-01/` through `module-04/` directories remain as historical CLI companions so published links keep working. `module-05/` is the standalone `rag_lab` package for the Module 5 article. New course features belong here.

## Run locally

From this folder, using Python 3.10+:

~~~bash
python -m venv .venv
~~~

Activate it with `.venv\Scripts\Activate.ps1` on Windows PowerShell or `source .venv/bin/activate` on Linux/macOS. Then:

~~~bash
python -m pip install -r requirements-dev.txt
python manage.py migrate
python manage.py runserver
~~~

Open <http://127.0.0.1:8000/> and select a module. The default `offline` backend needs no API key and gives deterministic, intentionally narrow responses. It demonstrates application behavior; it is not a substitute for evaluating a real model.

To try a live model, copy `.env.example` to `.env`, set `SUPPORT_MODEL_BACKEND=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL` to a model available in your account. Live calls may cost money. Keep `.env` out of Git. Modules 3–4 use only the fictional training policy in `data/approved_policy.txt`; Module 5 and the agent use only approved passages from `data/corpus/`. A customer's message cannot change either. Set `SUPPORT_RETRIEVAL=hybrid` (with `OPENAI_API_KEY`, and optionally `OPENAI_EMBEDDING_MODEL`) to add embeddings to keyword retrieval; the default `keyword` mode needs no key. Restart the server after editing the corpus.

In VS Code, open `webapp/`, select the `.venv` interpreter, and use the included Run/Debug configuration.

## Test

~~~bash
python manage.py check
python manage.py test support
~~~

The 48 tests cover all seven stages, CSRF protection, session isolation, correction, expiry, deletion, invalid model output, both offline evaluations, and Module 5's loader, chunk IDs, filters, region fallback, grounded-answer parser, citations, no-call fallback, poisoned document and hybrid fusion, and Module 6's order loader, tool-request parser, ownership check, sign-in, lookup limit, audit trail, tool evaluation and the agent's order lookups, and Module 7's code screen, triage parser, a model that tries to lower the level of care, clinic-only citations and the safety evaluation. The old CLI tests are still available in their historical folders.

## Code map

- `support/gateway.py`: offline and optional OpenAI generators; one provider interface. The offline stage-5 answer is extractive.
- `support/service.py`: stage progression and response metrics.
- `support/corpus.py`: Module 5 strict front-matter loader, heading-first chunking, content-addressed chunk IDs.
- `support/retrieval.py`: eligibility filters, BM25, optional embeddings with rank fusion, threshold, citations.
- `support/tools.py`: Module 6 tool registry, order loader, tool-request parser, permission checks, code-written replies and audit entries.
- `support/health.py`: Module 7 levels of care, code screen, triage parser and the clinic-only retriever.
- `support/routing.py`: Module 3/4 output validation, the Module 5 grounded-answer parser, and application-owned handoff replies.
- `support/state.py`: Module 4 state transitions and correction rules.
- `support/evaluation.py`: Module 3 fixed-case evaluation and the Module 5 frozen retrieval evaluation (`data/rag_cases.jsonl`, pinned to 2026-09-29) and the Module 6 tool evaluation (`data/tool_cases.jsonl`) and the Module 7 safety evaluation (`data/health_cases.jsonl`).
- `support/views.py`: HTTP forms, CSRF-protected actions, and browser sessions.
- `templates/support/home.html` and `static/support.css`: the web interface.
- `support/tests.py`: end-to-end teaching checks.

## Boundaries

Use fictional data only. This prototype has no user account system, real order API, clinical validation, or durable product database. Django isolates sessions by browser cookie, not by verified customer identity. Module 4 saves structured reported facts in the server-side session and removes earlier Module 2 and Module 3 raw history when entering Module 4. Session data can remain in SQLite until expiry or cleanup even after the browser closes. Deletion removes this prototype's session keys; it cannot assert anything about external logs or backups.

The application cannot complete refunds, cancellations, or medical decisions. Schema validation checks shape, not whether a model extracted a true fact. A citation proves which approved passage an answer came from, not that the answer is faithful to it. The delivery region and the Module 6 demo sign-in come from select boxes, not verified accounts. The Module 6 audit trail lives in the browser session, so deletion removes it; a real audit log would be kept server-side and could not be deleted by the customer. The Module 7 screen is a phrase list: it is a floor under the model, not a clinical triage tool, and it misses emergencies it has no phrase for.
