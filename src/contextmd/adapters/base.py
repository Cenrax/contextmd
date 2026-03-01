"""Abstract base class for provider adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from typing import Any

from contextmd.memory.types import Message, TokenUsage


class ProviderAdapter(ABC):
    """Abstract interface for LLM provider adapters."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'openai', 'anthropic', 'litellm')."""
        ...

    @abstractmethod
    def inject_memory(self, request: dict[str, Any], memory_text: str) -> dict[str, Any]:
        """Inject memory into the request.

        Args:
            request: The original request parameters.
            memory_text: The memory content to inject.

        Returns:
            Modified request with memory injected into system prompt.
        """
        ...

    @abstractmethod
    def extract_usage(self, response: Any) -> TokenUsage | None:
        """Extract token usage from the response.

        Args:
            response: The API response object.

        Returns:
            TokenUsage object or None if not available.
        """
        ...

    @abstractmethod
    def normalize_messages(self, response: Any) -> list[Message]:
        """Normalize response messages to a common format.

        Args:
            response: The API response object.

        Returns:
            List of normalized Message objects.
        """
        ...

    @abstractmethod
    def get_context_window_size(self, model: str) -> int:
        """Get the context window size for a model.

        Args:
            model: The model name.

        Returns:
            Context window size in tokens.
        """
        ...

    def handle_streaming(
        self,
        stream: Iterator[Any] | AsyncIterator[Any],
    ) -> tuple[Iterator[Any], list[str]]:
        """Handle streaming responses by buffering content.

        Args:
            stream: The streaming response iterator.

        Returns:
            Tuple of (passthrough iterator, buffered content chunks).
        """
        buffered_chunks: list[str] = []

        def passthrough() -> Iterator[Any]:
            for chunk in stream:  # type: ignore
                content = self._extract_chunk_content(chunk)
                if content:
                    buffered_chunks.append(content)
                yield chunk

        return passthrough(), buffered_chunks

    async def handle_streaming_async(
        self,
        stream: AsyncIterator[Any],
    ) -> tuple[AsyncIterator[Any], list[str]]:
        """Handle async streaming responses by buffering content.

        Args:
            stream: The async streaming response iterator.

        Returns:
            Tuple of (passthrough async iterator, buffered content chunks).
        """
        buffered_chunks: list[str] = []

        async def passthrough() -> AsyncIterator[Any]:
            async for chunk in stream:
                content = self._extract_chunk_content(chunk)
                if content:
                    buffered_chunks.append(content)
                yield chunk

        return passthrough(), buffered_chunks

    def _extract_chunk_content(self, chunk: Any) -> str | None:
        """Extract content from a streaming chunk. Override in subclasses."""
        return None
