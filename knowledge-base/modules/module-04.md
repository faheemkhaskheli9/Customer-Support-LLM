# Module 4: Conversation State and Safe Memory for a Customer Support LLM

> **Project:** Customer Support LLM
>
> **Build:** Customer Support Assistant v0.4
>
> **Learning loop:** Build → Break → Measure → Improve
>
> **Complete code:** [module-04/](../../module-04/) — setup, source, 25 synthetic scenarios, offline tests, optional live evaluation, and a notebook.

## Module mission

In Module 3, our assistant could classify one message, return a valid JSON object, and select a route. That is useful, but a real support request often takes several turns:

> Customer: Where is my order?
>
> Assistant: What is the order number?
>
> Customer: A123. Actually, I mistyped it. The number is B456.

If the assistant stores every line and hopes the model figures it out, it may keep using A123. It may also lose the unresolved question when history is shortened, or mix facts between two customers if the application reuses state incorrectly.

In this module, we will give the assistant **explicit conversation state**. It will record what a fictional customer reported, accept corrections, ask for missing details, and allow review and deletion. Python will control transitions and session access. The model will propose a route and extracted facts; its output will not become verified truth merely because it is valid JSON.

We use fictional order and healthcare examples. This code is an educational prototype. It has no refund, cancellation, diagnosis, prescribing, or emergency decision capability.

## What you will build

Customer Support Assistant v0.4 adds four pieces around the Module 3 idea:

1. A **state record** for each conversation: current facts, missing details, pending question, route, and expiry.
2. A **router** that receives only relevant working state, approved policy supplied for this turn, and the new message.
3. A **transition function** that checks proposed changes before saving anything.
4. An **owner-scoped store** with review, explicit correction, retention choice, expiration, and deletion.

The standalone implementation lives in [module-04/](../../module-04/). Start with its [README](../../module-04/README.md) if you want to run the code while reading.

## Learning outcomes

By the end, you should be able to explain the difference between a transcript, a summary, and structured state; implement a bounded multi-turn support flow; mark reported information as reported; handle corrections without keeping contradictory current values; isolate sessions; and test expiration, deletion, and failures without an API key.

## 1. Begin with the failure, not the architecture

Try a naive implementation:

~~~python
messages = []
messages.append({"role": "user", "content": "My order is A123"})
messages.append({"role": "user", "content": "Correction: it is B456"})
~~~

The transcript contains both numbers. It does not tell your application which one is current. A model might infer the correction, but your program has no explicit rule to enforce that inference. Every future request becomes dependent on a fresh interpretation of the transcript.

Our baseline question is: **What is the current order reference?** Record whether a raw-transcript assistant uses B456, whether it invents a verification status, and how it behaves after ten more turns. We will compare the explicit state design against this baseline.

## 2. Separate history, state, and evidence

These objects serve different jobs:

**Message history** preserves what was said and when. It can grow large and contain sensitive details.

**Working state** stores the few values needed for the open request, such as a reported order reference and a pending question.

**Approved policy** is business evidence supplied by the application. It is not a customer fact, and it must not be overwritten by a customer message.

**Backend results**, if a later module adds them, can verify an order status. A reported delivery status is not equivalent to a backend result.

Module 4 deliberately stores no raw transcript. A fact records a value and the number of the message that supplied it:

~~~python
@dataclass(frozen=True)
class Fact:
    value: str
    source_event_id: int
    source: str = "reported_by_customer"
~~~

Why the source field? Because “I think my package arrived” and “the authenticated order system says delivered” have different authority. The lab records customer reports only. It never upgrades them to verified facts.

See [state.py](../../module-04/src/state_lab/state.py) for the complete schema.

## 3. Define a state transition

A state transition is a small rule for moving from the old record to the new one. For this lab, the important events are new message, clarification, correction, retention choice, close, deletion, and expiry.

