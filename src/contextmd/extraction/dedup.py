"""Deduplication and contradiction resolution for extracted facts."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from contextmd.extraction.prompts import DEDUP_SYSTEM_PROMPT, DEDUP_USER_PROMPT

if TYPE_CHECKING:
    from contextmd.adapters.base import ProviderAdapter
    from contextmd.config import ContextMDConfig
    from contextmd.storage.memory import MemoryStore


class Deduplicator:
    """Handles deduplication and contradiction resolution for memory entries."""

    def __init__(
        self,
        config: ContextMDConfig,
        store: MemoryStore,
        client: Any,
        adapter: ProviderAdapter,
    ) -> None:
        self.config = config
        self.store = store
        self._client = client
        self._adapter = adapter

    def check_and_resolve(self, new_content: str) -> tuple[bool, str | None]:
        """Check if a new fact is a duplicate or contradiction.

        Args:
            new_content: The new fact to check.

        Returns:
            Tuple of (should_add, contradicted_entry).
            - should_add: True if the fact should be added
            - contradicted_entry: The entry that was contradicted (if any)
        """
        existing_entries = self.store.get_all_semantic_entries()

        if not existing_entries:
            return True, None

        new_lower = new_content.lower().strip()
        for entry in existing_entries:
            entry_lower = entry.lower().strip()
            if entry_lower == new_lower:
                return False, None

            if self._is_similar(new_lower, entry_lower):
                return False, None

        for entry in existing_entries:
            if self._might_conflict(new_content, entry):
                result = self._llm_check(entry, new_content)

                if result == "duplicate":
                    return False, None
                elif result == "contradiction":
                    return True, entry

        return True, None

    def _is_similar(self, a: str, b: str, threshold: float = 0.85) -> bool:
        """Simple word overlap similarity check."""
        words_a = set(a.split())
        words_b = set(b.split())

        if not words_a or not words_b:
            return False

        intersection = len(words_a & words_b)
        union = len(words_a | words_b)

        return (intersection / union) >= threshold

    def _might_conflict(self, new: str, existing: str) -> bool:
        """Quick heuristic check if two facts might conflict."""
        new_words = set(new.lower().split())
        existing_words = set(existing.lower().split())

        common = new_words & existing_words
        if len(common) < 2:
            return False

        conflict_indicators = {"not", "never", "don't", "doesn't", "isn't", "aren't", "no"}
        new_has_negation = bool(new_words & conflict_indicators)
        existing_has_negation = bool(existing_words & conflict_indicators)

        if new_has_negation != existing_has_negation and len(common) >= 3:
            return True

        return len(common) >= 4

    def _llm_check(self, existing: str, new: str) -> str:
        """Use LLM to check for duplicates or contradictions."""
        try:
            messages = [
                {"role": "system", "content": DEDUP_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": DEDUP_USER_PROMPT.format(existing=existing, new=new),
                },
            ]

            model = self.config.extraction_model or "gpt-4.1-nano"

            if hasattr(self._client, "chat"):
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=20,
                    temperature=0,
                )
                result = response.choices[0].message.content.strip().lower()
            elif hasattr(self._client, "messages"):
                response = self._client.messages.create(
                    model=model,
                    system=DEDUP_SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": DEDUP_USER_PROMPT.format(existing=existing, new=new)}],
                    max_tokens=20,
                )
                result = response.content[0].text.strip().lower()
            else:
                import types
                if isinstance(self._client, types.ModuleType):
                    response = self._client.completion(
                        model=model,
                        messages=messages,
                        max_tokens=20,
                        temperature=0,
                    )
                    result = response.choices[0].message.content.strip().lower()
                else:
                    return "different"

            if "duplicate" in result:
                return "duplicate"
            elif "contradiction" in result:
                return "contradiction"
            else:
                return "different"

        except Exception:
            return "different"
