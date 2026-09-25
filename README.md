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

## Module code

Each module has a separate code workspace so examples, dependencies, and tests do not get mixed between lessons:

- [Module 1 lesson](docs/module-01.md) · [Module 1 standalone code, notebook, and tests](module-01/)
- [Module 2 lesson](docs/module-02.md) · [Module 2 standalone code, notebook, and tests](module-02/)
- [Module 3 lesson](knowledge-base/modules/module-03.md) · [Module 3 complete code package](module-03/)

Module 3 includes its own prompt, Python router, 24 synthetic regression cases, offline tests, command-line demo, evaluation runner, and notebook. Follow [module-03/README.md](module-03/README.md) for setup.
