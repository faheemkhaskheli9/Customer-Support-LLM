# Healthcare Safety

Safety controls belong in code and operations as well as prompts.

- Minimize PHI before external model calls and keep mapping data inside the trust boundary.
- Classify urgent, self-harm, diagnosis, dosage, and adverse-reaction intents conservatively.
- Use deterministic responses for emergency and escalation categories.
- Require citations and an uncertainty statement for educational answers.
- Keep a human handoff with enough context for continuity, without copying unnecessary data.
- Red-team prompt injection, false reassurance, fabricated sources, and stale guidance.
