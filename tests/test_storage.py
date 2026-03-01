"""Tests for storage layer."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from contextmd.config import ContextMDConfig
from contextmd.memory.types import MemoryEntry, MemoryType
from contextmd.storage.markdown import MarkdownStorage
from contextmd.storage.memory import MemoryStore


class TestMarkdownStorage:
    """Tests for MarkdownStorage."""

    def test_read_nonexistent_file(self, temp_memory_dir: Path) -> None:
        storage = MarkdownStorage()
        content = storage.read(temp_memory_dir / "nonexistent.md")
        assert content == ""

    def test_write_and_read(self, temp_memory_dir: Path) -> None:
        storage = MarkdownStorage()
        test_file = temp_memory_dir / "test.md"

        storage.write(test_file, "Hello, World!")
        content = storage.read(test_file)

        assert content == "Hello, World!"

    def test_append(self, temp_memory_dir: Path) -> None:
        storage = MarkdownStorage()
        test_file = temp_memory_dir / "test.md"

        storage.write(test_file, "Line 1\n")
        storage.append(test_file, "Line 2\n")

        content = storage.read(test_file)
        assert content == "Line 1\nLine 2\n"

    def test_list_files(self, temp_memory_dir: Path) -> None:
        storage = MarkdownStorage()

        (temp_memory_dir / "file1.md").write_text("content")
        (temp_memory_dir / "file2.md").write_text("content")
        (temp_memory_dir / "file3.txt").write_text("content")

        md_files = storage.list_files(temp_memory_dir, "*.md")
        assert len(md_files) == 2

    def test_count_lines(self, temp_memory_dir: Path) -> None:
        storage = MarkdownStorage()
        test_file = temp_memory_dir / "test.md"

        storage.write(test_file, "Line 1\nLine 2\nLine 3")
        count = storage.count_lines(test_file)

        assert count == 3


class TestMemoryStore:
    """Tests for MemoryStore."""

    def test_load_empty_semantic_memory(self, memory_store: MemoryStore) -> None:
        content = memory_store.load_semantic_memory()
        assert "# Memory" in content

    def test_save_semantic_memory(self, memory_store: MemoryStore) -> None:
        entry = MemoryEntry(
            content="User prefers dark mode",
            memory_type=MemoryType.SEMANTIC,
            timestamp=datetime.now(),
        )
        memory_store.save_memory(entry)

        content = memory_store.load_semantic_memory()
        assert "User prefers dark mode" in content

    def test_save_episodic_memory(self, memory_store: MemoryStore, config: ContextMDConfig) -> None:
        entry = MemoryEntry(
            content="Completed authentication feature",
            memory_type=MemoryType.EPISODIC,
            timestamp=datetime.now(),
        )
        memory_store.save_memory(entry)

        content = memory_store.load_episodic_memory(24)
        assert "Completed authentication feature" in content

    def test_get_all_semantic_entries(self, memory_store: MemoryStore) -> None:
        entries = [
            MemoryEntry(
                content="Fact 1",
                memory_type=MemoryType.SEMANTIC,
                timestamp=datetime.now(),
            ),
            MemoryEntry(
                content="Fact 2",
                memory_type=MemoryType.SEMANTIC,
                timestamp=datetime.now(),
            ),
        ]

        for entry in entries:
            memory_store.save_memory(entry)

        semantic_entries = memory_store.get_all_semantic_entries()
        assert "Fact 1" in semantic_entries
        assert "Fact 2" in semantic_entries

    def test_remove_semantic_entry(self, memory_store: MemoryStore) -> None:
        entry = MemoryEntry(
            content="Entry to remove",
            memory_type=MemoryType.SEMANTIC,
            timestamp=datetime.now(),
        )
        memory_store.save_memory(entry)

        removed = memory_store.remove_semantic_entry("Entry to remove")
        assert removed is True

        entries = memory_store.get_all_semantic_entries()
        assert "Entry to remove" not in entries

    def test_save_session_snapshot(self, memory_store: MemoryStore, config: ContextMDConfig) -> None:
        memory_store.save_session_snapshot("test-session", "Test conversation content")

        sessions_dir = config.memory_dir / "sessions"
        session_files = list(sessions_dir.glob("*.md"))

        assert len(session_files) == 1
        assert "test-session" in session_files[0].name
