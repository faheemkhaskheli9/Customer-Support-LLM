# Module 06: Tools and Agents

## Goal
Let the assistant take bounded actions without giving it unchecked authority.

## Topics
Tool schemas; allowlists; authentication; confirmation gates; idempotency; state machines; max iterations; time and token budgets; audit events.

## Lab
Implement a support agent that can search policy and draft a ticket, but must ask for confirmation before changing an account.

## Check
Every tool has an owner, input validation, authorization decision, timeout, and failure response.
