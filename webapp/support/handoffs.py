"""Support agent handoffs: one reference per conversation; the log keeps IDs only."""

from __future__ import annotations

from uuid import uuid4

from .models import Handoff

REASONS = dict(Handoff.REASONS)
SESSION_KEY = "agent_handoff"  # this conversation's open reference
RECENT = 10


def reason(turn) -> str:
    """Set from the turn in code, never from model text."""
    if turn.status != "ok":
        return "unavailable"
    if (turn.retrieval or {}).get("grounding") in ("declined", "invalid_output"):
        return "not_confirmed"
    if (turn.tool or {}).get("decision") == "rate_limited":
        return "lookup_limit"
    return "needs_review"


def open_handoff(session, turn) -> str:
    """Return this conversation's reference for a handoff reply, or "" for any other reply.

    Safety-screened replies keep nothing, so they open no handoff. A later handoff in the
    same conversation reuses the reference instead of adding a record."""
    if turn.route != "handoff" or turn.safety:
        return ""
    if session.get(SESSION_KEY):
        return session[SESSION_KEY]
    record = Handoff.objects.create(
        reference=f"HO-{uuid4().hex[:8].upper()}", reason=reason(turn),
        sources=", ".join(dict.fromkeys(f"{s['doc_id']} v{s['version']}" for s in turn.sources))[:300],
        tool_decision=(turn.tool or {}).get("decision", ""))
    session[SESSION_KEY] = record.reference
    return record.reference


def summary(limit: int = RECENT) -> dict:
    counts = {key: 0 for key in REASONS}
    for key in Handoff.objects.values_list("reason", flat=True):
        counts[key] += 1
    return {"total": sum(counts.values()),
            "reasons": [{"reason": key, "label": REASONS[key], "count": n} for key, n in counts.items() if n],
            "recent": list(Handoff.objects.all()[:limit])}
