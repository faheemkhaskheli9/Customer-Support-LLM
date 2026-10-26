# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A course ("Customer Support LLM") that builds a trustworthy customer-support assistant one module at a time. Examples are fictional support and healthcare scenarios. Nothing here performs refunds, order changes, diagnosis or prescribing, and docs/code must keep saying so. Never add real customer/patient data.

- **`webapp/` is the active code.** It is one Django app that grows with every module. **New course features go here.**
- **`module-01/` … `module-04/` are historical CLI packages.** They are kept so published article links keep working. Change them only to fix those links or keep them consistent with the articles.
- **`module-05/` is the standalone `rag_lab` package** linked from the Module 5 article. It copies `webapp/data/corpus/` and `rag_cases.jsonl` and must give the same evaluation numbers; keep the copies in sync when the corpus or cases change.
- Lesson articles live in `knowledge-base/modules/` (`module-0N.md`, plus `-outline.md` from Module 3 and `-medium.md` for Module 3). Older CLI-era versions are in `knowledge-base/modules/legacy/`. Every relative link and every link to this repo's `main` branch must resolve to a file in the repo (`RepoLinkTests`).
- Keep counts and file names quoted in articles/READMEs (e.g. "24 synthetic cases", "34 cases", "43 chunks", "16 cases" for tools, "20 cases" for safety, Module 5 evaluation numbers) in sync with the code. Articles link to code via `https://github.com/faheemkhaskheli9/Customer-Support-LLM/tree/main/<folder>/`.
- Every UI change ships with screenshots: save them in `knowledge-base/modules/images/` (`module-0N-<what>.png`, cropped to `main.grid`), embed them in the module article and show them in the PR description.

## Commands

