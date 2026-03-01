"""Tests for memory router and bootstrap."""

from __future__ import annotations

from datetime import datetime

import pytest

from contextmd.config import ContextMDConfig
from contextmd.memory.bootstrap import BootstrapLoader
from contextmd.memory.router import MemoryRouter
from contextmd.memory.types import MemoryEntry, MemoryType, Message, TokenUsage
from contextmd.storage.memory import MemoryStore


class TestBootstrapLoader:
    """Tests for BootstrapLoader."""

    def test_load_empty_memory(self, config: ContextMDConfig) -> None:
        store = MemoryStore(config)
        loader = BootstrapLoader(config, store)

        memory = loader.load()
        assert memory == "" or "# Memory" in memory

    def test_load_with_semantic_memory(self, config: ContextMDConfig) -> None:
        store = MemoryStore(config)
        loader = BootstrapLoader(config, store)

        entry = MemoryEntry(
            content="User is a Python developer",
            memory_type=MemoryType.SEMANTIC,
            timestamp=datetime.now(),
        )
        store.save_memory(entry)

        memory = loader.load()
        assert "User is a Python developer" in memory

    def test_load_for_system_prompt(self, config: ContextMDConfig) -> None:
        store = MemoryStore(config)
        loader = BootstrapLoader(config, store)

        entry = MemoryEntry(
            content="Test fact",
            memory_type=MemoryType.SEMANTIC,
            timestamp=datetime.now(),
        )
        store.save_memory(entry)

        prompt = loader.load_for_system_prompt()
        assert "<contextmd_memory>" in prompt
        assert "</contextmd_memory>" in prompt


class TestMemoryRouter:
    """Tests for MemoryRouter."""

    def test_remember_semantic(self, memory_router: MemoryRouter) -> None:
        memory_router.remember("User prefers TypeScript", MemoryType.SEMANTIC)

        memory = memory_router.get_bootstrap_memory()
        assert "User prefers TypeScript" in memory

    def test_remember_with_string_type(self, memory_router: MemoryRouter) -> None:
        memory_router.remember("User uses VS Code", "semantic")

        memory = memory_router.get_bootstrap_memory()
        assert "User uses VS Code" in memory

    def test_track_usage_below_threshold(self, memory_router: MemoryRouter) -> None:
        memory_router.set_context_window(100000)

        usage = TokenUsage(input_tokens=1000, output_tokens=500, total_tokens=1500)
        needs_compaction = memory_router.track_usage(usage)

        assert needs_compaction is False

    def test_track_usage_above_threshold(self, memory_router: MemoryRouter) -> None:
        memory_router.set_context_window(10000)

        usage = TokenUsage(input_tokens=7000, output_tokens=2000, total_tokens=9000)
        needs_compaction = memory_router.track_usage(usage)

        assert needs_compaction is True

    def test_check_duplicate(self, memory_router: MemoryRouter) -> None:
        memory_router.remember("User likes Python", MemoryType.SEMANTIC)

        is_dup = memory_router.check_duplicate("User likes Python")
        assert is_dup is True

        is_dup = memory_router.check_duplicate("User likes JavaScript")
        assert is_dup is False

    def test_save_session_snapshot(self, memory_router: MemoryRouter, config: ContextMDConfig) -> None:
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="How are you?"),
            Message(role="assistant", content="I'm doing well, thanks!"),
        ]

        memory_router.save_session_snapshot("test-chat", messages)

        sessions_dir = config.memory_dir / "sessions"
        session_files = list(sessions_dir.glob("*.md"))

        assert len(session_files) == 1

    def test_increment_message_count(self, config: ContextMDConfig) -> None:
        config.extraction_frequency = "every_n_messages"
        config.extraction_message_interval = 3

        router = MemoryRouter(config)

        assert router.increment_message_count() is False
        assert router.increment_message_count() is False
        assert router.increment_message_count() is True

        router.reset_message_count()
        assert router.increment_message_count() is False
