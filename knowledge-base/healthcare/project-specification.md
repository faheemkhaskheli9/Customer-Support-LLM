# Healthcare Support Assistant: Project Specification

## Problem
Help users find trustworthy, plain-language information about medications, symptoms, and healthcare administration without presenting the assistant as a clinician.

## In scope
Source-grounded education, medication lookup, symptom information, appointment and benefits guidance, citations, uncertainty, and human escalation.

## Out of scope
Diagnosis, prescribing, individualized treatment plans, emergency triage as a replacement for emergency services, and autonomous clinical decisions.

## Acceptance criteria
- Answers cite approved, versioned sources.
- Retrieval misses produce a clear limitation and escalation path.
- Sensitive data is minimized and access is auditable.
- High-risk intents trigger conservative handoff behavior.
- Quality, safety, latency, and cost are measured on a versioned test set.
