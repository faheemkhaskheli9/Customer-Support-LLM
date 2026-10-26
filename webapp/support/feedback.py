"""Customer feedback: rate the latest agent reply once; the log keeps IDs only."""

from __future__ import annotations

from uuid import uuid4

from .models import Feedback

RATINGS = dict(Feedback.RATINGS)
PENDING_KEY = "agent_feedback"  # the one reply this browser session may still rate
RECENT = 10


def offer(session, turn) -> str:
    """Make the latest agent reply rateable and return its ID. Safety-screened replies keep
    nothing in the session, so they cannot be rated and clear any earlier offer."""
    session.pop(PENDING_KEY, None)
    if turn.safety:
        return ""
    turn_id = uuid4().hex
    session[PENDING_KEY] = {
        "turn_id": turn_id, "route": turn.route, "status": turn.status,
        "sources": ", ".join(dict.fromkeys(f"{s['doc_id']} v{s['version']}" for s in turn.sources))[:300],
        "tool_decision": (turn.tool or {}).get("decision", ""),
    }
    return turn_id


def record(session, turn_id: str, rating: str) -> Feedback:
    """The route, sources and decision come from the session, never from the form."""
    if rating not in RATINGS:
        raise ValueError("Choose helpful or not helpful.")
    pending = session.get(PENDING_KEY)
    if not pending or pending["turn_id"] != turn_id:
        raise ValueError("Only the latest reply can be rated, once.")
    session.pop(PENDING_KEY)
    return Feedback.objects.create(rating=rating, **pending)


def summary(limit: int = RECENT) -> dict:
    by_route: dict[str, dict] = {}
    for route, rating in Feedback.objects.values_list("route", "rating"):
        row = by_route.setdefault(route, {"route": route, "helpful": 0, "not_helpful": 0})
        row[rating] += 1
    rows = sorted(by_route.values(), key=lambda r: r["route"])
    return {"total": sum(r["helpful"] + r["not_helpful"] for r in rows),
            "helpful": sum(r["helpful"] for r in rows), "routes": rows,
            "recent": list(Feedback.objects.filter(rating="not_helpful")[:limit])}
