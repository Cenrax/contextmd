"""Abstract base class for storage backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contextmd.memory.types import MemoryEntry


class StorageBackend(ABC):
    """Abstract storage backend interface."""

    @abstractmethod
    def read(self, path: Path) -> str:
        """Read content from a file."""
        ...

    @abstractmethod
    def write(self, path: Path, content: str) -> None:
        """Write content to a file."""
        ...

    @abstractmethod
    def append(self, path: Path, content: str) -> None:
        """Append content to a file."""
        ...

    @abstractmethod
    def exists(self, path: Path) -> bool:
        """Check if a file exists."""
        ...

    @abstractmethod
    def list_files(self, directory: Path, pattern: str = "*") -> list[Path]:
        """List files in a directory matching a pattern."""
        ...


class MemoryStorage(ABC):
    """Abstract interface for memory storage operations."""

    @abstractmethod
    def load_semantic_memory(self) -> str:
        """Load the semantic memory (MEMORY.md)."""
        ...

    @abstractmethod
    def load_episodic_memory(self, hours: int) -> str:
        """Load episodic memory from the last N hours."""
        ...

    @abstractmethod
    def save_memory(self, entry: MemoryEntry) -> None:
        """Save a memory entry to the appropriate file."""
        ...

    @abstractmethod
    def save_session_snapshot(self, session_name: str, content: str) -> None:
        """Save a session snapshot."""
        ...

    @abstractmethod
    def get_memory_line_count(self) -> int:
        """Get the current line count of MEMORY.md."""
        ...

    @abstractmethod
    def remove_semantic_entry(self, content: str) -> bool:
        """Remove a semantic entry from MEMORY.md."""
        ...

    @abstractmethod
    def get_all_semantic_entries(self) -> list[str]:
        """Get all semantic entries from MEMORY.md."""
        ...
