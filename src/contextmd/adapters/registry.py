"""Provider adapter registry and detection."""

from __future__ import annotations

from typing import Any

from contextmd.adapters.base import ProviderAdapter


class AdapterRegistry:
    """Registry for provider adapters."""

    _adapters: dict[str, type[ProviderAdapter]] = {}

    @classmethod
    def register(cls, name: str, adapter_class: type[ProviderAdapter]) -> None:
        """Register an adapter class."""
        cls._adapters[name] = adapter_class

    @classmethod
    def get(cls, name: str) -> type[ProviderAdapter] | None:
        """Get an adapter class by name."""
        return cls._adapters.get(name)

    @classmethod
    def create(cls, name: str) -> ProviderAdapter | None:
        """Create an adapter instance by name."""
        adapter_class = cls.get(name)
        if adapter_class:
            return adapter_class()
        return None

    @classmethod
    def list_providers(cls) -> list[str]:
        """List all registered provider names."""
        return list(cls._adapters.keys())


def _register_builtin_adapters() -> None:
    """Register built-in adapters."""
    from contextmd.adapters.anthropic import AnthropicAdapter
    from contextmd.adapters.litellm import LiteLLMAdapter
    from contextmd.adapters.openai import OpenAIAdapter

    AdapterRegistry.register("openai", OpenAIAdapter)
    AdapterRegistry.register("anthropic", AnthropicAdapter)
    AdapterRegistry.register("litellm", LiteLLMAdapter)


def detect_provider(client: Any) -> str | None:
    """Detect the provider type from a client instance.

    Args:
        client: The LLM client instance.

    Returns:
        Provider name ('openai', 'anthropic', 'litellm') or None.
    """
    client_type = type(client).__name__
    client_module = type(client).__module__

    if "openai" in client_module.lower():
        return "openai"

    if "anthropic" in client_module.lower():
        return "anthropic"

    if "litellm" in client_module.lower():
        return "litellm"

    if client_type in ("OpenAI", "AsyncOpenAI"):
        return "openai"

    if client_type in ("Anthropic", "AsyncAnthropic"):
        return "anthropic"

    if hasattr(client, "completion") and hasattr(client, "acompletion"):
        if "litellm" in str(getattr(client, "completion", "")):
            return "litellm"

    import types
    if isinstance(client, types.ModuleType):
        if client.__name__ == "litellm":
            return "litellm"

    return None


_register_builtin_adapters()