The model's proposed output includes the Module 3 route plus a list of fact updates. Each update has a fixed key, a value, and an operation: `set` or `correct`. The application accepts only a small list of keys, such as `order_reference`, `delivery_status`, `reported_symptom`, and `duration`. An arbitrary field such as `confirmed_diagnosis` is rejected.

~~~python
@dataclass(frozen=True)
class FactUpdate:
    key: str
    value: str
    operation: Literal["set", "correct"] = "set"
~~~

If A123 already exists, another `set` of B456 is an error. The model must propose an explicit correction, or the customer can use the application's correction operation. The previous fact is marked superseded; the current state exposes only B456.

Why require the operation? It prevents an unnoticed overwrite and makes a correction visible to tests and to the user. A model can still misunderstand a message, so this is a useful boundary, not proof of extraction accuracy.

The transition function first validates **all** updates on a copied state. Only after the whole proposal succeeds does the service save the new state. If a second update is invalid, the first update is not partly committed.

**Checkpoint:** Run the `order_correction` and `wrong_overwrite_rejected` cases in [conversation_cases.jsonl](../../module-04/tests/conversation_cases.jsonl). Explain why their final states differ.

## 4. Ask for a detail, then resume

When a customer asks “Where is my order?” without an order reference, the router may return `ask_clarifying_question`, `missing_information=["order_reference"]`, and `pending_question="What is the order number?"`.

The next call sends a bounded snapshot: current intent, current reported facts, missing details, and pending question. It does not resend a full transcript or another customer's state. The model can interpret “A123” in light of the pending question.

The service rejects a clarification route if no question is present. It also refuses an `answer_from_approved_info` route when no approved policy was supplied. These are deterministic checks; prompt wording alone does not provide them.

Try the terminal demo:

~~~bash
cd module-04
python -m pip install -e ".[dev]"
python -m state_lab.cli
~~~

Then enter `Where is my order?`, `Order A123`, and `/state`. The default demo is scripted and free. It is intentionally narrow: it demonstrates the state flow without pretending to understand arbitrary language.

## 5. Treat model output as a proposal

The router requests a JSON object with an intent, route, missing information, pending question, response draft, review flag, and fact updates. [router.py](../../module-04/src/state_lab/router.py) parses it with exact keys and types before the transition code sees it.

Valid JSON is still capable of being wrong. For example, this is shaped correctly but false:

~~~json
{"key":"order_reference","value":"X999","operation":"set"}
~~~

If the customer never supplied X999, schema validation cannot detect the error. That is why the fact remains `reported_by_customer` rather than `verified_by_backend`, the customer can review it, and consequential actions are unavailable in this lab.

The application itself generates generic handoff and unsupported replies. A model draft saying “Your refund is approved” cannot become the customer-facing response on a handoff route. For an answer from approved policy, however, this lab cannot yet prove that the draft faithfully follows the policy. Module 5 will introduce retrieved evidence and citations.

**Break test:** Make the scripted model output malformed JSON, an unknown fact key, a false handoff flag, or two updates to the same fact. The expected result is an error fallback and unchanged state.

## 6. Keep the context bounded

Sending all previous messages to a model increases cost and can preserve old, contradictory details. Module 4's context builder sends only current reported facts and the active request. A source event number remains attached to each fact in state for review, but old superseded values are not sent back to the model.

This design is intentionally simple. It does not solve every long-conversation problem. It can lose nuance if a useful detail is not captured in the allowed fields. Expanding the schema should follow actual test failures, not a desire to store everything. Keep sensitive information out unless it is necessary for a clearly defined task.

For a longer experiment, send many fictional messages, inspect the `state` object passed to the scripted generator, and compare its size with a full transcript. Check that the pending question and corrected order reference survive.

## 7. Isolate, expire, and delete sessions

The in-memory store keys each state by `(owner_id, session_id)`. Reading, saving, correcting, and deleting all require both values. If Bob guesses Alice's session ID, the store returns the same unavailable-session result as it would for an unknown ID. The ID alone does not authorize access.

