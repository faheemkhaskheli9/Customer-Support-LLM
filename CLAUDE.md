# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A course ("Customer Support LLM") that builds a trustworthy customer-support assistant one module at a time. Examples are fictional support and healthcare scenarios. Nothing here performs refunds, order changes, diagnosis or prescribing, and docs/code must keep saying so. Never add real customer/patient data.

- **`webapp/` is the active code.** It is one Django app that grows with every module. **New course features go here.**
- **`module-01/` … `module-04/` are historical CLI packages.** They are kept so published article links keep working. Change them only to fix those links or keep them consistent with the articles.
- Lesson articles: `docs/module-01.md` and `docs/module-02.md`. Modules 3+ live in `knowledge-base/modules/` (`module-0N.md`, `-outline.md`, `-medium.md`). Older CLI-era versions of the articles are in `docs/legacy/` and `knowledge-base/modules/legacy/`. `knowledge-base/` is gitignored, so those articles exist only locally, even though the READMEs link to them.
- Keep counts and file names quoted in articles/READMEs (e.g. "24 synthetic cases") in sync with the code. Articles link to code via `https://github.com/faheemkhaskheli9/Customer-Support-LLM/tree/main/<folder>/`.

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
```

The backend is chosen by `SUPPORT_MODEL_BACKEND` in `webapp/.env` (copy it from `.env.example`). The default `offline` backend needs no API key and returns deterministic canned behavior. With `openai`, it reads `OPENAI_API_KEY` and `OPENAI_MODEL`, and live calls cost money. Tests must stay offline.

### Historical module packages (run from `module-0N/`)

```bash
python -m pip install -e ".[dev]"          # module-04: add ",live" for OpenAI extras
python -m pytest -q
python -m pytest tests/test_state.py::test_name -q
```

Each module is its own package (`support_basics`, `customer_support`, `prompt_lab`, `state_lab`) with its own `.venv`, `.env`, notebook and tests. A module never imports from another module or from `webapp/`. There is no linter or formatter configured.

## Webapp architecture

A single page (`templates/support/home.html`) switches between stages with `?stage=N`. `STAGES` in `support/views.py` sets the navigation order. Stages 1–4 are the lessons. **Stage 5 (`AGENT`) is the home page: the "Support agent", which combines all four modules in one conversation.**

- `gateway.py`: the `Gateway` Protocol with `OfflineGateway` (regex/keyword heuristics) and `OpenAIGateway`. `get_gateway()` picks one from the setting. Unlike module-03/04, the prompts here are **inline in `STAGE_PROMPTS`**, keyed by stage, not versioned files.
- `routing.py`: the strict JSON boundary for stages 3/4/agent (`parse_route` → `validate_route`). Four routes: `answer_from_approved_info`, `ask_clarifying_question`, `handoff`, `unsupported`. Handoff, unsupported and clarification replies come from code (`customer_response`), never from model text. Invalid output falls back safely.
- `state.py`: Module 4 reported-fact state as plain dicts (so they fit in the session). Includes `apply_proposal`, `correct_fact`, `is_expired` and the allowed fact keys. Facts are customer-*reported*, not verified.
- `service.py`: `process_turn` (lesson stages) and `agent_turn` (stage 5). `agent_turn` runs in two steps: (1) route with the Module 4 contract and update facts, then (2) only on an approved-policy route, make a second call (stage-5 prompt) that sees recent agent turns and the facts. **A failed turn commits nothing to the session.** Replies carry latency/token metrics.
- `views.py`: server-rendered forms with CSRF-protected POSTs. All state lives in the Django session (SQLite, 30-minute cookie age), keyed per stage (`m2_history`, `m3_history`, `agent_history`, etc.). Entering stage 4 drops the stage 2/3 raw history. The correct/retention/delete forms are shared by stage 4 and the agent. `back()` returns to whichever page sent the request.
- `evaluation.py`: the Module 3 offline regression over `data/prompt_cases.jsonl`. `data/approved_policy.txt` is the only policy the app may answer from.

The historical modules follow the same ideas in package form: a Protocol generator with an OpenAI adapter, versioned `prompts/<name>_vN.txt` files (bump the suffix when behavior changes), and the JSON boundary (`parse_and_validate` in module 3, `parse_proposal` in module 4). Module 4 is layered as state → store → router → service → cli/run_eval.
