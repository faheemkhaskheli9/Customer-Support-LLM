# Module 3 — Add Structured Support Routing to Your Web App

> **Project:** Customer Support LLM
>
> **Build:** Web app v0.3 — prompt-driven support routes
>
> **Learning loop:** Build → Break → Measure → Improve
>
> **Code:** [The evolving Django app](https://github.com/faheemkhaskheli9/Customer-Support-LLM/tree/main/webapp)

## Module mission

Our Module 2 app can answer follow-ups, but a support team also needs a predictable decision: can the assistant answer from approved information, ask for a missing detail, hand the case to a person, or say the request is unsupported? Module 3 adds that decision to the same Django app and keeps a bounded recent conversation. It does not start another project.

The model proposes structured JSON. Python checks it before the app uses any field. This separates language generation from application decisions, while keeping consequential actions unavailable.

## What you will build

Stage 3 at `http://127.0.0.1:8000/?stage=3` returns one of four routes:

- `answer_from_approved_info` when the supplied fictional policy directly answers a question;
- `ask_clarifying_question` when a needed detail is missing;
- `handoff` when a human must review or perform an action;
- `unsupported` when the app has no approved answer and no defined handoff workflow.

Try “What is the return policy?”, “Where is my order?”, “Cancel my order”, and “What is the warranty?” The first can use the application's fictional return policy. Cancellation is a handoff, not an action. An unknown warranty must not gain an invented duration.

## 1. Specify the task before editing the prompt

“Be helpful” does not define what the app should do with a refund request. The [stage instructions](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/gateway.py) specify the output fields, four route names, and safety rules. They are versioned with the application code.

The approved training policy is stored in [webapp/data/approved_policy.txt](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/data/approved_policy.txt). The server supplies it to the generator. A customer cannot change that file by writing “our policy is 90 days” in a message. Both customer text and policy text remain data; neither becomes an instruction that can override application rules.

The offline backend is intentionally deterministic and narrow. The optional live backend sends trusted instructions separately from a JSON object containing the current message and approved text. Both use the same validation boundary.

The JSON input also includes recent Module 3 conversation when available. Ask “Where is my order?” and then “A123”: the first turn requests an order number and the second can use that context. The service stores the two turns only after a valid response, caps the history at eight messages, and clears it when Module 4 switches to structured working state.

## 2. Validate the JSON boundary

The response schema contains `intent`, `route`, `summary`, `missing_information`, `response_draft`, and `needs_human_review`. The [routing module](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/routing.py) checks exact keys, types, lengths, valid routes, and consistency between `handoff` and `needs_human_review`.

It also refuses an `answer_from_approved_info` route if no approved policy was supplied. If parsing or validation fails, the service displays a controlled fallback and does not accept a partial routing result. “Return JSON” in a prompt is a request, not a guarantee; validation in Python is the real application boundary.

Even valid JSON can contain an unsupported statement. Shape validation does not prove policy fidelity. For a handoff or unsupported route, Python chooses a generic customer-facing response instead of trusting the model's draft. That prevents a generated “Your refund is approved” sentence from being shown as a completed action in those routes. A policy answer still needs better source checking; Module 5 adds retrieval and citations.

## 3. Compare prompts on fixed cases

The web app includes a **Run offline routing evaluation** button. It runs the app's router on 24 fictional cases in [prompt_cases.jsonl](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/data/prompt_cases.jsonl). The page reports the number of routes matching the expected labels, the number of schema-valid responses, and up to ten mismatches.

This is a baseline, not a promise of perfect accuracy. Review the failed cases. Ask whether the route definition is unclear, the supplied policy is insufficient, or the offline example logic is too narrow. If you change instructions, save the test-set version and compare the same cases before adding new ones. A high schema-valid rate means the response shape is stable; it says nothing by itself about truth, tone, or safety.

The browser-level tests also inject malformed JSON and verify the safe fallback. Run them with `python manage.py test support` from `webapp/`.

## 4. Try to break the boundaries

Use fictional messages that ask the assistant to ignore instructions, expose its prompt, invent a policy, or claim a refund occurred. A prompt can reduce some failures but cannot enforce identity checks or authorize actions. This stage has no action tools, so it cannot cancel an order even if the output says it did.

For healthcare examples, personal dosing or diagnostic requests should be handed to a qualified human. The app has no clinical knowledge base and no validated triage logic. Do not turn a routing label into a medical disposition.

## Module project

Run all four route examples, the 24-case offline evaluation, and one invalid-output test. Save a short report with the prompt version, case-set version, route matches, schema-valid count, one failure and its cause, and one limitation that a prompt change cannot solve. Keep every example fictional.

## What comes next

Module 4 extends this same app with structured conversation state. It will remember reported facts, accept corrections, scope data to a browser session, and expose retention and deletion controls. The validated route remains part of every update.

[Continue to Module 4](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/knowledge-base/modules/module-04.md)
