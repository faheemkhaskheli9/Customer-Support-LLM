# Module 4 — Add Safe Conversation State to the Same Web App

> **Project:** Customer Support LLM
>
> **Build:** Web app v0.4 — reported facts, corrections, and retention
>
> **Learning loop:** Build → Break → Measure → Improve
>
> **Code:** [The evolving Django app](https://github.com/faheemkhaskheli9/Customer-Support-LLM/tree/main/webapp)

## Module mission

Module 3 makes one routing decision per message. A support conversation also needs to know what remains unresolved and which customer-reported facts are current. Consider this fictional exchange:

> Customer: Where is my order?
>
> Assistant: What is the order number?
>
> Customer: A123. Actually, the correct number is B456.

A raw transcript contains both identifiers. Module 4 adds explicit state so Python can mark A123 as superseded, keep B456 current, and show the recorded value for review. The app still cannot verify an order or perform a refund. Use only fictional data.

## What you will build

Open `http://127.0.0.1:8000/?stage=4` in the same app you built in Modules 1–3. The page now shows a pending question, route, current reported facts, expiry, and retention choice. It provides forms to correct a fact or delete the prototype's session data.

The active code is in [state.py](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/state.py), [routing.py](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/routing.py), [service.py](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/service.py), and [views.py](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/views.py). These files extend the app rather than creating a separate Module 4 package. The older CLI companion remains as historical reference for published links.

## 1. Separate a report from a verified fact

The state record contains `current_facts`, `missing_information`, `pending_question`, `last_route`, an event number, and an expiry time. A fact stores its value, source event number, and `reported_by_customer` status. This distinction matters: “I think it arrived” is not the same as an authenticated order system reporting delivery.

The allowed keys are deliberately small: order reference, delivery status, contact channel, reported symptom, duration, and medication name as entered. An arbitrary field such as `confirmed_diagnosis` is rejected. A model can propose extracted facts, but application code checks the schema and transition. It cannot prove the model extracted the right value from the message, which is why the customer can review and correct it.

## 2. Make corrections explicit and atomic

Try these messages in the browser:

1. “Where is my order?”
2. “A123”
3. “Actually order B456.”

The first turn stores a pending question. The second adds the reported order reference. The third uses a `correct` operation to supersede A123. The current state shows B456; a bounded list of superseded facts remains internally for the lab's failure analysis.

The pure [transition function](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/state.py) copies the existing state and validates all proposed updates before the service saves it. A second invalid fact cannot leave the first half of the proposal committed. A changed existing value without an explicit correction fails. The **Correct a reported fact** form provides an independent, customer-controlled correction path that does not require another model call.

Why not just summarize the transcript? Summaries can omit an unresolved question or preserve an outdated number. This lab sends the current reported facts and pending question to the model; it does not send a Module 4 raw transcript back on every turn. On entering Module 4, the app clears the earlier Module 2 and Module 3 histories from that browser session.

## 3. Use the same routing boundary

The Module 4 model proposal includes the route from Module 3 plus `pending_question` and `fact_updates`. The [JSON validator](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/webapp/support/routing.py) rejects missing or extra fields, unknown routes, inconsistent handoff flags, invalid fact keys, oversized fields, and a policy answer with no approved text. If an update fails, the app returns a safe fallback and keeps the prior state.

The offline backend understands only a few fictional patterns. It can demonstrate an order reference correction and record “headache” as a *reported symptom* while routing a dosing question to a person. That does not amount to diagnosis, emergency triage, or medication advice. The model receives no action tools; Python supplies generic handoff text without claiming a refund or cancellation occurred.

## 4. Isolate, expire, and delete

Django keeps state in a server-side session associated with the browser's session cookie. Two separate browser sessions do not share reported facts. The test suite creates separate clients and checks that a fact entered by one is absent from the other.

This is **browser-session isolation, not customer authentication**. Anyone using the same unlocked browser session can access its state. A real service needs identity verification, authorization, data retention design, audit rules, and access controls before handling customer or patient records.

The working state has a fixed 30-minute expiry. The default retention preference is **this browser session**. The alternative keeps the session cookie until expiry. The UI lets the learner delete the course state explicitly. Deletion removes keys from this application's session; it does not prove removal from logs, backups, or any external system. Django's SQLite session rows may remain until session cleanup even after a browser closes. Do not promise stronger deletion than this prototype implements.

## 5. Test what code guarantees

From `webapp/`, run:

~~~bash
python manage.py check
python manage.py test support
~~~

The integration tests cover clarification, a bare order number after the question, correction, separate browser sessions, expiry, deletion, a reported health detail, CSRF rejection, and invalid model output leaving state unchanged. These tests verify application behavior with a scripted backend. They do **not** establish that a live model extracts facts accurately or resists every prompt injection.

For your own evaluation, add fictional multi-turn cases for repeated values, contradictions, missing details, long conversations, and an unauthorized request. Record the expected route and current facts before you run them. Measure transition pass rate, correction errors, schema-valid rate, cross-session leaks, latency, and any unsupported claim. Review each consequential failure rather than relying on an overall score.

## Module project

Show a completed clarification, a correction from A123 to B456, the current state review, a rejected cross-session read, and deletion or expiry. Explain which facts are customer reports, what the app can verify, and which risks remain before production use.

## What comes next

Module 5 will add retrieval from approved documents and citations to this same app. Customer memory will identify the active question; retrieved company evidence will stay separate from customer-reported facts.
