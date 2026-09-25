# Module 2: First Healthcare Customer-Support LLM

Companion code for Module 2. This is an educational support chatbot, not a diagnostic or emergency-care system.

## Setup

```bash
python -m venv .venv
```

Activate on Windows:

```powershell
.venv\Scripts\activate
```

Activate on Linux or macOS:

```bash
source .venv/bin/activate
```

Install and configure:

```bash
pip install -e ".[dev]"
cp .env.example .env
```

On Windows, use `copy .env.example .env`. Add your API key to `.env`, then run:

```bash
healthcare-chat
```

Run tests without making an API call:

```bash
pytest
```

## Important limitations

The bot has no trusted clinic knowledge, medication database, symptom tool, or production safety layer yet. It must not be used to diagnose, prescribe, or replace professional care. A prompt is behavioral guidance, not a complete security or clinical-safety boundary.
