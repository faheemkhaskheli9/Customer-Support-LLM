# Module 05: Retrieval-Augmented Generation

## Goal
Answer from an approved support corpus and show where the answer came from.

## Topics
Ingestion; chunking; embeddings; vector search; metadata filters; hybrid search; reranking; citation metadata; retrieval misses.

## Lab
Build an idempotent pipeline whose chunk ID hashes source, position, and content. Return a deterministic fallback when no relevant chunks are found.

## Check
Citations come from retrieved metadata, not from trusting citation numbers invented by the model.
