# Module 03: Prompting

## Goal
Design prompts that make task boundaries and evidence requirements explicit.

## Topics
Instruction hierarchy; delimiters; few-shot examples; refusal behavior; prompt injection; conversation history; prompt versioning.

## Lab
Create a support prompt that distinguishes policy text from customer-provided text and requires an uncertainty statement when evidence is insufficient.

## Check
Test an input that says to ignore previous instructions. The assistant should treat it as customer content, not a system instruction.
