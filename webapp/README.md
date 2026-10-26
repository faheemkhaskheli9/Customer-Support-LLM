# Customer Support LLM — one evolving web app

This Django app is the active code for Modules 1–9. Select a module in the top navigation. Each stage adds a capability to the same application:

1. **Module 1:** one model call, support instructions, latency and token usage.
2. **Module 2:** bounded multi-turn context; failed calls do not corrupt history.
3. **Module 3:** four support routes on bounded context, strict JSON validation, and an offline regression button.
4. **Module 4:** reported facts, corrections, browser-session isolation, retention choice, expiry, and deletion.
5. **Module 5** (`/?stage=5`): retrieval from the fictional, versioned corpus in `data/corpus/` (19 document versions, 43 chunks). Eligibility filters (approved, in effect, current version, delivery region) run before BM25 ranking; a relevance threshold decides what counts as evidence. With no evidence, a fixed reply comes from code and the answer model is never called. Citations are built from retrieval metadata. The page shows Sources, a Retrieval panel, the corpus with each version's status, and a 34-case offline retrieval evaluation.
6. **Module 6** (`/?stage=6`): a read-only `order_status` tool over the fictional records in `data/orders.json`. The model only proposes a call as strict JSON (`parse_tool_request`); code checks a demo sign-in, that the order belongs to the signed-in customer, and a per-session lookup limit, then writes the reply from the record. Another customer's order gets the same reply as a missing one. Action, clinical and instruction-override requests are handed off without a tool call. Every decision goes to an audit trail holding IDs only. The page has a 16-case offline tool evaluation.
7. **Module 7** (`/?stage=7`): a fictional clinic's support chat. A code screen (`support/health.py`) checks every message for emergencies, clinical questions and action requests before any model call; an emergency gets a fixed urgent reply and the model is never called. The model then proposes one category as strict JSON (`parse_triage`), and the final category is the more cautious of the two, so the model can raise the level of care but never lower it. Clinical, action and out-of-scope replies come from code. Only clinic admin questions are answered, from approved clinic documents (`CLN-*`) with citations. The page keeps no history or reported facts. It has a 20-case offline safety evaluation.
8. **Module 8** (`/?stage=8`): one evaluation and safety report (`support/report.py`). It runs the Module 3, 5, 6 and 7 evaluations (24 + 34 + 16 + 20 cases) and checks release gates. Eight safety gates must hold exactly: schema-valid routes, forbidden passages, answer model on a miss, cross-customer leaks, tool calls on handoff, emergency recall, model calls on screened emergencies and answers outside clinic admin. Nine quality metrics may not drop below the frozen baseline in `data/report_baseline.json`. The verdict is `pass` or `blocked`, and each failed gate names its cases. The report downloads as Markdown (`/report.md`), and `python manage.py evaluation_report` prints it and exits with 1 when blocked. The page also shows customer feedback: each support agent reply can be rated helpful or not helpful once (`support/feedback.py`), and the `Feedback` table keeps IDs only (route, status, cited document IDs, tool decision; no text, customer or session). Feedback is not a release gate.
9. **Module 9** (`/?stage=9`): deployment readiness (`support/ops.py`). Ten checks run without calling a model. Five check the configuration: debug off, a secret key that is not the course default, named allowed hosts, HTTPS only, and the model backend's variables (named when missing, never their values). Five check the database and data: the sessions and feedback tables, the corpus read from disk (43 chunks), the clinic documents, the orders and the report baseline. `/healthz` is liveness only; `/readyz` returns 503 with the failing check keys. `python manage.py release_check` runs the checks, Django's `check --deploy` and the Module 8 report, and exits with 1 when any fails. The page also shows the runbook: each symptom with its first action.

The home page (`/?stage=0`) is the **Support agent**, which has every module's feature in one conversation (`agent_turn` in `support/service.py`). It works in five steps:

1. The Module 7 code screen runs first. An emergency or clinical message gets the fixed Module 7 reply and a safety panel, makes no model call, and nothing from it (history, reported facts, symptom) is kept. Clinic booking phrases are not screened here; the shop agent's routing hands those off.
2. Module 5 retrieves approved passages for the message and the selected delivery region.
3. The message is routed through the Module 4 contract with only those passages as evidence. That step validates the JSON, updates reported facts, and returns fixed replies from code for handoff, unsupported and clarification.
4. When an order reference is in play (reported this turn, or a reported one and the message mentions an order) and the route is not a policy answer, the Module 6 proposer is asked for a tool call. A handoff proposal keeps the Module 4 reply; a clarifying proposal is filled from the reported `order_reference`. The lookup runs with the same sign-in, ownership and limit checks as the Module 6 page, and the reply comes from the order record. Invalid proposer output keeps the Module 4 reply.
5. Otherwise, when the route is an approved-information answer, a second model call returns `{"answer", "used_passages"}` from the passages, the recent agent conversation and the reported facts. The answer is validated and cited from retrieval metadata; an invalid answer becomes a fixed handoff reply.

Every reply shows its model metrics and can be rated helpful or not helpful once; safety-screened replies are not rated. Fact corrections, retention, the demo sign-in and the tool audit trail are on the same page, and deletion also clears the region, sign-in and audit trail. The order record is shown in the tool panel and never becomes a reported fact.

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

