# Healthcare Project Architecture

```text
User -> API boundary -> intent/risk classifier -> retrieval or approved tool
                                      |                 |
                                      +-> policy guard <-+
                                      |
                              grounded response + citations
                                      |
                           audit event / human escalation
```

Keep the model provider, embedding provider, vector store, and tools behind interfaces. Enforce authorization and safety policy in application code. Store source IDs, versions, retrieval scores, prompt version, model version, and escalation reason with each auditable interaction.
