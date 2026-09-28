# Module 1 — Build Your First Customer Support LLM Web App

> **Project:** Customer Support LLM
>
> **Build:** Web app v0.1 — one request, one response
>
> **Learning loop:** Build → Break → Measure → Improve
>
> **Code:** [The evolving Django app](https://github.com/faheemkhaskheli9/Customer-Support-LLM/tree/main/webapp)

## Module mission

We will grow one application throughout this course. Module 1 gives it a browser interface, a single model call, support instructions, and basic measurements. Modules 2–4 add features to these same files. You can run the first stage without an API key using the offline teaching backend, then switch to a live model when ready.

A model can produce a convincing return policy without having a real policy. Our first rule is simple: the app must not treat plausible language as a verified company fact. It also cannot complete an order action by writing a sentence about it.

## Learning outcomes

By the end, you can run the Django app, trace one request from form to response, explain what trusted instructions do, configure an optional provider, measure latency and token use, and find unsupported claims in a small test set.

## 1. Set up the shared app

Clone the repository, enter `webapp/`, create a virtual environment, and install the dependencies:

~~~bash
git clone https://github.com/faheemkhaskheli9/Customer-Support-LLM.git
cd Customer-Support-LLM/webapp
python -m venv .venv
python -m pip install -r requirements-dev.txt
python manage.py migrate
python manage.py runserver
~~~

Activate `.venv` before the install command: `.venv\Scripts\Activate.ps1` in Windows PowerShell or `source .venv/bin/activate` on Linux/macOS. Open `http://127.0.0.1:8000/?stage=1`. The migration creates Django's server-side session table, which later modules use. Module 1 itself sends one message at a time.

Open [webapp/README.md](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/README.md) for the full setup and VS Code launch configuration. The older `module-01/` CLI package remains in the repository for published links; the web app is the active course project.

## 2. Trace one request

The form in [home.html](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/templates/support/home.html) posts to `/chat/1/`. Django verifies the CSRF token. The [view](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/views.py) validates the module, calls `process_turn`, stores the result for the redirect, and displays it on the page.

In [service.py](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/service.py), stage 1 passes only the current user message to the generator. It does not read Module 2 history or Module 4 state. That makes the baseline easy to inspect: a second question is a new request, not an implicit continuation.

The [gateway](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/gateway.py) keeps model-specific code behind `generate(stage, messages, policy, state)`. The offline version gives predictable examples without cost. The optional OpenAI version sends trusted stage instructions separately from the customer's input. In both modes, customer text is data, not an authorization signal.

## 3. Define the support boundary

Stage 1 instructions tell the model to be clear, ask a focused question when required information is missing, and avoid inventing company policies, records, diagnoses, or completed actions. Try these fictional requests:

- “What is your warranty period?”
- “Where is my order?”
- “Cancel order A123.”
- “Give me a 50% discount code.”

For an unknown warranty, the assistant should say it lacks approved information. For a missing order number, it can ask a question. For cancellation, it must not claim an action took place. A prompt can guide text, but it cannot authorize an order update. This app has no order action tool.

The offline backend deliberately recognizes only a narrow set of examples. Its output does not demonstrate that a real model is accurate. Use the same questions with a configured live model if you want to observe model behavior, then record what changes.

## 4. Measure the call

The service records elapsed time around the generator call. The result also carries input and output token counts when the provider supplies them. The offline backend displays a model name and latency but no fake token counts.

Why measure now? Later features add context, JSON instructions, and retrieved evidence. Each can increase latency and cost. A first measurement gives us a baseline, although a few requests are not enough to estimate production performance.

For a live model, copy `.env.example` to `.env`, set `SUPPORT_MODEL_BACKEND=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL`, then restart the server. Never place the key in the browser or commit `.env`. The live provider may charge for requests. If the call fails, the app shows a controlled fallback rather than a traceback to the customer.

## 5. Break and test it

Run the browser-level tests from `webapp/`:

~~~bash
python manage.py check
python manage.py test support
~~~

The Module 1 test checks that an unsupported policy is not invented and that this stage does not store conversation history. Try a direct POST without a CSRF token: Django rejects it. This is a web security boundary enforced by middleware, not by an LLM instruction.

For your own short report, record the message, expected behavior, actual response, latency, whether the response made an unsupported claim, and any provider error. Use fictional data. Do not count a polished tone as evidence that a company fact is true.

## Module project

Start the app, send the four fictional requests above, and compare responses with the rules. Explain the difference between a generated cancellation sentence and a completed cancellation. Show the model name and latency from the UI. Keep one failed or unsupported case in your report.

## What comes next

Module 2 extends this same app with a short conversation history. The first stage remains selectable so you can compare single-turn and multi-turn behavior without switching projects.

[Continue to Module 2](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/docs/module-02.md)
