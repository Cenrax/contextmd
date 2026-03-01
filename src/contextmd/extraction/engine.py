"""Extraction engine for identifying facts worth remembering."""

from __future__ import annotations

import json
import types
from typing import TYPE_CHECKING, Any

from contextmd.extraction.dedup import Deduplicator
from contextmd.extraction.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT
from contextmd.memory.types import MemoryType
from contextmd.storage.memory import MemoryStore

if TYPE_CHECKING:
    from contextmd.adapters.base import ProviderAdapter
    from contextmd.config import ContextMDConfig


class ExtractionEngine:
    """LLM-powered extraction engine for identifying memorable facts."""

    def __init__(
        self,
        config: ContextMDConfig,
        client: Any,
        adapter: ProviderAdapter,
    ) -> None:
        self.config = config
        self._client = client
        self._adapter = adapter
        self._store = MemoryStore(config)
        self._dedup = Deduplicator(config, self._store, client, adapter)

    def extract(self, messages: list[Any], last_n: int = 20) -> list[dict[str, Any]]:
        """Extract facts from a conversation.

        Args:
            messages: List of Message objects from the conversation.
            last_n: Number of recent messages to analyze.

        Returns:
            List of extracted facts with type and confidence.
        """
        if not messages:
            return []

        recent_messages = messages[-last_n:]
        conversation_text = self._format_conversation(recent_messages)

        if not conversation_text.strip():
            return []

        raw_facts = self._call_extraction_llm(conversation_text)

        processed_facts: list[dict[str, Any]] = []
        for fact in raw_facts:
            content = fact.get("content", "").strip()
            if not content:
                continue

            memory_type = fact.get("type", "semantic")
            if memory_type not in ("semantic", "episodic", "procedural"):
                memory_type = "semantic"

            confidence = fact.get("confidence", 0.8)
            if not isinstance(confidence, (int, float)):
                confidence = 0.8
            confidence = max(0.0, min(1.0, float(confidence)))

            if confidence < 0.5:
                continue

            if memory_type == "semantic":
                should_add, contradicted = self._dedup.check_and_resolve(content)
                if not should_add:
                    continue
                if contradicted:
                    self._store.remove_semantic_entry(contradicted)
                    self._store.log_contradiction(contradicted, content)

            processed_facts.append({
                "content": content,
                "type": memory_type,
                "confidence": confidence,
            })

        return processed_facts

    def _format_conversation(self, messages: list[Any]) -> str:
        """Format messages into a conversation string."""
        lines: list[str] = []

        for msg in messages:
            if hasattr(msg, "role") and hasattr(msg, "content"):
                role = msg.role.capitalize()
                content = msg.content or ""
                if content.strip():
                    lines.append(f"{role}: {content}")
            elif isinstance(msg, dict):
                role = msg.get("role", "unknown").capitalize()
                content = msg.get("content", "")
                if content and content.strip():
                    lines.append(f"{role}: {content}")

        return "\n\n".join(lines)

    def _call_extraction_llm(self, conversation: str) -> list[dict[str, Any]]:
        """Call the LLM to extract facts."""
        try:
            model = self.config.extraction_model or self._get_default_model()

            messages = [
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": EXTRACTION_USER_PROMPT.format(conversation=conversation),
                },
            ]

            if hasattr(self._client, "chat"):
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0,
                )
                content = response.choices[0].message.content
            elif hasattr(self._client, "messages"):
                response = self._client.messages.create(
                    model=model,
                    system=EXTRACTION_SYSTEM_PROMPT,
                    messages=[
                        {
                            "role": "user",
                            "content": EXTRACTION_USER_PROMPT.format(conversation=conversation),
                        }
                    ],
                    max_tokens=1000,
                )
                content = response.content[0].text
            elif isinstance(self._client, types.ModuleType):
                response = self._client.completion(
                    model=model,
                    messages=messages,
                    max_tokens=1000,
                    temperature=0,
                )
                content = response.choices[0].message.content
            else:
                return []

            return self._parse_json_response(content)

        except Exception:
            return []

    def _parse_json_response(self, content: str) -> list[dict[str, Any]]:
        """Parse JSON response from the extraction LLM."""
        if not content:
            return []

        content = content.strip()

        if content.startswith("```"):
            lines = content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            content = "\n".join(lines)

        try:
            result = json.loads(content)
            if isinstance(result, list):
                return result
            return []
        except json.JSONDecodeError:
            start = content.find("[")
            end = content.rfind("]")
            if start != -1 and end != -1:
                try:
                    return json.loads(content[start : end + 1])
                except json.JSONDecodeError:
                    pass
            return []

    def _get_default_model(self) -> str:
        """Get a default extraction model based on the provider."""
        provider = self._adapter.provider_name

        if provider == "openai":
            return "gpt-4.1-nano"
        elif provider == "anthropic":
            return "claude-haiku-4-5"
        elif provider == "litellm":
            return "gpt-4.1-nano"
        else:
            return "gpt-4.1-nano"
