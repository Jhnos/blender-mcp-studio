"""SessionStorePort — abstract interface for persistent session storage.

Replaces the in-memory dict in the chat router, enabling sessions to survive
API restarts and supporting multi-process deployments.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from src.core.domain.session import Session


class SessionStorePort(ABC):
    """CRUD interface for conversation sessions."""

    @abstractmethod
    async def get(self, session_id: str) -> Session | None:
        """Return the session with the given ID, or None if not found."""

    @abstractmethod
    async def save(self, session: Session) -> None:
        """Persist or update the session."""

    @abstractmethod
    async def delete(self, session_id: str) -> None:
        """Remove a session (e.g., on timeout or explicit close)."""

    @abstractmethod
    async def create(self) -> Session:
        """Create a new empty session, persist it, and return it."""
