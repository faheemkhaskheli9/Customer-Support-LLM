"""Customer feedback on agent replies: the only server-side table the course app adds."""

from __future__ import annotations

from django.db import models


class Feedback(models.Model):
    """IDs and decisions only: no message text, reply text, customer or session ID."""

    RATINGS = (("helpful", "Helpful"), ("not_helpful", "Not helpful"))

    created_at = models.DateTimeField(auto_now_add=True)
    turn_id = models.CharField(max_length=32, unique=True)  # one rating per reply
    rating = models.CharField(max_length=12, choices=RATINGS)
    route = models.CharField(max_length=40)
    status = models.CharField(max_length=12)
    sources = models.CharField(max_length=300, blank=True)  # cited "DOC-ID vN", comma-separated
    tool_decision = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ("-created_at", "-id")
