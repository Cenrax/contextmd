"""Pytest configuration and fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Generator

import pytest

from contextmd.config import ContextMDConfig
from contextmd.memory.router import MemoryRouter
from contextmd.storage.memory import MemoryStore


@pytest.fixture
def temp_memory_dir() -> Generator[Path, None, None]:
    """Create a temporary memory directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config(temp_memory_dir: Path) -> ContextMDConfig:
    """Create a test configuration."""
    cfg = ContextMDConfig(memory_dir=temp_memory_dir)
    cfg.ensure_directories()
    return cfg


@pytest.fixture
def memory_store(config: ContextMDConfig) -> MemoryStore:
    """Create a test memory store."""
    return MemoryStore(config)


@pytest.fixture
def memory_router(config: ContextMDConfig) -> MemoryRouter:
    """Create a test memory router."""
    return MemoryRouter(config)
