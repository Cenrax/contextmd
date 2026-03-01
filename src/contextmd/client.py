"""Main ContextMD client wrapper."""

from __future__ import annotations

import types
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from typing import Any

from contextmd.adapters import AdapterRegistry, ProviderAdapter, detect_provider
from contextmd.config import ContextMDConfig
from contextmd.memory.router import MemoryRouter
from contextmd.memory.types import MemoryType
from contextmd.session import Session


class ChatCompletions:
    """Proxy for OpenAI-style chat.completions interface."""

    def __init__(self, contextmd: ContextMD) -> None:
        self._contextmd = contextmd

    def create(self, **kwargs: Any) -> Any:
        """Create a chat completion with memory injection."""
        return self._contextmd._create_completion(**kwargs)

    async def acreate(self, **kwargs: Any) -> Any:
        """Async create a chat completion with memory injection."""
        return await self._contextmd._acreate_completion(**kwargs)


class Chat:
    """Proxy for OpenAI-style chat interface."""

    def __init__(self, contextmd: ContextMD) -> None:
        self.completions = ChatCompletions(contextmd)


class Messages:
    """Proxy for Anthropic-style messages interface."""

    def __init__(self, contextmd: ContextMD) -> None:
        self._contextmd = contextmd

    def create(self, **kwargs: Any) -> Any:
        """Create a message with memory injection."""
        return self._contextmd._create_completion(**kwargs)

    async def acreate(self, **kwargs: Any) -> Any:
        """Async create a message with memory injection."""
        return await self._contextmd._acreate_completion(**kwargs)


