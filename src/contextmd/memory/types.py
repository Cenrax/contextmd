"""Memory type definitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any


class MemoryType(Enum):
    """Types of memory that can be stored."""

    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


@dataclass
class MemoryEntry:
    """A single memory entry."""

    content: str
    memory_type: MemoryType
    timestamp: datetime
    confidence: float = 1.0
    metadata: dict[str, Any] | None = None

    def to_markdown(self) -> str:
        """Convert the memory entry to markdown format."""
        timestamp_str = self.timestamp.strftime("%Y-%m-%d %H:%M")
        if self.memory_type == MemoryType.EPISODIC:
            return f"- [{timestamp_str}] {self.content}"
        return f"- {self.content}"


@dataclass
class ExtractedFact:
    """A fact extracted from a conversation."""

    content: str
    memory_type: MemoryType
    confidence: float
    source_message_index: int | None = None


@dataclass
class TokenUsage:
    """Token usage information from an API response."""

    input_tokens: int
    output_tokens: int
    total_tokens: int

    @classmethod
    def from_openai(cls, usage: Any) -> TokenUsage:
        """Create from OpenAI usage object."""
        return cls(
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
        )

    @classmethod
    def from_anthropic(cls, usage: Any) -> TokenUsage:
        """Create from Anthropic usage object."""
        return cls(
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            total_tokens=usage.input_tokens + usage.output_tokens,
        )


@dataclass
class Message:
    """Normalized message format."""

    role: str
    content: str
    name: str | None = None
    tool_calls: list[Any] | None = None
