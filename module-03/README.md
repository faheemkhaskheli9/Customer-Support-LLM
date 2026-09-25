# Module 3 — Prompt Engineering Lab

This directory is the complete, self-contained code companion for Module 3. It has its own prompt, Python package, test cases, tests, and notebook. It does not change or import Module 2 source files.

The lab classifies synthetic support requests. It does not complete refunds or order changes and must not be used for diagnosis, prescribing, or emergency decisions.

## Requirements

- Python 3.10+
- OpenAI API key for live model evaluation (unit tests do not require an API key)

## Setup

From this directory:

~~~bash
python -m venv .venv
~~~

Activate the environment:

~~~bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate
~~~

Install the package and developer dependencies:

~~~bash
python -m pip install -e ".[dev]"
~~~

Copy .env.example to .env and add your API key. Never commit .env.

~~~bash
# macOS/Linux
cp .env.example .env

# Windows
copy .env.example .env
~~~

## Run the tests without API calls

~~~bash
pytest
~~~

## Run the evaluation against the configured model

~~~bash
python -m prompt_lab.run_eval --cases tests/prompt_cases.jsonl --output reports/module-03-results.json
~~~

The evaluation sends 20 synthetic prompts to the configured model and may incur API charges. Check your provider's current pricing before running it. The JSON report includes case IDs and route results, not full raw model responses.

## Use the router interactively

~~~bash
python -m prompt_lab.cli
~~~

Enter a synthetic message. Type quit to stop.

## Files

- prompts/support_router_v1.txt — versioned system instructions.
- src/prompt_lab/router.py — prompt assembly, OpenAI adapter, and strict output validation.
- src/prompt_lab/run_eval.py — batch runner and metrics report.
- tests/prompt_cases.jsonl — synthetic evaluation cases.
- tests/ — offline unit tests.
- notebooks/module_03_prompt_engineering.ipynb — guided companion notebook.

## Routes

- answer_from_approved_info: supplied policy directly answers the question.
- ask_clarifying_question: one missing detail is needed to proceed.
- handoff: a person must review or complete the request.
- unsupported: request is out of scope or not answerable from the supplied evidence, with no defined handoff workflow.

Prompt instructions are not a security boundary. User text and policy documents can contain hostile instructions. The model receives no action tools; validate outputs and enforce permissions in application code. Use fictional data only.