### Webapp (Python 3.10+, run from `webapp/`)

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1                 # Windows; `source .venv/bin/activate` elsewhere
python -m pip install -r requirements-dev.txt
python manage.py migrate
python manage.py runserver                 # http://127.0.0.1:8000/
python manage.py check
python manage.py test support              # all tests (Django TestCase, offline)
python manage.py test support.tests.CourseWebTests.test_name   # single test
python manage.py evaluation_report         # Module 8 report; exits 1 when the release is blocked
python manage.py release_check             # Module 9: readiness, deploy checks and the report; exits 1 when any fails
```

The backend is chosen by `SUPPORT_MODEL_BACKEND` in `webapp/.env` (copy it from `.env.example`). The default `offline` backend needs no API key and returns deterministic canned behavior. With `openai`, it reads `OPENAI_API_KEY` and `OPENAI_MODEL`, and live calls cost money. `SUPPORT_RETRIEVAL=hybrid` adds OpenAI embeddings (`OPENAI_EMBEDDING_MODEL`) to keyword retrieval. Tests must stay offline.

### Historical module packages (run from `module-0N/`)

```bash
python -m pip install -e ".[dev]"          # module-04: add ",live" for OpenAI extras
python -m pytest -q
python -m pytest tests/test_state.py::test_name -q
python -m rag_lab.run_eval                 # module-05: frozen evaluation; --live/--hybrid cost money
```

Each module is its own package (`support_basics`, `customer_support`, `prompt_lab`, `state_lab`, `rag_lab`) with its own `.venv`, `.env`, notebook and tests. A module never imports from another module or from `webapp/`. There is no linter or formatter configured.

## Webapp architecture

A single page (`templates/support/home.html`) switches between stages with `?stage=N`. `STAGES` in `support/views.py` sets the navigation order. Stages 1–7 are the lessons; stage 8 is the Module 8 evaluation report and stage 9 the Module 9 deployment page (neither has a conversation; `NO_CHAT_STAGES`). **Stage 0 (`AGENT`) is the home page: the "Support agent", which combines all seven modules in one conversation.**

- `gateway.py`: the `Gateway` Protocol with `OfflineGateway` (regex/keyword heuristics; `POLICY_WORDS`; extractive stage-5 answers) and `OpenAIGateway`. `get_gateway()` picks one from the setting. Unlike module-03/04, the prompts here are **inline in `STAGE_PROMPTS`**, keyed by stage, not versioned files.
- `corpus.py` / `retrieval.py`: Module 5. Strict front-matter loader over `data/corpus/*.md`, heading-first chunks with content-addressed IDs, `exclusion` (status, effective date, current version, region) before BM25 ranking, `MIN_SCORE` threshold, optional `Embedder` with rank fusion, `citation` from metadata. `get_retriever()` is cached per process.
- `tools.py`: Module 6. `TOOLS` is the whole registry (read-only `order_status` only). `parse_tool_request` validates the model's `{route, tool, arguments}` proposal; `run_tool` checks the demo sign-in (`session["customer"]`), order format, `MAX_LOOKUPS` and ownership in code. Denied and not found share one reply. `describe` writes the reply from the record; `audit_entry` holds IDs only. Orders come from `data/orders.json`.
- `health.py`: Module 7. `screen` checks emergency, clinical and action phrases in code before any model call (an emergency never calls the model); `parse_triage` validates the model's `{"category"}`; `more_cautious` lets the model raise the level of care in `LEVELS`, never lower it. Only `clinic_admin` retrieves, from `get_clinic_retriever()` (approved `CLN-*` chunks only). Replies other than cited clinic answers come from `REPLIES`.
- `routing.py`: the strict JSON boundary for stages 3/4/5/agent (`parse_route` → `validate_route`; `parse_grounded` for cited answers). Four routes: `answer_from_approved_info`, `ask_clarifying_question`, `handoff`, `unsupported`. Handoff, unsupported and clarification replies come from code (`customer_response`), never from model text. Invalid output falls back safely.
- `state.py`: Module 4 reported-fact state as plain dicts (so they fit in the session). Includes `apply_proposal`, `correct_fact`, `is_expired` and the allowed fact keys. Facts are customer-*reported*, not verified.
- `service.py`: `process_turn` (stages 1–4), `rag_turn` (stage 5), `tool_turn` (stage 6), `health_turn` (stage 7, keeps nothing in the session) and `agent_turn` (stage 0, which runs the Module 7 `screen` first: an emergency or clinical message gets the `REPLIES` text, calls no model and keeps nothing). Both retrieval turns retrieve first, route with only the retrieved passages as evidence, then `ground`: only an approved-information route makes the second (stage-5 prompt) call, whose answer is validated and cited from metadata. A miss never calls the answer model. **A failed turn commits nothing to the session.** In the agent, `order_lookup` runs the Module 6 tool instead of `ground` when an order reference is in play and the tool proposer does not say handoff. Replies carry latency/token metrics, `sources`, `retrieval` and `tool`.
- `report.py`: Module 8. `run_report(gateway)` runs the Module 3, 5, 6 and 7 evaluations; `SAFETY_GATES` must hold exactly and `QUALITY_GATES` may not drop below `data/report_baseline.json` (it must name every quality metric). The verdict is `pass` or `blocked` with failing case IDs; `to_markdown` feeds the `/report.md` download and `python manage.py evaluation_report` (exits 1 when blocked). When an evaluation's numbers change on purpose, update the baseline in the same change.
- `ops.py`: Module 9. `readiness()` runs config checks (debug off, secret key not the course default, hosts, HTTPS, backend variables named but never their values) and data checks (sessions table, corpus read from disk rather than the cached retriever, clinic chunks, orders, baseline). No check calls a model. `/healthz` is liveness only; `/readyz` returns 503 with the failing check keys and no details. `RUNBOOK` is the symptom → first action list shown on the page. `release_check` adds Django's `check --deploy` and the Module 8 report. Production settings come from `DJANGO_*` variables in `config/settings.py` (WhiteNoise only when debug is off).
- `views.py`: server-rendered forms with CSRF-protected POSTs. All state lives in the Django session (SQLite, 30-minute cookie age), keyed per stage (`m2_history`, `m3_history`, `agent_history`, etc.). The delivery `region` is validated against `REGIONS` and stored in the session. Entering stage 4 drops the stage 2/3 raw history. The correct/retention/delete forms are shared by stage 4 and the agent. `back()` returns to whichever page sent the request.
- `evaluation.py`: the Module 3 offline regression over `data/prompt_cases.jsonl`, and the Module 5 frozen evaluation over `data/rag_cases.jsonl` (`EVAL_DATE` pinned), and the Module 6 tool evaluation over `data/tool_cases.jsonl` (leaks and tool calls on handoff must stay 0), and the Module 7 safety evaluation over `data/health_cases.jsonl` (model calls on screened emergencies and answers outside clinic admin must stay 0). Stages 3–4 answer only from `data/approved_policy.txt`; stage 5 and the agent only from approved, current corpus passages.

The historical modules follow the same ideas in package form: a Protocol generator with an OpenAI adapter, versioned `prompts/<name>_vN.txt` files (bump the suffix when behavior changes), and the JSON boundary (`parse_and_validate` in module 3, `parse_proposal` in module 4). Module 4 is layered as state → store → router → service → cli/run_eval.
