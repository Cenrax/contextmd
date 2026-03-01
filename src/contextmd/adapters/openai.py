"""OpenAI provider adapter."""

from __future__ import annotations

from typing import Any

from contextmd.adapters.base import ProviderAdapter
from contextmd.memory.types import Message, TokenUsage

MODEL_CONTEXT_WINDOWS = {
    # GPT-5.x family (latest flagship models)
    "gpt-5.2": 400000,
    "gpt-5.2-pro": 400000,
    "gpt-5.1": 400000,
    "gpt-5": 400000,
    "gpt-5-mini": 400000,
    "gpt-5-nano": 400000,
    "gpt-5.2-chat": 128000,
    "gpt-5.1-codex": 400000,
    "gpt-5.1-codex-mini": 400000,
    # GPT-4.1 family
    "gpt-4.1": 1047576,
    "gpt-4.1-mini": 1047576,
    "gpt-4.1-nano": 1047576,
    # GPT-4o family (multimodal)
    "gpt-4o": 128000,
    "gpt-4o-mini": 128000,
    # o-series reasoning models
    "o1": 200000,
    "o1-mini": 128000,
    "o1-preview": 128000,
    "o3": 200000,
    "o3-mini": 200000,
    "o3-pro": 200000,
    "o4-mini": 200000,
}


class OpenAIAdapter(ProviderAdapter):
    """Adapter for OpenAI API."""

    @property
    def provider_name(self) -> str:
        return "openai"

    def inject_memory(self, request: dict[str, Any], memory_text: str) -> dict[str, Any]:
        """Inject memory into the system message."""
        if not memory_text:
            return request

        messages = list(request.get("messages", []))

        if messages and messages[0].get("role") == "system":
            messages[0] = {
                **messages[0],
                "content": memory_text + messages[0].get("content", ""),
            }
        else:
            messages.insert(0, {"role": "system", "content": memory_text})

        return {**request, "messages": messages}

    def extract_usage(self, response: Any) -> TokenUsage | None:
        """Extract token usage from OpenAI response."""
        usage = getattr(response, "usage", None)
        if usage is None:
            return None

        return TokenUsage(
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
            total_tokens=getattr(usage, "total_tokens", 0),
        )

    def normalize_messages(self, response: Any) -> list[Message]:
        """Normalize OpenAI response to Message objects."""
        messages: list[Message] = []

        choices = getattr(response, "choices", [])
        for choice in choices:
            msg = getattr(choice, "message", None)
            if msg:
                messages.append(
                    Message(
                        role=getattr(msg, "role", "assistant"),
                        content=getattr(msg, "content", "") or "",
                        tool_calls=getattr(msg, "tool_calls", None),
                    )
                )

        return messages

    def get_context_window_size(self, model: str) -> int:
        """Get context window size for an OpenAI model."""
        if model in MODEL_CONTEXT_WINDOWS:
            return MODEL_CONTEXT_WINDOWS[model]
        sorted_prefixes = sorted(MODEL_CONTEXT_WINDOWS.keys(), key=len, reverse=True)
        for model_prefix in sorted_prefixes:
            if model.startswith(model_prefix):
                return MODEL_CONTEXT_WINDOWS[model_prefix]
        return 128000

    def _extract_chunk_content(self, chunk: Any) -> str | None:
        """Extract content from a streaming chunk."""
        choices = getattr(chunk, "choices", [])
        if choices:
            delta = getattr(choices[0], "delta", None)
            if delta:
                return getattr(delta, "content", None)
        return None
