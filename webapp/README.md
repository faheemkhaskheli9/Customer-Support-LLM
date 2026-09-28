# Customer Support LLM — one evolving web app

This Django app is the active code for Modules 1–4. Select a module in the top navigation. Each stage adds a capability to the same application:

1. **Module 1:** one model call, support instructions, latency and token usage.
2. **Module 2:** bounded multi-turn context; failed calls do not corrupt history.
3. **Module 3:** four support routes, strict JSON validation, and an offline regression button.
4. **Module 4:** reported facts, corrections, browser-session isolation, retention choice, expiry, and deletion.

The older `module-01/` through `module-04/` directories remain as historical CLI companions so published links keep working. New course features belong here.

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

To try a live model, copy `.env.example` to `.env`, set `SUPPORT_MODEL_BACKEND=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL` to a model available in your account. Live calls may cost money. Keep `.env` out of Git. The UI uses only the fictional training policy in `data/approved_policy.txt`; it cannot change company policy based on a customer's message.

In VS Code, open `webapp/`, select the `.venv` interpreter, and use the included Run/Debug configuration.

## Test

~~~bash
python manage.py check
python manage.py test support
~~~

The browser-level tests cover all four stages, CSRF protection, session isolation, correction, expiry, deletion, invalid model output, and the offline regression runner. The old CLI tests are still available in their historical folders.

## Code map

- `support/gateway.py`: offline and optional OpenAI generators; one provider interface.
- `support/service.py`: stage progression and response metrics.
- `support/routing.py`: Module 3/4 output validation and application-owned handoff replies.
- `support/state.py`: Module 4 state transitions and correction rules.
- `support/evaluation.py`: Module 3 fixed-case evaluation.
- `support/views.py`: HTTP forms, CSRF-protected actions, and browser sessions.
- `templates/support/home.html` and `static/support.css`: the web interface.
- `support/tests.py`: end-to-end teaching checks.

## Boundaries

Use fictional data only. This prototype has no user account system, order API, clinical validation, or durable product database. Django isolates sessions by browser cookie, not by verified customer identity. Module 4 saves structured reported facts in the server-side session and removes earlier Module 2 raw history when entering Module 4. Session data can remain in SQLite until expiry or cleanup even after the browser closes. Deletion removes this prototype's session keys; it cannot assert anything about external logs or backups.

The application cannot complete refunds, cancellations, or medical decisions. Schema validation checks shape, not whether a model extracted a true fact. Module 5 will add approved retrieval and citations.
