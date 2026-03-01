"""Anthropic provider adapter."""

from __future__ import annotations

from typing import Any

from contextmd.adapters.base import ProviderAdapter
from contextmd.memory.types import Message, TokenUsage

MODEL_CONTEXT_WINDOWS = {
    # Claude 4.6 family (latest - February 2026)
    "claude-opus-4-6": 200000,
    "claude-sonnet-4-6": 200000,
    # Claude 4.5 family
    "claude-opus-4-5": 200000,
    "claude-sonnet-4-5": 200000,
    "claude-haiku-4-5": 200000,
    # Claude 4.x family
    "claude-opus-4-1": 200000,
    "claude-opus-4": 200000,
    "claude-sonnet-4": 200000,
    # Claude 3.x family (still supported)
    "claude-3-7-sonnet": 200000,
    "claude-3-5-sonnet": 200000,
    "claude-3-5-haiku": 200000,
    "claude-3-haiku": 200000,
}


class AnthropicAdapter(ProviderAdapter):
    """Adapter for Anthropic API."""

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def inject_memory(self, request: dict[str, Any], memory_text: str) -> dict[str, Any]:
        """Inject memory into the system parameter."""
        if not memory_text:
            return request

        existing_system = request.get("system", "")

        new_system: str | list[dict[str, str]]
        if isinstance(existing_system, list):
            new_system = [{"type": "text", "text": memory_text}] + existing_system
        elif existing_system:
            new_system = memory_text + str(existing_system)
        else:
            new_system = memory_text

        return {**request, "system": new_system}

    def extract_usage(self, response: Any) -> TokenUsage | None:
        """Extract token usage from Anthropic response."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return None

        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)

        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )

    def normalize_messages(self, response: Any) -> list[Message]:
        """Normalize Anthropic response to Message objects."""
        messages: list[Message] = []

        content_blocks = getattr(response, "content", [])
        text_parts: list[str] = []

        for block in content_blocks:
            if getattr(block, "type", None) == "text":
                text_parts.append(getattr(block, "text", ""))

        if text_parts:
            messages.append(
                Message(
                    role="assistant",
                    content="\n".join(text_parts),
                )
            )

        return messages

    def get_context_window_size(self, model: str) -> int:
        """Get context window size for an Anthropic model."""
        for model_prefix, size in MODEL_CONTEXT_WINDOWS.items():
            if model.startswith(model_prefix):
                return size
        return 200000

    def _extract_chunk_content(self, chunk: Any) -> str | None:
        """Extract content from a streaming chunk."""
        chunk_type = getattr(chunk, "type", None)

        if chunk_type == "content_block_delta":
            delta = getattr(chunk, "delta", None)
            if delta and getattr(delta, "type", None) == "text_delta":
                return getattr(delta, "text", None)

        return None
