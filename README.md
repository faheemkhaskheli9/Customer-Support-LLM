# Customer Support LLM Knowledge Base

This knowledge base is the working curriculum and product reference for building a trustworthy customer-support assistant with large language models.

## Start here

1. Read the [course vision](knowledge-base/course/course-vision.md) and [learning outcomes](knowledge-base/course/learning-outcomes.md).
2. Follow the [course outline](knowledge-base/course/course-outline.md) in order.
3. Use the [healthcare project specification](knowledge-base/healthcare/project-specification.md) as the capstone reference implementation.
4. Check [safety](knowledge-base/healthcare/safety.md), [limitations](knowledge-base/healthcare/limitations.md), and [evaluation](knowledge-base/technical/evaluation.md) before treating a prototype as production-ready.

## Knowledge base map

- [Course](knowledge-base/course/): audience, outcomes, teaching strategy, and differentiation.
- [Modules](knowledge-base/modules/): the nine-part learning path from foundations through deployment.
- [Healthcare project](knowledge-base/healthcare/): the domain project, architecture, retrieval design, terminology, and safety boundaries.
- [Technical reference](knowledge-base/technical/): LLMs, embeddings, vector databases, RAG, agents, tool calling, evaluation, and deployment.
- [Exercises](knowledge-base/exercises/): labs, quizzes, assignments, and capstone guidance.
- [Research](knowledge-base/research/): sources, competitors, technology watch, and change history.
- [Glossary](knowledge-base/glossary.md): shared vocabulary.

## Core principles

- Ground answers in approved sources and cite the evidence used.
- Return a clear fallback when retrieval finds no usable evidence.
- Keep provider integrations behind replaceable interfaces.
- Minimize, redact, and audit sensitive customer data.
- Evaluate quality, safety, latency, and cost together.
- Keep human escalation available for consequential or uncertain cases.

## One evolving web app

[Run the Django web app](webapp/README.md). Each module adds a feature to this same project:

- [Module 1](docs/module-01.md): one request, support instructions, and metrics.
- [Module 2](docs/module-02.md): bounded multi-turn context and controlled failures.
- [Module 3](knowledge-base/modules/module-03.md): validated support routes and a 24-case offline evaluation.
- [Module 4](knowledge-base/modules/module-04.md): reported facts, corrections, browser-session isolation, retention, expiry, and deletion.

The older `module-01/` through `module-04/` CLI packages remain for existing published links. They are historical references; new features are added to `webapp/`. Previous article versions are kept under `docs/legacy/` and `knowledge-base/modules/legacy/`.
