# Module 4 — Conversation State and Safe Memory

Standalone code companion for the [Module 4 tutorial](../knowledge-base/modules/module-04.md). Module 4 does not import code from earlier folders. It carries forward Module 3's route names and strict JSON boundary.

This is a fictional support lab. It does not perform refunds or order changes and is not a clinical system. The local store is process memory only; it is not a durable database, authentication service, or production privacy solution.

## Requirements

- Python 3.10+
- No API key for the demo and offline tests
- An OpenAI API key and model only for optional live mode

## Setup in VS Code or a terminal

Open the `module-04` folder in VS Code, select its `.venv` interpreter, and run:

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
python -m state_lab.cli
~~~

Try `Where is my order?`, `Order A123`, `/state`, `/correct order_reference B456`, and `/delete`. The default demo uses a deterministic scripted generator, so its language understanding is intentionally narrow. It shows state transitions without paid API calls.

To test policy answers, load the fictional training policy as an application-controlled file:

~~~bash
python -m state_lab.cli --policy-file data/approved_policy.txt
~~~

Ask `What is the return policy?`. The offline demo quotes the supplied text. You can combine `--policy-file` with `--live` after configuring a model.

## Optional live model

Install the extras and copy `.env.example` to `.env` within this folder. Fill `OPENAI_API_KEY` and a model your account supports. Never commit `.env`.

~~~bash
python -m pip install -e ".[dev,live]"
python -m state_lab.cli --live
python -m state_lab.run_eval --cases tests/conversation_cases.jsonl --output reports/module-04-live-results.json
~~~

The live evaluation sends only synthetic messages and may incur API charges. It skips cases whose scripted expectation is an invalid model output. The report omits message text, but it still records case IDs and derived results. Do not replace the fixtures with customer or patient data.

## Files

- `src/state_lab/state.py` — typed records, fact provenance, corrections, and atomic state transitions.
- `src/state_lab/store.py` — owner-scoped, expiring in-memory sessions.
- `src/state_lab/router.py` — provider-neutral generator, JSON parser, and optional model adapter.
- `src/state_lab/service.py` — application boundary, safe fallback, retention, deletion, and review.
- `src/state_lab/cli.py` — fictional offline and optional live terminal demos.
- `src/state_lab/run_eval.py` — optional live route and fact evaluation.
- `prompts/state_router_v1.txt` — versioned model instructions.
- `data/approved_policy.txt` — fictional, application-supplied policy for the offline demo.
- `tests/conversation_cases.jsonl` — 26 fictional scenarios; many contain multiple turns.
- `tests/` — offline tests for state transitions, isolation, deletion, invalid output, and scenario integration.
- `notebooks/module_04_state_and_memory.ipynb` — guided lab.

## Boundaries and limitations

- `owner_id` must come from authentication in a real application; the local CLI uses a fixed fictional owner. A guessed session ID is never authorization.
- The store uses a fixed 30-minute TTL by default, holds no raw transcript, and disappears when the process exits. `session_only` deletes at explicit close. `until_expiry` retains only inside the still-running process until TTL or explicit deletion.
- A model-proposed fact is merely a reported value. The code checks shape and transitions but cannot prove that the model extracted it correctly. User review and an authenticated data source remain necessary.
- A nonempty approved policy allows an answer route, but the code cannot prove the draft faithfully quotes that policy. Module 5 adds retrieval and citation checks.
- The model cannot complete actions. Handoff and unsupported replies come from application code, regardless of model prose.
- Live evaluation on 26 synthetic cases is not a clinical, security, privacy, or production validation.