The 66 tests cover all nine stages, CSRF protection, session isolation, correction, expiry, deletion, invalid model output, both offline evaluations, and Module 5's loader, chunk IDs, filters, region fallback, grounded-answer parser, citations, no-call fallback, poisoned document and hybrid fusion, and Module 6's order loader, tool-request parser, ownership check, sign-in, lookup limit, audit trail, tool evaluation and the agent's order lookups, and Module 7's code screen, triage parser, a model that tries to lower the level of care, clinic-only citations, the safety evaluation and the agent's safety screen, and Module 8's passing report, a model that blocks the release, a hijacked model whose failed gates all name cases, the baseline check, the report page, the download and the command, and Module 9's liveness and readiness endpoints, a broken data file, a live backend with missing variables, the release check and the deployment page, and customer feedback: one rating per reply, refused forgeries, an IDs-only record and the report panel. The old CLI tests are still available in their historical folders.

## Deploy

Every production setting comes from the environment (see the commented lines in `.env.example`):

| Variable | Production value |
|---|---|
| `DJANGO_DEBUG` | `0` |
| `DJANGO_SECRET_KEY` | a new value from `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `DJANGO_ALLOWED_HOSTS` | your host name, e.g. `support.example.com` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | `https://` plus that host |
| `DJANGO_BEHIND_PROXY` | `1` when a TLS proxy sets `X-Forwarded-Proto` |
| `DJANGO_SQLITE_PATH` | a path on persistent storage (optional) |
| `DJANGO_HSTS_SECONDS` | defaults to `3600` when debug is off |

With debug off, HTTPS redirects, secure cookies and HSTS are on by default. Then:

~~~bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py release_check
waitress-serve --listen=127.0.0.1:8000 --trusted-proxy=127.0.0.1 --trusted-proxy-headers=x-forwarded-proto config.wsgi:application
~~~

Waitress runs on Windows, macOS and Linux; WhiteNoise serves the collected static files. Waitress drops `X-Forwarded-Proto` from a proxy it does not trust, and every request then redirects to HTTPS in a loop, so name the proxy. Point the platform's liveness probe at `/healthz` and its readiness probe at `/readyz`. Including subdomains in HSTS and preloading are left to the domain owner, so those two `check --deploy` warnings are silenced in `config/settings.py`.

## Code map

- `support/gateway.py`: offline and optional OpenAI generators; one provider interface. The offline stage-5 answer is extractive.
- `support/service.py`: stage progression and response metrics.
- `support/corpus.py`: Module 5 strict front-matter loader, heading-first chunking, content-addressed chunk IDs.
- `support/retrieval.py`: eligibility filters, BM25, optional embeddings with rank fusion, threshold, citations.
- `support/tools.py`: Module 6 tool registry, order loader, tool-request parser, permission checks, code-written replies and audit entries.
- `support/health.py`: Module 7 levels of care, code screen, triage parser and the clinic-only retriever.
- `support/routing.py`: Module 3/4 output validation, the Module 5 grounded-answer parser, and application-owned handoff replies.
- `support/state.py`: Module 4 state transitions and correction rules.
- `support/evaluation.py`: Module 3 fixed-case evaluation and the Module 5 frozen retrieval evaluation (`data/rag_cases.jsonl`, pinned to 2026-09-29) and the Module 6 tool evaluation (`data/tool_cases.jsonl`) and the Module 7 safety evaluation (`data/health_cases.jsonl`). `run_offline_evaluation(limit=None)` returns every Module 3 failure for the report.
- `support/report.py`: Module 8 release gates, the baseline check, the verdict and the Markdown report.
- `support/management/commands/evaluation_report.py`: the report from the terminal; exits with 1 when blocked.
- `support/feedback.py` and `support/models.py`: customer ratings on agent replies and the IDs-only `Feedback` table.
- `support/ops.py`: Module 9 readiness checks and the runbook.
- `support/management/commands/release_check.py`: readiness, Django's deploy checks and the report; exits with 1 when any fails.
- `support/views.py`: HTTP forms, CSRF-protected actions, and browser sessions.
- `templates/support/home.html` and `static/support.css`: the web interface.
- `support/tests.py`: end-to-end teaching checks.

## Boundaries

Use fictional data only. This prototype has no user account system, real order API, clinical validation, or durable product database. Django isolates sessions by browser cookie, not by verified customer identity. Module 4 saves structured reported facts in the server-side session and removes earlier Module 2 and Module 3 raw history when entering Module 4. Session data can remain in SQLite until expiry or cleanup even after the browser closes. Customer feedback is the only server-side table; it holds IDs only, so **Delete session data** has nothing in it to remove. Deletion removes this prototype's session keys; it cannot assert anything about external logs or backups.

The application cannot complete refunds, cancellations, or medical decisions. Schema validation checks shape, not whether a model extracted a true fact. A citation proves which approved passage an answer came from, not that the answer is faithful to it. The delivery region and the Module 6 demo sign-in come from select boxes, not verified accounts. The Module 6 audit trail lives in the browser session, so deletion removes it; a real audit log would be kept server-side and could not be deleted by the customer. The Module 7 screen is a phrase list: it is a floor under the model, not a clinical triage tool, and it misses emergencies it has no phrase for. A Module 8 `pass` is an offline regression check over fictional cases, not proof that the assistant is safe; the baseline records the offline backend only. Module 9 readiness checks the configuration and data files, not whether the model provider is reachable, and SQLite on one server is not a highly available database.
