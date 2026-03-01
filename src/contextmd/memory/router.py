"""Memory Router - decides what to read and write."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from contextmd.memory.bootstrap import BootstrapLoader
from contextmd.memory.types import MemoryEntry, MemoryType, Message, TokenUsage
from contextmd.storage.memory import MemoryStore

if TYPE_CHECKING:
    from contextmd.config import ContextMDConfig


class MemoryRouter:
    """Routes memory operations between storage and extraction."""

    def __init__(self, config: ContextMDConfig) -> None:
        self.config = config
        self.store = MemoryStore(config)
        self.bootstrap = BootstrapLoader(config, self.store)
        self._conversation_tokens = 0
        self._message_count = 0
        self._context_window_size = 128000

    def set_context_window(self, size: int) -> None:
        """Set the context window size for the current model."""
        self._context_window_size = size

    def get_bootstrap_memory(self) -> str:
        """Get memory content for injection into requests."""
        return self.bootstrap.load_for_system_prompt()

    def track_usage(self, usage: TokenUsage) -> bool:
        """Track token usage and return True if compaction is needed."""
        self._conversation_tokens = usage.total_tokens
        threshold = int(self._context_window_size * self.config.compaction_threshold)
        return self._conversation_tokens >= threshold

    def increment_message_count(self) -> bool:
        """Increment message count and return True if extraction should run."""
        self._message_count += 1
        if self.config.extraction_frequency == "every_n_messages":
            return self._message_count >= self.config.extraction_message_interval
        return False

    def reset_message_count(self) -> None:
        """Reset the message count after extraction."""
        self._message_count = 0

    def remember(
        self,
        content: str,
        memory_type: MemoryType | str = MemoryType.SEMANTIC,
        confidence: float = 1.0,
    ) -> None:
        """Manually save a memory entry."""
        if isinstance(memory_type, str):
            memory_type = MemoryType(memory_type)

        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            timestamp=datetime.now(),
            confidence=confidence,
        )
        self.store.save_memory(entry)

    def save_extracted_facts(self, facts: list[dict[str, Any]]) -> None:
        """Save facts extracted by the extraction engine."""
        for fact in facts:
            memory_type = MemoryType(fact.get("type", "semantic"))
            entry = MemoryEntry(
                content=fact["content"],
                memory_type=memory_type,
                timestamp=datetime.now(),
                confidence=fact.get("confidence", 0.8),
            )
            self.store.save_memory(entry)

    def save_session_snapshot(self, session_name: str, messages: list[Message]) -> None:
        """Save a session snapshot from the last N messages."""
        meaningful_messages = [
            m for m in messages
            if m.role in ("user", "assistant") and not m.tool_calls
        ]

        snapshot_messages = meaningful_messages[-self.config.snapshot_message_count:]

        content_parts: list[str] = []
        for msg in snapshot_messages:
            role = msg.role.capitalize()
            content_parts.append(f"**{role}:** {msg.content}")

        content = "\n\n".join(content_parts)
        self.store.save_session_snapshot(session_name, content)

    def check_duplicate(self, content: str) -> bool:
        """Check if a semantic entry already exists."""
        existing = self.store.get_all_semantic_entries()
        content_lower = content.lower().strip()

        for entry in existing:
            if entry.lower().strip() == content_lower:
                return True
            if self._is_similar(content_lower, entry.lower()):
                return True

        return False

    def resolve_contradiction(self, old_content: str, new_content: str) -> None:
        """Resolve a contradiction by replacing old with new."""
        self.store.remove_semantic_entry(old_content)
        self.store.log_contradiction(old_content, new_content)
        self.remember(new_content, MemoryType.SEMANTIC)

    def _is_similar(self, a: str, b: str, threshold: float = 0.8) -> bool:
        """Simple similarity check using word overlap."""
        words_a = set(a.split())
        words_b = set(b.split())

        if not words_a or not words_b:
            return False

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)

        return (intersection / union) >= threshold
