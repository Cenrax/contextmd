"""Tests for provider adapters."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from contextmd.adapters.anthropic import AnthropicAdapter
from contextmd.adapters.litellm import LiteLLMAdapter
from contextmd.adapters.openai import OpenAIAdapter
from contextmd.adapters.registry import AdapterRegistry, detect_provider


class TestOpenAIAdapter:
    """Tests for OpenAI adapter."""

    def test_provider_name(self) -> None:
        adapter = OpenAIAdapter()
        assert adapter.provider_name == "openai"

    def test_inject_memory_empty(self) -> None:
        adapter = OpenAIAdapter()
        request = {"messages": [{"role": "user", "content": "Hello"}]}

        result = adapter.inject_memory(request, "")
        assert result == request

    def test_inject_memory_no_system(self) -> None:
        adapter = OpenAIAdapter()
        request = {"messages": [{"role": "user", "content": "Hello"}]}

        result = adapter.inject_memory(request, "Memory content\n")

        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "system"
        assert result["messages"][0]["content"] == "Memory content\n"

    def test_inject_memory_with_system(self) -> None:
        adapter = OpenAIAdapter()
        request = {
            "messages": [
                {"role": "system", "content": "You are helpful."},
                {"role": "user", "content": "Hello"},
            ]
        }

        result = adapter.inject_memory(request, "Memory: ")

        assert len(result["messages"]) == 2
        assert result["messages"][0]["content"] == "Memory: You are helpful."

    def test_get_context_window_size(self) -> None:
        adapter = OpenAIAdapter()

        assert adapter.get_context_window_size("gpt-5.2") == 400000
        assert adapter.get_context_window_size("gpt-4.1") == 1047576
        assert adapter.get_context_window_size("gpt-4o") == 128000
        assert adapter.get_context_window_size("unknown-model") == 128000


class TestAnthropicAdapter:
    """Tests for Anthropic adapter."""

    def test_provider_name(self) -> None:
        adapter = AnthropicAdapter()
        assert adapter.provider_name == "anthropic"

    def test_inject_memory_empty(self) -> None:
        adapter = AnthropicAdapter()
        request = {"messages": [{"role": "user", "content": "Hello"}]}

        result = adapter.inject_memory(request, "")
        assert result == request

    def test_inject_memory_no_system(self) -> None:
        adapter = AnthropicAdapter()
        request = {"messages": [{"role": "user", "content": "Hello"}]}

        result = adapter.inject_memory(request, "Memory content")

        assert result["system"] == "Memory content"

    def test_inject_memory_with_system_string(self) -> None:
        adapter = AnthropicAdapter()
        request = {
            "system": "You are helpful.",
            "messages": [{"role": "user", "content": "Hello"}],
        }

        result = adapter.inject_memory(request, "Memory: ")

        assert result["system"] == "Memory: You are helpful."

    def test_get_context_window_size(self) -> None:
        adapter = AnthropicAdapter()

        assert adapter.get_context_window_size("claude-opus-4-6") == 200000
        assert adapter.get_context_window_size("claude-sonnet-4-6") == 200000
        assert adapter.get_context_window_size("unknown-model") == 200000


class TestLiteLLMAdapter:
    """Tests for LiteLLM adapter."""

    def test_provider_name(self) -> None:
        adapter = LiteLLMAdapter()
        assert adapter.provider_name == "litellm"

    def test_inject_memory_empty(self) -> None:
        adapter = LiteLLMAdapter()
        request = {"messages": [{"role": "user", "content": "Hello"}]}

        result = adapter.inject_memory(request, "")
        assert result == request

    def test_inject_memory_no_system(self) -> None:
        adapter = LiteLLMAdapter()
        request = {"messages": [{"role": "user", "content": "Hello"}]}

        result = adapter.inject_memory(request, "Memory content\n")

        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "system"

    def test_get_context_window_size_fallback(self) -> None:
        adapter = LiteLLMAdapter()

        # Test with unknown model to ensure fallback works
        # Known models may return actual values from litellm.get_model_info
        result = adapter.get_context_window_size("unknown-model-xyz")
        assert result == 128000  # Default fallback


class TestAdapterRegistry:
    """Tests for adapter registry."""

    def test_list_providers(self) -> None:
        providers = AdapterRegistry.list_providers()

        assert "openai" in providers
        assert "anthropic" in providers
        assert "litellm" in providers

    def test_create_adapter(self) -> None:
        adapter = AdapterRegistry.create("openai")
        assert adapter is not None
        assert adapter.provider_name == "openai"

    def test_create_unknown_adapter(self) -> None:
        adapter = AdapterRegistry.create("unknown")
        assert adapter is None


class TestDetectProvider:
    """Tests for provider detection."""

    def test_detect_openai_by_module(self) -> None:
        mock_client = MagicMock()
        mock_client.__class__.__module__ = "openai._client"
        mock_client.__class__.__name__ = "OpenAI"

        provider = detect_provider(mock_client)
        assert provider == "openai"

    def test_detect_anthropic_by_module(self) -> None:
        mock_client = MagicMock()
        mock_client.__class__.__module__ = "anthropic._client"
        mock_client.__class__.__name__ = "Anthropic"

        provider = detect_provider(mock_client)
        assert provider == "anthropic"

    def test_detect_unknown(self) -> None:
        mock_client = MagicMock()
        mock_client.__class__.__module__ = "some.unknown.module"
        mock_client.__class__.__name__ = "UnknownClient"

        provider = detect_provider(mock_client)
        assert provider is None
