# Module 8 — Evaluation and Safety Report

> **Project:** Customer Support LLM  
> **Build:** Customer Support Assistant v0.8 — one report over every evaluation, with release gates and a single verdict  
> **Level:** Beginner to practical LLM engineering  
> **Learning loop:** Build → Break → Measure → Improve

**Implementation:** Module 8 extends the shared [Django web app](../../webapp/) with the page at `/?stage=8` (`support/report.py`, the baseline in `data/report_baseline.json`, the `evaluation_report` management command). The article is [module-08.md](module-08.md).

## Module mission

Modules 3–7 each added an evaluation with its own button. Nobody shipping a change looks at four pages and decides by feel. This module runs all four evaluations together (94 synthetic cases) and turns them into one release decision.

The report separates two kinds of number. **Safety gates** are invariants that must hold exactly: no forbidden passages, no answer model on a miss, no cross-customer leaks, no tool on a handoff, every emergency caught, no model call on a screened emergency, no answers outside clinic admin, every route schema-valid. **Quality metrics** can be imperfect, but may not drop below a frozen baseline. Any failed gate blocks the release and names its cases.

## Prerequisites

- Completed Modules 1–7 in the shared web app.
- The Module 3, 5, 6 and 7 evaluations.

## What you will build

**Customer Support Assistant v0.8** will:

1. Run the Module 3, 5, 6 and 7 evaluations in one call (`run_report`), with one gateway standing in for the model in Modules 5–7.
2. Check eight safety gates exactly (`SAFETY_GATES`).
3. Compare nine quality metrics with a frozen baseline (`QUALITY_GATES`, `data/report_baseline.json`); a drop blocks, a rise is reported.
4. Return a `pass` or `blocked` verdict, with the failing case IDs for every failed gate.
5. Show the report on a page, download it as Markdown, and print it from `python manage.py evaluation_report`, which exits with 1 when blocked.

## Learning outcomes

By the end, learners can:

- tell an invariant from a quality metric and gate each differently;
- freeze a baseline and treat a drop as a regression;
- turn several evaluations into one verdict a script can act on;
- trace every failed gate to case IDs;
- say what a passing report does not establish.

## Build → Break → Measure → Improve

- **Build:** the report, the gates, the baseline, the page, the download and the command.
- **Break:** run the report with a model that always says `clinic_admin`, a hijacked model that asks for another customer's order, and a model that is down; raise one baseline number; remove `"chest pain"` from the emergency screen.
- **Measure:** the offline report passes every gate; record which gates each broken model fails and which still hold.
- **Improve:** the report misses the removed screen phrase because the offline model also catches it. Add a gate or a case that only the screen can pass.

## Boundaries

- A pass is an offline regression check over fictional cases, not proof that the assistant is safe.
- The baseline records the offline backend only. A live model needs its own baseline, frozen from its own runs.
- The report checks outcomes. A protection that another layer duplicates can be removed without a gate failing; unit tests still matter.

## Next module

Module 9 covers deployment and a runbook: running the app outside a laptop, and what to do when a gate fails after release.
