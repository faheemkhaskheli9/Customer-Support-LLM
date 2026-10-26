# Customer Support LLM Knowledge Base

This knowledge base is the working curriculum and product reference for building a trustworthy customer-support assistant with large language models.

## Start here

1. Follow the [course outline](knowledge-base/course/course-outline.md) in order.
2. [Run the Django web app](webapp/README.md) and open each stage as you read its module.
3. Read the [Module 7 article](knowledge-base/modules/module-07.md) for the healthcare project and its safety boundaries.
4. Check the [Module 8 evaluation report](knowledge-base/modules/module-08.md) and the [Module 9 deployment runbook](knowledge-base/modules/module-09.md) before treating a prototype as production-ready.

## Knowledge base map

- [Course](knowledge-base/course/): the course outline.
- [Modules](knowledge-base/modules/): the nine-part learning path from foundations through deployment, with an outline per module from Module 3.
- [Web app](webapp/): the Django app that grows with every module.
- [Module 5 package](module-05/): the standalone `rag_lab` companion to the Module 5 article.
- Historical CLI packages: [Module 1](module-01/), [Module 2](module-02/), [Module 3](module-03/) and [Module 4](module-04/).

## Core principles

- Ground answers in approved sources and cite the evidence used.
- Return a clear fallback when retrieval finds no usable evidence.
- Keep provider integrations behind replaceable interfaces.
- Minimize, redact, and audit sensitive customer data.
- Evaluate quality, safety, latency, and cost together.
- Keep human escalation available for consequential or uncertain cases.

## One evolving web app

[Run the Django web app](webapp/README.md). Each module adds a feature to this same project:

- [Module 1](knowledge-base/modules/module-01.md): one request, support instructions, and metrics.
- [Module 2](knowledge-base/modules/module-02.md): bounded multi-turn context and controlled failures.
- [Module 3](knowledge-base/modules/module-03.md): validated support routes and a 24-case offline evaluation.
- [Module 4](knowledge-base/modules/module-04.md): reported facts, corrections, browser-session isolation, retention, expiry, and deletion.
- [Module 5](knowledge-base/modules/module-05.md): retrieval from a versioned approved corpus, citations from metadata, a no-evidence fallback, and a 34-case retrieval evaluation.
- [Module 6](knowledge-base/modules/module-06.md): a read-only order lookup tool behind sign-in and ownership checks, code-written replies, an audit trail, and a 16-case tool evaluation.
- [Module 7](knowledge-base/modules/module-07.md) ([outline](knowledge-base/modules/module-07-outline.md)): a clinic support page that screens for emergencies and clinical questions in code before any model call, answers only clinic admin questions from approved clinic documents, and a 20-case safety evaluation.
- [Module 8](knowledge-base/modules/module-08.md) ([outline](knowledge-base/modules/module-08-outline.md)): one evaluation and safety report over all 94 cases from Modules 3, 5, 6 and 7, with exact safety gates, a frozen quality baseline and a `pass` or `blocked` verdict.
- [Module 9](knowledge-base/modules/module-09.md) ([outline](knowledge-base/modules/module-09-outline.md)): production settings, ten readiness checks behind `/healthz` and `/readyz`, `python manage.py release_check` (readiness, Django's deploy checks and the Module 8 report) and a runbook.

The older `module-01/` through `module-04/` CLI packages remain for existing published links. They are historical references; new features are added to `webapp/`. `module-05/` is the standalone `rag_lab` companion to the Module 5 article: the same retrieval and grounding without Django. Previous article versions are kept under `knowledge-base/modules/legacy/`.
