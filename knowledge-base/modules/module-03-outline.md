# Module 3 — Prompt Engineering as Software Engineering

> **Project:** Customer Support LLM  
> **Build:** Customer Support Assistant v0.3 — prompt-driven support flows  
> **Level:** Beginner to practical LLM engineering  
> **Learning loop:** Build → Break → Measure → Improve

## Module mission

A prompt is part of the application’s behavior. It needs clear requirements, predictable inputs and outputs, version control, tests, and safe failure behavior. In this module, learners replace one-off instructions with reusable prompt templates and a small regression suite for common customer-support tasks.

The assistant may explain approved information, collect details, and route requests. It must not invent company policy, claim to have completed an action it did not perform, or make clinical decisions. Healthcare examples use synthetic data only.

## Prerequisites

- Completed Modules 1 and 2.
- A working Python environment and model client.
- A basic customer-support assistant that handles API errors and records safe usage metadata.

## Learning outcomes

By the end of this module, learners can:

- describe the roles of system instructions, user input, examples, and context;
- write and compare zero-shot and few-shot prompts;
- separate trusted instructions from untrusted user-provided text;
- build reusable, versioned prompt templates;
- request and validate structured output with JSON Schema or Pydantic;
- test prompt behavior against expected and prohibited outcomes;
- measure classification and extraction performance;
- identify tasks that need retrieval, deterministic code, or human review instead of a more elaborate prompt.

## Lesson outline

### 1. Prompt anatomy and task definition

- Define the task, audience, scope, allowed actions, and fallback.
- Distinguish instructions, reference context, examples, and the user’s message.
- Write explicit rules for uncertainty and unsupported requests.
- Identify what the model can say versus what the application must verify.

**Checkpoint:** Turn a vague request such as “help the customer” into a short task specification with acceptance criteria.

### 2. Zero-shot and few-shot prompting

- Establish a zero-shot baseline.
- Add a small number of representative examples.
- Choose examples that cover ordinary, ambiguous, and out-of-scope cases.
- Avoid examples that accidentally teach unsafe or contradictory behavior.
- Change one prompt variable at a time and compare results.

**Lab:** Classify synthetic support messages as answer_from_approved_info, ask_clarifying_question, handoff, or unsupported.

### 3. Prompt templates and versioning

- Use named templates and explicit variables.
- Validate required inputs before rendering a prompt.
- Store prompts separately from application logic where practical.
- Record a prompt version with test results.
- Review prompt changes like code changes.

**Exercise:** Create v1 and v2 of a return-policy prompt, then document what changed and why.

### 4. Untrusted input and instruction boundaries

- Treat customer messages, retrieved text, and uploaded content as data.
- Recognize prompt injection and conflicting instructions.
- Delimit or label untrusted content and state that it cannot override application rules.
- Do not rely on prompt wording alone for authorization or security.
- Keep tool permissions and business rules enforced by application code.

**Break test:** Include a message that asks the assistant to ignore its rules, reveal hidden instructions, or issue an unauthorized refund.

### 5. Structured output and validation

- Define a compact response schema for classification and information extraction.
- Choose explicit enums, nullable values, and required fields.
- Validate model output with JSON Schema or Pydantic.
- Handle malformed, incomplete, or out-of-range output.
- Keep user-facing prose separate from machine-readable fields when needed.

**Example support schema fields:** intent, summary, missing_information, route, needs_human_review.

**Healthcare extension:** Extract only provided synthetic information into fields such as reported_symptoms, duration, medication_name_as_entered, allergies_as_reported, and unknown_fields. Preserve uncertainty and never infer a diagnosis or dose.

### 6. Prompt evaluation and regression testing

- Write test cases before editing the prompt.
- Include normal, ambiguous, adversarial, multilingual, and out-of-scope inputs.
- Define expected behavior and prohibited behavior for each case.
- Score exact fields deterministically where possible.
- Use human review for tone, helpfulness, and nuanced safety behavior.
- Compare versions and keep raw outputs for reproducibility without storing personal data.

**Core metrics:**
- intent classification accuracy and per-class precision/recall;
- required-field extraction precision, recall, and F1;
- schema-valid response rate;
- unsupported-claim rate;
- appropriate clarification and escalation rates.

### 7. When prompting is not enough

- Use deterministic code for permissions, calculations, state changes, and policy thresholds.
- Use approved retrieval sources for changing or company-specific facts.
- Ask a clarifying question when required information is missing.
- Escalate consequential, ambiguous, or high-risk cases to a human.
- Recognize when a task needs a later course module on retrieval or tools.

## Module project

Build **Customer Support Assistant v0.3**, adding a versioned prompt layer and a repeatable evaluation set to the Module 2 application.

### Required behavior

- Route common customer-support intents using a fixed schema.
- Ask for missing details rather than guessing.
- Answer policy questions only from supplied approved text.
- Mark unsupported requests for handoff.
- Ignore instructions embedded in customer-provided text that conflict with system rules.
- In healthcare examples, use synthetic scenarios, preserve “reported” versus verified facts, and route clinical questions for qualified human review.

### Required files

- prompts/ with at least one versioned prompt.
- tests/prompt_cases.jsonl or an equivalent machine-readable test set.
- A runner that executes the cases against the configured model client.
- A short evaluation report comparing the baseline and revised prompt.
- A README section describing limitations and how to run the tests.

### Minimum test set

At least 20 synthetic cases covering:

- routine FAQ and policy questions;
- missing order or account details;
- refund, cancellation, and discount requests;
- ambiguous or conflicting customer messages;
- prompt injection attempts;
- unsupported company claims;
- English plus Urdu or Roman Urdu input;
- healthcare information requests requiring clarification or human review.

## Assessment

| Area | Weight | Evidence |
|---|---:|---|
| Prompt design | 20% | Clear task, scope, constraints, and fallback |
| Structured output | 20% | Schema and validation handle invalid output |
| Evaluation design | 25% | At least 20 cases with expected and prohibited behavior |
| Results and analysis | 20% | Baseline comparison, metrics, and failure analysis |
| Safety and privacy | 15% | No real patient data; appropriate uncertainty and escalation |

### Passing conditions

- Overall score of at least 70%.
- At least one prompt failure is documented and analyzed.
- Invalid structured output does not silently pass as valid.
- No company policy or clinical fact is invented as verified truth.
- Healthcare examples use synthetic data and do not produce autonomous diagnosis, prescribing, or emergency disposition.

## Suggested lesson sequence

1. Specify the task and baseline.
2. Build a zero-shot prompt and run the initial test set.
3. Add examples and a reusable template.
4. Add structured output and validation.
5. Run injection and ambiguity tests.
6. Compare metrics and write the failure analysis.

## Deliverable

A versioned prompt package, a runnable regression suite, and a short report showing what improved, what still fails, and which cases need retrieval, deterministic logic, or human review.

## What comes next

Module 4 will build on this tested prompt layer by introducing conversation state and memory, including correction, consent, retention, deletion, and isolation between users.
