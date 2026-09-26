# Module 04: Conversation State and Safe Memory

## Goal

Extend the validated structured routing from Module 3 into a bounded, testable multi-turn assistant. Track reported facts, corrections, missing details, retention choices, and deletion while isolating user sessions.

## Topics

State schemas; transition validation; clarification; corrections; provenance; bounded context; session isolation; consent-aware retention; expiry and deletion.

## Lab

Build an explicit conversation state manager around the Module 3 router. Use fictional multi-turn cases and deterministic offline tests. Keep reported information distinct from verified backend facts.

## Check

Corrections supersede prior values, deletion and expiry clear the prototype's own store, and one session cannot reveal another session's data. Invalid outputs fail safely.

## Full outline

See [Module 4 outline](module-04-outline.md). Structured output and schema validation were introduced in Module 3 and are applied to state here.
