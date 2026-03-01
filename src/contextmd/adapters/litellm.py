"""LiteLLM provider adapter."""

from __future__ import annotations

from typing import Any

from contextmd.adapters.base import ProviderAdapter
from contextmd.memory.types import Message, TokenUsage


class LiteLLMAdapter(ProviderAdapter):
    """Adapter for LiteLLM unified API.

    LiteLLM provides a unified interface for 100+ LLM providers.
    It uses OpenAI-compatible request/response format.
    """

    @property
    def provider_name(self) -> str:
        return "litellm"

    def inject_memory(self, request: dict[str, Any], memory_text: str) -> dict[str, Any]:
        """Inject memory into the messages array (OpenAI-compatible format)."""
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
        """Extract token usage from LiteLLM response.

        LiteLLM normalizes usage to OpenAI format.
        """
        usage = getattr(response, "usage", None)
        if usage is None:
            if isinstance(response, dict):
                usage = response.get("usage")
            if usage is None:
                return None

        if isinstance(usage, dict):
            return TokenUsage(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
            )

        return TokenUsage(
            input_tokens=getattr(usage, "prompt_tokens", 0),
            output_tokens=getattr(usage, "completion_tokens", 0),
            total_tokens=getattr(usage, "total_tokens", 0),
        )

    def normalize_messages(self, response: Any) -> list[Message]:
        """Normalize LiteLLM response to Message objects.

        LiteLLM uses OpenAI-compatible response format.
        """
        messages: list[Message] = []

        choices = getattr(response, "choices", None)
        if choices is None and isinstance(response, dict):
            choices = response.get("choices", [])

        if choices:
            for choice in choices:
                if isinstance(choice, dict):
                    msg = choice.get("message", {})
                    messages.append(
                        Message(
                            role=msg.get("role", "assistant"),
                            content=msg.get("content", "") or "",
                            tool_calls=msg.get("tool_calls"),
                        )
                    )
                else:
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
        """Get context window size for a model via LiteLLM.

        LiteLLM has built-in model info, but we provide sensible defaults.
        """
        try:
            import litellm
            model_info = litellm.get_model_info(model)
            max_tokens = model_info.get("max_input_tokens", 128000)
            return int(max_tokens) if max_tokens is not None else 128000
        except Exception:
            pass

        model_lower = model.lower()

        if "claude" in model_lower:
            return 200000
        elif "gpt-5" in model_lower:
            return 400000
        elif "gpt-4.1" in model_lower:
            return 1047576
        elif "gpt-4" in model_lower:
            return 128000
        elif "gemini" in model_lower:
            return 1000000
        elif "mistral" in model_lower:
            return 32768
        elif "llama" in model_lower:
            return 128000
        elif "o3" in model_lower or "o4" in model_lower:
            return 200000

        return 128000

    def _extract_chunk_content(self, chunk: Any) -> str | None:
        """Extract content from a streaming chunk."""
        choices = getattr(chunk, "choices", None)
        if choices is None and isinstance(chunk, dict):
            choices = chunk.get("choices", [])

        if choices:
            choice = choices[0] if choices else None
            if choice:
                if isinstance(choice, dict):
                    delta = choice.get("delta", {})
                    content = delta.get("content")
                    return str(content) if content is not None else None
                else:
                    delta = getattr(choice, "delta", None)
                    if delta:
                        return getattr(delta, "content", None)

        return None
