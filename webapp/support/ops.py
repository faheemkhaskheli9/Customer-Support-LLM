"""Module 9: readiness checks before the app serves traffic, and the runbook for when one fails."""

from __future__ import annotations

import os

from django.conf import settings
from django.db import connection

from .corpus import ingest, load_corpus
from .health import CLINIC_PREFIX
from .report import load_baseline
from .tools import load_orders

BACKENDS = ("offline", "openai")
RETRIEVAL_MODES = ("keyword", "hybrid")
# Symptom → first action. Kept in code so the page, the command and the article quote one list.
RUNBOOK = (
    ("/readyz is 503 on a config check",
     "Set the variable the check names and restart. Never turn DJANGO_DEBUG on in production to see an error."),
    ("/readyz is 503 on a data check",
     "Roll back the last change to data/. The running process keeps its cached corpus until restart, "
     "so fix the files before restarting."),
    ("/readyz is 503 on the database check",
     "Run python manage.py migrate against the database in DJANGO_SQLITE_PATH."),
    ("release_check is blocked by a safety gate",
     "Do not deploy. The gate names its cases; reproduce one, fix the cause and run the check again."),
    ("Replies show ERROR · handoff and \"cannot process that safely\"",
     "The model provider failed and the turn committed nothing. Check the provider status and the key; "
     "do not switch a real deployment to the offline demo backend."),
    ("A customer sees another customer's order, or an emergency reaches the model",
     "Treat it as an incident: take the app offline, keep the logs, add the message as a case to "
     "data/tool_cases.jsonl or data/health_cases.jsonl, and redeploy only when the report passes."),
)


def check(key: str, label: str, ok: bool, detail: str) -> dict:
    return {"key": key, "label": label, "ok": ok, "detail": detail}


def config_checks() -> list[dict]:
    backend, retrieval = settings.SUPPORT_MODEL_BACKEND, settings.SUPPORT_RETRIEVAL
    missing = [name for name, needed in (("OPENAI_API_KEY", backend == "openai" or retrieval == "hybrid"),
                                         ("OPENAI_MODEL", backend == "openai"))
               if needed and not os.getenv(name, "").strip()]
    https = settings.SESSION_COOKIE_SECURE and settings.CSRF_COOKIE_SECURE and settings.SECURE_SSL_REDIRECT
    return [
        check("config.debug", "Debug is off", not settings.DEBUG, "DJANGO_DEBUG=0"),
        check("config.secret_key", "Secret key is set", settings.SECRET_KEY not in ("", settings.DEV_SECRET_KEY),
              "DJANGO_SECRET_KEY is set and is not the course default"),
        check("config.hosts", "Allowed hosts are named", bool(settings.ALLOWED_HOSTS) and "*" not in settings.ALLOWED_HOSTS,
              "DJANGO_ALLOWED_HOSTS: " + (", ".join(settings.ALLOWED_HOSTS) or "none")),
        check("config.https", "HTTPS only", bool(https), "secure cookies and DJANGO_SECURE_SSL_REDIRECT=1"),
        # Names the missing variables, never their values. No check calls a model.
        check("config.backend", "Model backend is configured",
              backend in BACKENDS and retrieval in RETRIEVAL_MODES and not missing,
              f"{backend} / {retrieval}" + (f"; missing {', '.join(missing)}" if missing else "")),
    ]


def data_checks() -> list[dict]:
    try:
        tables = connection.introspection.table_names()
        database = check("data.database", "Sessions table exists", "django_session" in tables,
                         "migrations applied" if "django_session" in tables else "run python manage.py migrate")
    except Exception as exc:  # an unreachable database is a failed check, not a crash
        database = check("data.database", "Sessions table exists", False, str(exc))
    rows = [database]
    # Read from disk, not the cached retriever, so a broken edit shows before the next restart.
    try:
        chunks = ingest(load_corpus())
        clinic = sum(c.doc_id.startswith(CLINIC_PREFIX) for c in chunks)
        rows += [check("data.corpus", "Corpus loads", bool(chunks), f"{len(chunks)} chunks"),
                 check("data.clinic", "Clinic documents load", bool(clinic), f"{clinic} clinic chunks")]
    except (OSError, ValueError) as exc:
        rows += [check("data.corpus", "Corpus loads", False, str(exc)),
                 check("data.clinic", "Clinic documents load", False, "corpus did not load")]
    for key, label, load, describe in (
            ("data.orders", "Order records load", load_orders, lambda o: f"{len(o.records)} orders"),
            ("data.baseline", "Report baseline loads", load_baseline, lambda b: f"frozen {b['frozen']}")):
        try:
            rows.append(check(key, label, True, describe(load())))
        except (OSError, ValueError, KeyError) as exc:
            rows.append(check(key, label, False, str(exc)))
    return rows


def readiness() -> dict:
    checks = config_checks() + data_checks()
    return {"ready": all(c["ok"] for c in checks), "checks": checks,
            "failing": [c["key"] for c in checks if not c["ok"]]}
