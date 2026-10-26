# Module 9 — Deployment and Runbook

> **Project:** Customer Support LLM  
> **Build:** Customer Support Assistant v0.9 — readiness checks, production settings, a release check and a runbook  
> **Level:** Beginner to practical LLM engineering  
> **Learning loop:** Build → Break → Measure → Improve

**Implementation:** Module 9 extends the shared [Django web app](../../webapp/) with the page at `/?stage=9` (`support/ops.py`, the `/healthz` and `/readyz` endpoints, the `release_check` management command, production settings in `config/settings.py`). The article is [module-09.md](module-09.md).

## Module mission

Module 8 decides whether a change can ship. This module decides whether a *configuration* can serve traffic, and what to do when it cannot. The app now runs with debug off, a real secret key, named hosts, HTTPS only and a production server, and it says so through two endpoints and one command.

The module rests on one distinction. **Liveness** (`/healthz`) says the process answers. **Readiness** (`/readyz`) says this configuration and its data can serve customers. A platform restarts a process that is not live and stops routing to one that is not ready; mixing them up either restarts a healthy process in a loop or sends customers to a broken one.

## Prerequisites

- Completed Modules 1–8 in the shared web app.
- The Module 8 report and its `evaluation_report` command.

## What you will build

**Customer Support Assistant v0.9** will:

1. Read every production setting from `DJANGO_*` variables; refuse to start with debug off and no secret key.
2. Run ten readiness checks without calling a model: five on configuration, five on the database and data files (`readiness()`).
3. Serve `/healthz` (always `{"status": "ok"}`) and `/readyz` (503 with the failing check keys, never their details).
4. Run `python manage.py release_check`: the readiness checks, Django's `check --deploy` and the Module 8 report, exiting with 1 when any fails.
5. Show the checks and a runbook (symptom → first action) on the page at `/?stage=9`.

## Learning outcomes

By the end, learners can:

- tell liveness from readiness and point each probe at the right endpoint;
- move every production setting into the environment, with safe failure when one is missing;
- check configuration and data before traffic arrives, without calling a model or exposing a secret;
- combine readiness, framework checks and the evaluation report into one release command;
- write a runbook where each symptom has one first action.

## Build → Break → Measure → Improve

- **Build:** production settings, the readiness checks, the two endpoints, the release check, the page and the runbook.
- **Break:** turn debug on in production; remove the secret key; set the course default key; choose the OpenAI backend with no key; break a corpus file's front matter; point the database at a fresh file; raise one baseline number.
- **Measure:** for each break, record the `/readyz` status and failing keys and the `release_check` result.
- **Improve:** readiness does not check the model provider, and the offline demo backend passes in production. Add a check that refuses `offline` when a deployment flag is set.

## Boundaries

- Readiness checks configuration and files, not whether the model provider answers or whether answers are good.
- SQLite on one server is not a highly available database.
- The runbook gives first actions for a teaching app. A real service also needs alerting, on-call ownership and a tested rollback.

## After this module

Module 9 is the last module. The support agent at `/` combines Modules 1–7; ship it only with `release_check` passing.
