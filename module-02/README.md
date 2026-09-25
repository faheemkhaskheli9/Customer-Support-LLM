# Module 2 — Healthcare Customer-Support Chatbot

This is the self-contained code companion for Module 2. It has its own Python package, notebook, and offline tests. It does not import source code from Modules 1 or 3.

The chatbot demonstrates input validation, conversation state, a replaceable model interface, and controlled errors. It has no trusted clinic knowledge, medication database, symptom tool, or production safety layer. Do not use it to diagnose, prescribe, or replace professional care.

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

Copy `.env.example` to `.env`, add your key, and keep `.env` out of Git:

~~~bash
# macOS/Linux
cp .env.example .env

# Windows
copy .env.example .env
~~~

## Run the chatbot

~~~bash
healthcare-chat
~~~

## Run offline tests

~~~bash
pytest
~~~

Tests use a fake model provider and do not spend API credits.

## Use the notebook

Open `notebooks/module_02_first_chatbot.ipynb` for a guided walkthrough of the same application concepts. Live model cells require credentials and may incur charges.

## Files

- `src/customer_support/config.py` — environment configuration.
- `src/customer_support/prompts.py` — assistant instructions and boundaries.
- `src/customer_support/conversation.py` — short-term conversation state.
- `src/customer_support/llm.py` — provider adapter and application error.
- `src/customer_support/chatbot.py` — validation and turn orchestration.
- `src/customer_support/cli.py` — terminal interface.
- `tests/test_chatbot.py` — deterministic offline tests.
- `notebooks/module_02_first_chatbot.ipynb` — guided notebook.

A prompt is behavioral guidance, not a security or clinical-safety boundary. Use fictional data only.
