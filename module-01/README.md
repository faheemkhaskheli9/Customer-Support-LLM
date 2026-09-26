# Module 1 — Build Your First Customer-Support LLM

This is the standalone code companion for Module 1. It contains its own Python package, notebook, and offline tests. It does not import code from Modules 2 or 3.

You will build a small command-line assistant, compare a raw model with support instructions, and record what the first version can and cannot do.

> This is an educational prototype. It has no company policy database, customer records, or action tools. Never use it to make clinical decisions or claim that an order, refund, or appointment was changed.

## Requirements

- Python 3.10 or newer
- An OpenAI API key for live model requests
- No API key is needed to run the tests

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

Copy `.env.example` to `.env` and add your key. Never commit `.env`.

~~~bash
# macOS/Linux
cp .env.example .env

# Windows
copy .env.example .env
~~~

## Run the assistant

~~~bash
support-basics
~~~

Ask a fictional customer-support question. Type `quit` to exit.

## Run tests without API calls

~~~bash
pytest
~~~

## Use the notebook

Open `notebooks/module_01_first_support_llm.ipynb` from this directory. It compares a raw model response with one that receives support instructions. Running those cells sends API requests and may incur charges.

## Files

- `src/support_basics/cli.py` — terminal interface.
- `src/support_basics/assistant.py` — provider boundary and response metrics.
- `src/support_basics/prompts.py` — trusted application instructions.
- `notebooks/module_01_first_support_llm.ipynb` — guided experiments.
- `tests/test_assistant.py` — deterministic tests with a fake client.

## What this version does not do

The model does not know your company's actual policies. The app does not verify customer identity, look up orders, issue refunds, or escalate a ticket. A system prompt is behavioral guidance, not a security boundary. Module 2 adds a replaceable provider interface, input validation, conversation state, and tests for a healthcare support prototype.