~~~python
key = (owner_id, session_id)
state = self._sessions.get(key)
if state is None:
    raise SessionNotFound("Unknown or unavailable session")
~~~

In the terminal demo, `owner_id` is a fixed fictional value. In a real application, it must come from authentication, not from a user-editable request parameter. This lab does not build authentication.

The default store expires sessions after 30 minutes. Its clock is injectable, so the test can advance time immediately instead of sleeping. A default `session_only` record is deleted when the application explicitly closes the session. An `until_expiry` choice keeps it in the still-running process until expiry or deletion. All records vanish when the process stops, regardless of choice; there is no database or backup here.

Use `/state` to review the current record, `/correct order_reference B456` to correct a value, and `/delete` to remove the current demo session. The delete method can verify only removal from this prototype's own in-memory store. A future production system would need a separate design for logs, backups, external processors, retention policy, and applicable privacy requirements.

**Isolation test:** Create one state for Alice and another for Bob, then attempt to read or delete Alice's session under Bob's owner ID. Confirm Alice's state remains available and Bob receives nothing.

## 8. Test the transitions offline

The [25 synthetic scenarios](../../module-04/tests/conversation_cases.jsonl) cover missing order information, corrections, repeated values, forbidden overwrites, refunds and cancellations, policy gaps, prompt injection, Roman Urdu, fictional symptom intake, bad JSON, invalid fields, and contradictory output. Many scenarios span two messages.

~~~bash
python -m pytest -q
~~~

The offline tests script model responses. They prove that our Python boundary behaves as intended for those inputs. They **do not** measure whether a real model extracts facts accurately or resists prompt injection. Additional tests cover cross-owner access, fixed expiry, deletion, retention choice, snapshot copying, and atomic failure.

If you configure `.env` with `OPENAI_API_KEY` and `OPENAI_MODEL`, you can opt into a live synthetic evaluation:

~~~bash
python -m pip install -e ".[dev,live]"
python -m state_lab.run_eval --cases tests/conversation_cases.jsonl --output reports/module-04-live-results.json
~~~

It may incur API charges. The runner skips fixtures designed to simulate malformed model output. Its report counts route matches and exact final fact sets on the remaining fictional cases. Review individual failures; a percentage alone hides whether a correction, handoff, or health-related case failed. Do not use real customer or patient information as fixtures.

## 9. Module project: Customer Support Assistant v0.4

Extend the starter implementation or build your own version with:

- an explicit state schema and bounded context;
- a checked transition function and a way for the customer to review or correct values;
- owner-scoped sessions, explicit close, expiry, and deletion;
- at least 25 fictional multi-turn cases and deterministic tests;
- a short before-and-after report: baseline failures, new results, one unresolved failure, and limits.

For assessment, focus on correctness of state and correction behavior (40%), isolation and retention behavior (25%), test quality and failure analysis (25%), and clear setup and limitations (10%). Passing work must show no cross-session leakage in its tests, no partial commit after invalid output, no false claim of a completed action, and an honest description of what its model and storage cannot verify.

## Knowledge check

1. Why is the entire transcript not the same as current state?
2. What changes when a customer corrects an order reference?
3. Why must a guessed session ID be insufficient to read state?
4. What does a valid JSON object fail to prove about extracted facts?
5. What can this lab's delete operation verify, and what can it not verify?
6. Why are the 25 scripted scenarios insufficient to claim model safety?

**Suggested answers:** A transcript retains conflicting old statements; a correction supersedes the old current value; access requires an authenticated owner as well as a session; schema validation checks shape rather than truth; deletion verifies only the local store; and scripted outputs test application logic rather than live model behavior.

## Deliverable

Submit the standalone package, offline tests, synthetic case set, and a short report comparing your baseline with the stateful version. Show a corrected value, a refused cross-session read, and a deleted or expired record. Explain at least one failure that remains.

## What comes next

Module 5 adds retrieval from approved support documents. The conversation state will help identify the current question, while retrieved passages will provide cited evidence. We will keep those two sources separate: a customer's memory is not company policy.
