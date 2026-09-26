# Module 1 — Build Your First Customer-Support LLM

**Project:** Customer Support LLM  
**Build:** Customer Support Assistant v0.1  
**Level:** Beginner  
**Learning loop:** Build → Break → Measure → Improve

A chatbot can produce a confident answer without knowing your company's policy. In this module, you will make a first model request, add basic support instructions, and test what changes.

The code is a small learning prototype. It does not have company policy documents, customer records, order lookup, or tools that can change accounts. It must never claim that a refund, cancellation, or other action has happened unless a trusted application confirms it.

## What you will learn

By the end, you will be able to:

- send a request to an LLM from Python;
- keep an API key out of source code;
- explain why fluent output is not the same as verified information;
- compare a raw model response with one guided by support instructions;
- measure response latency and token usage;
- identify unsupported claims and false action confirmations.

## Get the complete code

The standalone code companion has its own package, notebook, and offline tests. It does not import code from later modules.

[Open the Module 1 code workspace on GitHub](https://github.com/faheemkhaskheli9/Customer-Support-LLM/tree/main/module-01)

The notebook's live cells make API calls and may incur charges. The tests run offline.

## 1. Set up the lab

Install Python 3.10 or newer. Then open a terminal at the repository root:

```bash
cd module-01
python -m venv .venv
```

Activate the environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# Linux/macOS
source .venv/bin/activate
```

Install the project:

```bash
python -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and put your API key in the local file:

```bash
# Linux/macOS
cp .env.example .env

# Windows
copy .env.example .env
```

Never commit `.env`, paste a real key into a notebook, or include it in a screenshot.

## 2. Make a baseline request

Before adding rules, test the model with a fictional support question:

```python
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
response = client.responses.create(
    model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
    input="Can I return headphones after 45 days?",
)
print(response.output_text)
```

This example intentionally supplies no return policy. If the model gives a specific answer anyway, that answer is not company evidence. A plausible completion is not a verified policy.

At a simplified level, a language model estimates a likely next token from preceding context:

```text
P(next token | previous tokens)
```

This helps explain why a model can write a coherent sentence without having access to the facts needed to support it.

## 3. Add application instructions

The code companion stores support rules in `module-01/src/support_basics/prompts.py`. The rules tell the assistant not to invent policies and not to report actions as completed.

A prompt can guide behavior, but it cannot verify a policy or enforce permissions. Those responsibilities belong to the application and trusted data sources.

```text
Customer asks about a policy
        ↓
Application checks approved policy data
        ↓
Assistant explains the verified information
```

If approved information is missing, the system should say it cannot verify the answer or ask a focused question. The next course modules add stronger state management, retrieval, and validation.

## 4. Measure before improving

Use the same questions for the raw model and the instructed assistant:

- What is your warranty period?
- Can I return headphones after 45 days?
- Cancel order ORD-12345.
- Give me a 50% discount code.
- Where is my order?

For each response, record:

- whether the answer used evidence provided by the application;
- whether it invented a policy, price, discount, or customer fact;
- whether it claimed to complete an action;
- whether it asked for missing information;
- latency and token usage, when available.

Do not count a fluent response as a successful response. The point is to discover failure cases and improve them.

## 5. Run the assistant and tests

From `module-01/`, start the interactive assistant:

```bash
support-basics
```

Use fictional examples and type `quit` to exit.

Run the unit tests without contacting the API:

```bash
pytest
```

The tests use a fake model client. They check request construction, empty input handling, and response metrics. They do not prove that a real model will always behave safely.

## 6. Break it deliberately

Try requests that ask the assistant to reveal hidden instructions, invent a discount, or claim that an order has been cancelled. Record what happened and how the application should handle it.

Never use a real person's health information in this course. The assistant is not a medical service and must not diagnose, prescribe, or make emergency decisions.

## Definition of done

- [ ] The standalone package installs in a virtual environment.
- [ ] The assistant makes a model request without a hard-coded secret.
- [ ] The same prompt can be tested with raw and guided model behavior.
- [ ] Latency and token usage are captured when returned by the provider.
- [ ] Offline tests pass without an API key.
- [ ] At least one unsupported claim or other failure is recorded.
- [ ] The assistant does not claim that an action was completed.

This is a learning baseline, not a production-readiness threshold.

## Next: Module 2

Module 2 turns the experiment into a structured healthcare customer-support application. You will add conversation state, input validation, an interchangeable model interface, controlled errors, and tests that do not spend API credits.

[Continue to Module 2](https://github.com/faheemkhaskheli9/Customer-Support-LLM/blob/main/docs/module-02.md)
