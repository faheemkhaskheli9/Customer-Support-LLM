# Module 4 — Conversation State and Safe Memory

> **Project:** Customer Support LLM  
> **Build:** Customer Support Assistant v0.4 — stateful, consent-aware support flows  
> **Level:** Beginner to practical LLM engineering  
> **Learning loop:** Build → Break → Measure → Improve

## Module mission

Module 3 produced a validated support route for one message. A conversation needs more: the assistant must remember what the customer actually said, ask for missing details, accept corrections, and avoid mixing one person's information with another's. Memory introduces privacy and reliability risks, so this module makes state explicit, bounded, and testable.

Build a small state manager around the Module 3 router. Keep the initial implementation local and use fictional customer and healthcare scenarios. This module does not add policy retrieval, refund tools, diagnosis, or an autonomous clinical workflow.

## Prerequisites

- Completed Modules 1–3.
- A working model client and the Module 3 validated routing result.
- Basic Python dictionaries, data classes or typed models, and tests.

## What you will build

**Customer Support Assistant v0.4** will:

1. Maintain a separate state for each synthetic conversation.
2. Ask for missing information and resume when the customer supplies it.
3. Record reported facts with a source message and status.
4. Replace or invalidate an earlier fact when the customer corrects it.
5. Show the current state for review.
6. Handle an explicit retention choice and a delete request.
7. Expire or clear state according to a configurable policy.
8. Fall back safely when a message, state update, or model output is invalid.

Keep conversation memory separate from trusted company policy. A customer's statement, a generated summary, and an authenticated backend result have different authority.

## Learning outcomes

By the end, learners can:

- explain the difference between message history, extracted state, a summary, and durable memory;
- define a small state schema and transition rules;
- keep conversations isolated by an application-generated session identifier;
- merge new facts and corrections without silently retaining contradictions;
- track whether a detail is reported, verified, unknown, or superseded;
- bound context size without losing unresolved questions or important corrections;
- apply explicit retention and deletion rules;
- test privacy, isolation, correction, and expiration behaviors offline.

## Lesson outline

### 1. Why a chat transcript is not enough

- Revisit the short in-memory conversation from Module 2 and the single-message router from Module 3.
- Compare sending the entire transcript with maintaining a small, structured working state.
- Define the limits of each: history preserves wording; state supports logic; summaries may lose details.
- Separate ephemeral session state from persistent storage.

**Checkpoint:** Explain what the assistant should remember after “My package was delivered yesterday” and what changes after “Correction: it has not arrived.”

### 2. Model a conversation as state and transitions

- Define fields such as session_id, current_intent, reported_facts, missing_information, last_route, pending_question, retention_choice, and updated_at.
- Represent fact status and source: reported_by_customer, verified_by_backend, unknown, or superseded.
- Define transitions for new message, clarification, correction, handoff, deletion, and expiry.
- Make transition validation deterministic; the LLM may propose an extraction, but application code decides whether a transition is allowed.
- Use typed records or schema validation for both model output and stored state.

**Lab:** Implement a small `ConversationState` record and pure `apply_event(state, event)` function using synthetic messages.

### 3. Capture only the facts needed for the task

- Extract details from a message while preserving “reported” versus “verified.”
- Store the minimum needed for the active support request.
- Avoid treating a model-generated summary as a source of verified truth.
- Keep company policy in its own approved evidence path; do not write it into customer memory as a customer fact.
- In fictional healthcare intake, record “symptom reported,” not a confirmed condition; do not infer missing medication, allergy, or dosage details.

**Exercise:** Compare a free-form summary with a structured record after three messages, and identify unsupported additions.

### 4. Ask, resume, and handle corrections

- Use the Module 3 route and missing_information fields to ask one focused question.
- Resume the pending task only when the response supplies the needed detail.
- Detect explicit corrections and mark the older value superseded.
- Resolve conflicting or ambiguous details by asking the customer to confirm.
- Keep a small audit trail of state changes without exposing sensitive values in ordinary logs.

**Break test:** “My order is A123.” → “Actually, it is B456.” → “What number do you have?” The assistant must use B456 and must not present A123 as current.

### 5. Bound the context window

- Send the active question, relevant current facts, and approved evidence needed for this turn.
- Summarize older turns only when needed and retain source links or message identifiers for consequential facts.
- Preserve unresolved questions and corrections when trimming history.
- Measure prompt size and note what was omitted.
- Treat any summary as untrusted derived data that can be rechecked against source messages.

**Lab:** Run the same synthetic long conversation with full history and bounded state; compare answer quality, token use, and failure cases.

