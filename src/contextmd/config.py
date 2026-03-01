"""Configuration management for ContextMD."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal


@dataclass
class ContextMDConfig:
    """Configuration for ContextMD memory system."""

    memory_dir: Path = field(default_factory=lambda: Path(".contextmd"))
    memory_line_cap: int = 200
    bootstrap_window_hours: int = 48
    compaction_threshold: float = 0.8
    snapshot_message_count: int = 15
    extraction_model: str | None = None
    extraction_frequency: Literal["session_end", "every_n_messages", "threshold"] = "session_end"
    extraction_message_interval: int = 10

    def __post_init__(self) -> None:
        if isinstance(self.memory_dir, str):
            self.memory_dir = Path(self.memory_dir)

    @classmethod
    def from_file(cls, config_path: Path) -> ContextMDConfig:
        """Load configuration from a config.md file."""
        if not config_path.exists():
            return cls()

        content = config_path.read_text()
        config_dict: dict[str, str | int | float] = {}

        for line in content.splitlines():
            line = line.strip()
            if line.startswith("- "):
                match = re.match(r"- `(\w+)`:\s*(.+)", line)
                if match:
                    key, value = match.groups()
                    value = value.strip()
                    if value.isdigit():
                        config_dict[key] = int(value)
                    elif value.replace(".", "", 1).isdigit():
                        config_dict[key] = float(value)
                    else:
                        config_dict[key] = value

        return cls(
            memory_line_cap=int(config_dict.get("memory_line_cap", 200)),
            bootstrap_window_hours=int(config_dict.get("bootstrap_window_hours", 48)),
            compaction_threshold=float(config_dict.get("compaction_threshold", 0.8)),
            snapshot_message_count=int(config_dict.get("snapshot_message_count", 15)),
            extraction_model=str(config_dict.get("extraction_model")) if "extraction_model" in config_dict else None,
            extraction_frequency=config_dict.get("extraction_frequency", "session_end"),  # type: ignore
        )

    def to_file(self, config_path: Path) -> None:
        """Save configuration to a config.md file."""
        content = """# ContextMD Configuration

## Settings

- `memory_line_cap`: {memory_line_cap}
- `bootstrap_window_hours`: {bootstrap_window_hours}
- `compaction_threshold`: {compaction_threshold}
- `snapshot_message_count`: {snapshot_message_count}
- `extraction_model`: {extraction_model}
- `extraction_frequency`: {extraction_frequency}
""".format(
            memory_line_cap=self.memory_line_cap,
            bootstrap_window_hours=self.bootstrap_window_hours,
            compaction_threshold=self.compaction_threshold,
            snapshot_message_count=self.snapshot_message_count,
            extraction_model=self.extraction_model or "default",
            extraction_frequency=self.extraction_frequency,
        )

        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(content)

    def ensure_directories(self) -> None:
        """Create the memory directory structure if it doesn't exist."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        (self.memory_dir / "memory").mkdir(exist_ok=True)
        (self.memory_dir / "sessions").mkdir(exist_ok=True)

        memory_file = self.memory_dir / "MEMORY.md"
        if not memory_file.exists():
            memory_file.write_text("""# Memory

## Semantic Facts

## Procedural Rules

""")

        config_file = self.memory_dir / "config.md"
        if not config_file.exists():
            self.to_file(config_file)
