"""Short-lived local memory. The caller supplies an authenticated owner ID."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import uuid4

from .state import ConversationState


class SessionNotFound(KeyError):
    pass


class MemoryStore:
    def __init__(self, *, ttl: timedelta = timedelta(minutes=30),
                 clock: Callable[[], datetime] | None = None) -> None:
        if ttl <= timedelta(0):
            raise ValueError("TTL must be positive")
        self.ttl = ttl
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._sessions: dict[tuple[str, str], ConversationState] = {}

    def _now(self) -> datetime:
        now = self.clock()
        if now.tzinfo is None:
            raise ValueError("Clock must return a timezone-aware datetime")
        return now

    def create(self, owner_id: str) -> ConversationState:
        if not owner_id or not owner_id.strip():
            raise ValueError("Authenticated owner ID required")
        self.sweep_expired()
        now = self._now()
        state = ConversationState(str(uuid4()), now, now + self.ttl)
        self._sessions[(owner_id, state.session_id)] = deepcopy(state)
        return deepcopy(state)

    def get(self, owner_id: str, session_id: str) -> ConversationState:
        key = (owner_id, session_id)
        state = self._sessions.get(key)
        if state is None:
            raise SessionNotFound("Unknown or unavailable session")
        if self._now() >= state.expires_at:
            del self._sessions[key]
            raise SessionNotFound("Unknown or unavailable session")
        return deepcopy(state)

    def save(self, owner_id: str, state: ConversationState) -> None:
        self.get(owner_id, state.session_id)
        self._sessions[(owner_id, state.session_id)] = deepcopy(state)

    def delete(self, owner_id: str, session_id: str) -> bool:
        # Do not reveal whether a session exists under a different owner.
        return self._sessions.pop((owner_id, session_id), None) is not None

    def sweep_expired(self) -> int:
        now = self._now()
        expired = [key for key, state in self._sessions.items() if now >= state.expires_at]
        for key in expired:
            del self._sessions[key]
        return len(expired)