### 6. Consent, retention, and deletion

- Explain to a customer what information the prototype would retain and for how long before enabling persistence.
- Make the retention choice explicit in state; default to short-lived local session state in the course lab.
- Define a configurable expiry time and a clear deletion operation for the prototype's own store.
- Avoid logging raw messages, health details, access tokens, or secrets by default.
- Clarify that a toy exercise does not establish compliance with any jurisdiction's privacy requirements.
- Describe limits of deletion where a production system has backups or external processors; do not claim deletion beyond what the application actually controls.

**Checkpoint:** Show the stored state before and after a delete request, including what the prototype can verify was removed.

### 7. Isolate users and sessions

- Generate session identifiers in application code; do not accept a user-provided ID as proof of access.
- Scope reads and writes to the authenticated user's session in a real application.
- Make a second synthetic user's conversation invisible to the first.
- Reject unknown, expired, or unauthorized sessions in the storage layer.
- Explain why prompt instructions cannot enforce access control.

**Break test:** Ask one session to recall an order number supplied only in another session. It must not reveal it.

### 8. Evaluate the stateful assistant

Create a frozen set of at least 25 synthetic, multi-turn cases covering:

- routine continuation and missing details;
- corrections, contradictions, and user review of captured facts;
- unknown facts and unsupported policy requests;
- handoff without false action claims;
- cross-session isolation and guessed session IDs;
- long conversations and summary drift;
- retention choice, expiry, and deletion;
- fictional healthcare intake with reported versus verified facts;
- prompt injection embedded in a customer turn or old summary;
- English and Roman Urdu or Urdu messages where practical.

**Metrics:** state transition pass rate, correction accuracy, clarification completion, unsupported fact rate, cross-session leakage count, deletion/expiry pass rate, schema validity, latency, and token use. Report denominators and review failures individually. A small synthetic set does not validate clinical or privacy performance in production.

## Module project

Extend the Module 3 application into **Customer Support Assistant v0.4**. The deliverable is a working state layer, not just a prompt that says “remember.”

### Required behavior

- Accept a new synthetic support message in a session.
- Route with the existing validated Module 3 schema.
- Update state through explicit, tested transition code.
- Let the user inspect and correct recorded details.
- Remove or expire the prototype's own saved state.
- Keep two users' conversations isolated.
- Hand off requests requiring human review.
- Never claim a refund, cancellation, diagnosis, prescription, or other external action was completed.

### Planned standalone code package

Place Module 4's runnable code in `module-04/`, with its own README and dependency definition. Include:

- `src/` — state schema, event transitions, bounded context builder, and storage interface;
- `tests/` — offline transition, correction, isolation, expiry, deletion, and failure tests;
- `tests/conversation_cases.jsonl` or equivalent synthetic multi-turn cases;
- `notebooks/` — a guided lab using fictional examples;
- `reports/` — short evaluation results and a failure analysis.

Reuse concepts from earlier modules, but make Module 4 independently runnable from its own folder. Model-backed tests may be optional and must be separated from deterministic offline tests.

## Assessment

- **State design — 20%:** Clear schema, sources, statuses, and transitions.
- **Corrections and clarification — 20%:** Current facts change correctly and missing details are requested.
- **Isolation and privacy — 25%:** Sessions are scoped; retention, expiry, and deletion work as stated.
- **Evaluation — 25%:** At least 25 synthetic multi-turn cases, metrics, and failure analysis.
- **Communication — 10%:** Setup, limits, and design decisions are explained.

### Passing conditions

- Overall rubric score of at least 70%.
- No cross-session fact leakage in the required isolation tests.
- A corrected value supersedes the prior value and is reflected in responses.
- Deletion and expiry tests pass for the prototype's own store.
- Invalid model output or state updates fail safely.
- No invented policy, verified clinical finding, completed action, or real patient record is used.

## Suggested lesson sequence

1. Establish a multi-turn baseline and document its failures.
2. Define the state schema and transition events.
3. Add missing-information flow and correction handling.
4. Add bounded context and measure its effects.
5. Add retention, deletion, expiry, and user isolation.
6. Run the frozen test set and write a failure report.

## Deliverable

A standalone Module 4 code package, a state diagram or transition specification, 25+ synthetic multi-turn cases, offline tests, and a concise report comparing the baseline with the stateful assistant.

## What comes next

Module 5 will add retrieval from approved, versioned support content and cited answers. Conversation state will tell retrieval what the user is asking; retrieved evidence will remain separate from customer memory.
