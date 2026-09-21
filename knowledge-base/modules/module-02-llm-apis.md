# Module 02: LLM APIs

## Goal
Wrap a model provider in a reliable application boundary.

## Topics
Authentication; request and response schemas; timeouts; retries with backoff; rate limits; streaming; token and cost accounting; provider adapters.

## Lab
Implement a provider interface with a fake backend, typed errors, bounded retries, and request correlation IDs.

## Check
A timeout must be distinguishable from an invalid request and from a model refusal; each has a different recovery path.
