"""Bootstrap loading for memory injection."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from contextmd.config import ContextMDConfig
    from contextmd.storage.memory import MemoryStore


class BootstrapLoader:
    """Loads memory for injection into API requests."""

    def __init__(self, config: ContextMDConfig, store: MemoryStore) -> None:
        self.config = config
        self.store = store

    def load(self) -> str:
        """Load all relevant memory for bootstrap injection.

        Returns:
            A formatted string containing semantic memory and recent episodic memory.
        """
        semantic = self.store.load_semantic_memory()
        episodic = self.store.load_episodic_memory(self.config.bootstrap_window_hours)

        parts: list[str] = []

        if semantic.strip():
            parts.append("# Your Memory\n\n" + semantic)

        if episodic.strip():
            parts.append("# Recent Activity\n\n" + episodic)

        if not parts:
            return ""

        return "\n\n---\n\n".join(parts)

    def load_for_system_prompt(self) -> str:
        """Load memory formatted for system prompt injection.

        Returns:
            Memory content wrapped in XML-style tags for clear delineation.
        """
        memory = self.load()
        if not memory:
            return ""

        return f"""<contextmd_memory>
{memory}
</contextmd_memory>

"""
