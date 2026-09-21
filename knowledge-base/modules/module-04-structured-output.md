# Module 04: Structured Output

## Goal
Make model responses safe for application code to consume.

## Topics
JSON Schema; typed parsing; validation and repair; enums; refusal and uncertainty fields; schema evolution.

## Lab
Define an `Answer` object with `answer`, `confidence`, `citations`, `needs_human`, and `reason`. Reject missing or out-of-range fields.

## Check
Malformed output is an explicit model/backend error, never silently coerced into a successful support response.
