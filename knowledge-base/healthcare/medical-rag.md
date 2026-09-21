# Medical RAG

Medical RAG should be conservative by construction:

1. Filter to approved source types and current versions.
2. Retrieve with metadata for population, topic, and publication date.
3. Rerank for direct relevance and remove contradictory or stale passages.
4. Refuse to answer beyond the retrieved evidence.
5. Attach citations from records, not generated text.
6. Escalate when the request is individualized, urgent, or ambiguous.

Measure retrieval recall separately from answer groundedness. A fluent answer cannot repair missing or outdated evidence.
