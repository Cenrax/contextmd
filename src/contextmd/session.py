"""Session management for ContextMD."""

from __future__ import annotations

import uuid
import weakref
from datetime import datetime
from typing import TYPE_CHECKING, Any

from contextmd.memory.types import Message

if TYPE_CHECKING:
    from contextmd.memory.router import MemoryRouter


class Session:
    """Manages a conversation session with memory tracking."""

    _active_sessions: weakref.WeakSet[Session] = weakref.WeakSet()

    def __init__(
        self,
        router: MemoryRouter,
        name: str | None = None,
        extraction_callback: Any | None = None,
    ) -> None:
        self.id = str(uuid.uuid4())[:8]
        self.name = name or f"session-{self.id}"
        self.router = router
        self.messages: list[Message] = []
        self.started_at = datetime.now()
        self.ended = False
        self._extraction_callback = extraction_callback

        Session._active_sessions.add(self)

    def add_message(self, message: Message) -> None:
        """Add a message to the session history."""
        self.messages.append(message)

    def add_messages(self, messages: list[Message]) -> None:
        """Add multiple messages to the session history."""
        self.messages.extend(messages)

    def end(self, name: str | None = None) -> None:
        """End the session and save a snapshot.

        Args:
            name: Optional name for the session snapshot.
        """
        if self.ended:
            return

        self.ended = True
        session_name = name or self.name

        if self._extraction_callback and self.messages:
            try:
                self._extraction_callback(self.messages)
            except Exception:
                pass

        if self.messages:
            self.router.save_session_snapshot(session_name, self.messages)

    def __del__(self) -> None:
        """Cleanup on garbage collection."""
        if not self.ended:
            try:
                self.end()
            except Exception:
                pass

    def __enter__(self) -> Session:
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit - end the session."""
        self.end()

    @classmethod
    def get_active_sessions(cls) -> list[Session]:
        """Get all active sessions."""
        return list(cls._active_sessions)
