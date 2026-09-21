# Evaluation

Maintain a versioned dataset of representative, difficult, and adversarial support cases. Measure:

- Retrieval recall and citation coverage.
- Groundedness, correctness, helpfulness, and appropriate refusal.
- Safety violations, privacy leakage, and escalation precision.
- P50/P95 latency, token use, cost, and dependency failures.

Use deterministic checks where possible and a pluggable judge for rubric-based quality. Report case-level rationales, not only aggregate scores.