class ContextMD:
    """Main ContextMD wrapper that adds memory to LLM API calls.

    Usage:
        # OpenAI
        client = ContextMD(openai.OpenAI(), memory_dir=".contextmd/")
        response = client.chat.completions.create(model="gpt-5.2", messages=[...])

        # Anthropic
        client = ContextMD(anthropic.Anthropic(), memory_dir=".contextmd/")
        response = client.messages.create(model="claude-opus-4-6", messages=[...])

        # LiteLLM
        import litellm
        client = ContextMD(litellm, memory_dir=".contextmd/")
        response = client.completion(model="gpt-5.2", messages=[...])
    """

    def __init__(
        self,
        client: Any,
        memory_dir: str | Path = ".contextmd",
        config: ContextMDConfig | None = None,
        provider: str | None = None,
    ) -> None:
        """Initialize ContextMD wrapper.

        Args:
            client: The underlying LLM client (OpenAI, Anthropic, or litellm module).
            memory_dir: Directory for memory files.
            config: Optional configuration object.
            provider: Optional provider name override ('openai', 'anthropic', 'litellm').
        """
        self._client = client
        self._provider_name = provider or detect_provider(client)

        if not self._provider_name:
            raise ValueError(
                f"Could not detect provider for client type: {type(client).__name__}. "
                "Please specify the 'provider' parameter explicitly."
            )

        adapter = AdapterRegistry.create(self._provider_name)
        if not adapter:
            raise ValueError(f"No adapter found for provider: {self._provider_name}")

        self._adapter: ProviderAdapter = adapter

        if config:
            self.config = config
            self.config.memory_dir = Path(memory_dir)
        else:
            self.config = ContextMDConfig(memory_dir=Path(memory_dir))

        self.config.ensure_directories()

        self._router = MemoryRouter(self.config)
        self._session: Session | None = None
        self._extraction_engine: Any = None

        self.chat = Chat(self)
        self.messages = Messages(self)

    @property
    def session(self) -> Session:
        """Get or create the current session."""
        if self._session is None or self._session.ended:
            self._session = Session(
                router=self._router,
                extraction_callback=self._run_extraction,
            )
        return self._session

    def new_session(self, name: str | None = None) -> Session:
        """Start a new session, ending the current one if active."""
        if self._session and not self._session.ended:
            self._session.end()

        self._session = Session(
            router=self._router,
            name=name,
            extraction_callback=self._run_extraction,
        )
        return self._session

    def remember(
        self,
        content: str,
        memory_type: MemoryType | str = MemoryType.SEMANTIC,
    ) -> None:
        """Manually save a memory entry.

        Args:
            content: The content to remember.
            memory_type: Type of memory ('semantic', 'episodic', 'procedural').
        """
        self._router.remember(content, memory_type)

    def completion(self, **kwargs: Any) -> Any:
        """LiteLLM-style completion with memory injection."""
        return self._create_completion(**kwargs)

    async def acompletion(self, **kwargs: Any) -> Any:
        """Async LiteLLM-style completion with memory injection."""
        return await self._acreate_completion(**kwargs)

    def _create_completion(self, **kwargs: Any) -> Any:
        """Internal method to create a completion with memory."""
        memory_text = self._router.get_bootstrap_memory()

        model = kwargs.get("model", "")
        context_window = self._adapter.get_context_window_size(model)
        self._router.set_context_window(context_window)

        enriched_request = self._adapter.inject_memory(kwargs, memory_text)

        stream = enriched_request.get("stream", False)

        response = self._call_provider(enriched_request)

        if stream:
            return self._handle_streaming_response(response)

        self._process_response(response)
        return response

    async def _acreate_completion(self, **kwargs: Any) -> Any:
        """Internal async method to create a completion with memory."""
        memory_text = self._router.get_bootstrap_memory()

        model = kwargs.get("model", "")
        context_window = self._adapter.get_context_window_size(model)
        self._router.set_context_window(context_window)

        enriched_request = self._adapter.inject_memory(kwargs, memory_text)

        stream = enriched_request.get("stream", False)

        response = await self._acall_provider(enriched_request)

        if stream:
            return self._handle_streaming_response_async(response)

        self._process_response(response)
        return response

    def _call_provider(self, request: dict[str, Any]) -> Any:
        """Call the underlying provider."""
        if self._provider_name == "openai":
            return self._client.chat.completions.create(**request)
        elif self._provider_name == "anthropic":
            return self._client.messages.create(**request)
        elif self._provider_name == "litellm":
            if isinstance(self._client, types.ModuleType):
                return self._client.completion(**request)
            return self._client.completion(**request)
        else:
            raise ValueError(f"Unknown provider: {self._provider_name}")

    async def _acall_provider(self, request: dict[str, Any]) -> Any:
        """Async call the underlying provider."""
        if self._provider_name == "openai":
            return await self._client.chat.completions.create(**request)
        elif self._provider_name == "anthropic":
            return await self._client.messages.create(**request)
        elif self._provider_name == "litellm":
            if isinstance(self._client, types.ModuleType):
                return await self._client.acompletion(**request)
            return await self._client.acompletion(**request)
        else:
            raise ValueError(f"Unknown provider: {self._provider_name}")

    def _handle_streaming_response(self, stream: Iterator[Any]) -> Iterator[Any]:
        """Handle streaming response with content buffering."""
        buffered_content: list[str] = []

        for chunk in stream:
            content = self._adapter._extract_chunk_content(chunk)
            if content:
                buffered_content.append(content)
            yield chunk

        if buffered_content:
            from contextmd.memory.types import Message
            full_content = "".join(buffered_content)
            self.session.add_message(Message(role="assistant", content=full_content))

    async def _handle_streaming_response_async(
        self, stream: AsyncIterator[Any]
    ) -> AsyncIterator[Any]:
        """Handle async streaming response with content buffering."""
        buffered_content: list[str] = []

        async for chunk in stream:
            content = self._adapter._extract_chunk_content(chunk)
            if content:
                buffered_content.append(content)
            yield chunk

        if buffered_content:
            from contextmd.memory.types import Message
            full_content = "".join(buffered_content)
            self.session.add_message(Message(role="assistant", content=full_content))

    def _process_response(self, response: Any) -> None:
        """Process a non-streaming response."""
        usage = self._adapter.extract_usage(response)
        if usage:
            needs_compaction = self._router.track_usage(usage)
            if needs_compaction:
                self._run_extraction(self.session.messages)

        messages = self._adapter.normalize_messages(response)
        self.session.add_messages(messages)

        should_extract = self._router.increment_message_count()
        if should_extract:
            self._run_extraction(self.session.messages)
            self._router.reset_message_count()

    def _run_extraction(self, messages: list[Any]) -> None:
        """Run the extraction engine on messages."""
        if self._extraction_engine is None:
            try:
                from contextmd.extraction.engine import ExtractionEngine
                self._extraction_engine = ExtractionEngine(
                    config=self.config,
                    client=self._client,
                    adapter=self._adapter,
                )
            except ImportError:
                return

        try:
            facts = self._extraction_engine.extract(messages)
            if facts:
                self._router.save_extracted_facts(facts)
        except Exception:
            pass

    def __getattr__(self, name: str) -> Any:
        """Proxy unknown attributes to the underlying client."""
        return getattr(self._client, name)
