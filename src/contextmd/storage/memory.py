"""Memory-specific storage operations."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from contextmd.storage.base import MemoryStorage
from contextmd.storage.markdown import MarkdownStorage

if TYPE_CHECKING:
    from contextmd.config import ContextMDConfig
    from contextmd.memory.types import MemoryEntry

from contextmd.memory.types import MemoryType


class MemoryStore(MemoryStorage):
    """Storage operations for ContextMD memory files."""

    def __init__(self, config: ContextMDConfig) -> None:
        self.config = config
        self.storage = MarkdownStorage()
        self._memory_file = config.memory_dir / "MEMORY.md"
        self._memory_dir = config.memory_dir / "memory"
        self._sessions_dir = config.memory_dir / "sessions"

    def load_semantic_memory(self) -> str:
        """Load the semantic memory (MEMORY.md)."""
        return self.storage.read(self._memory_file)

    def load_episodic_memory(self, hours: int | None = None) -> str:
        """Load episodic memory from the last N hours."""
        if hours is None:
            hours = self.config.bootstrap_window_hours

        cutoff = datetime.now() - timedelta(hours=hours)
        daily_logs: list[str] = []

        for log_file in self.storage.list_files(self._memory_dir, "*.md"):
            try:
                date_str = log_file.stem
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date >= cutoff.replace(hour=0, minute=0, second=0, microsecond=0):
                    content = self.storage.read(log_file)
                    if content.strip():
                        daily_logs.append(f"## {date_str}\n\n{content}")
            except ValueError:
                continue

        return "\n\n".join(daily_logs)

    def save_memory(self, entry: MemoryEntry) -> None:
        """Save a memory entry to the appropriate file."""
        if entry.memory_type == MemoryType.EPISODIC:
            self._save_episodic(entry)
        elif entry.memory_type in (MemoryType.SEMANTIC, MemoryType.PROCEDURAL):
            self._save_semantic(entry)

    def _save_episodic(self, entry: MemoryEntry) -> None:
        """Save an episodic memory entry to today's daily log."""
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self._memory_dir / f"{today}.md"

        if not self.storage.exists(log_file):
            self.storage.write(log_file, f"# Daily Log - {today}\n\n")

        self.storage.append(log_file, entry.to_markdown() + "\n")

    def _save_semantic(self, entry: MemoryEntry) -> None:
        """Save a semantic or procedural memory entry to MEMORY.md."""
        content = self.storage.read(self._memory_file)

        if entry.memory_type == MemoryType.PROCEDURAL:
            section_header = "## Procedural Rules"
        else:
            section_header = "## Semantic Facts"

        if section_header not in content:
            content = content.rstrip() + f"\n\n{section_header}\n\n"

        section_start = content.find(section_header)
        next_section = content.find("\n## ", section_start + 1)

        if next_section == -1:
            insert_pos = len(content)
        else:
            insert_pos = next_section

        new_entry = entry.to_markdown() + "\n"
        new_content = content[:insert_pos].rstrip() + "\n" + new_entry + "\n" + content[insert_pos:].lstrip()

        self._enforce_line_cap(new_content)

    def _enforce_line_cap(self, content: str) -> None:
        """Enforce the line cap on MEMORY.md."""
        lines = content.splitlines()
        if len(lines) > self.config.memory_line_cap:
            semantic_start = None
            procedural_start = None

            for i, line in enumerate(lines):
                if line.strip() == "## Semantic Facts":
                    semantic_start = i
                elif line.strip() == "## Procedural Rules":
                    procedural_start = i

            if semantic_start is not None:
                excess = len(lines) - self.config.memory_line_cap
                entry_lines = []
                for i in range(semantic_start + 1, len(lines)):
                    if lines[i].startswith("## "):
                        break
                    if lines[i].startswith("- "):
                        entry_lines.append(i)

                lines_to_remove = entry_lines[:excess]
                lines = [line for i, line in enumerate(lines) if i not in lines_to_remove]

            content = "\n".join(lines)

        self.storage.write(self._memory_file, content)

    def save_session_snapshot(self, session_name: str, content: str) -> None:
        """Save a session snapshot."""
        timestamp = datetime.now().strftime("%Y-%m-%d")
        safe_name = re.sub(r"[^\w\-]", "-", session_name.lower())
        filename = f"{timestamp}-{safe_name}.md"
        snapshot_file = self._sessions_dir / filename

        snapshot_content = f"""# Session: {session_name}

**Date:** {datetime.now().strftime("%Y-%m-%d %H:%M")}

## Conversation

{content}
"""
        self.storage.write(snapshot_file, snapshot_content)

    def get_memory_line_count(self) -> int:
        """Get the current line count of MEMORY.md."""
        return self.storage.count_lines(self._memory_file)

    def remove_semantic_entry(self, content: str) -> bool:
        """Remove a semantic entry from MEMORY.md."""
        file_content = self.storage.read(self._memory_file)
        lines = file_content.splitlines()

        content_normalized = content.strip().lower()
        new_lines = []
        removed = False

        for line in lines:
            if line.startswith("- "):
                entry_content = line[2:].strip().lower()
                if entry_content == content_normalized:
                    removed = True
                    continue
            new_lines.append(line)

        if removed:
            self.storage.write(self._memory_file, "\n".join(new_lines))

        return removed

    def get_all_semantic_entries(self) -> list[str]:
        """Get all semantic entries from MEMORY.md."""
        content = self.storage.read(self._memory_file)
        entries: list[str] = []

        in_semantic_section = False
        for line in content.splitlines():
            if line.strip() == "## Semantic Facts":
                in_semantic_section = True
                continue
            elif line.startswith("## "):
                in_semantic_section = False
                continue

            if in_semantic_section and line.startswith("- "):
                entries.append(line[2:].strip())

        return entries

    def log_contradiction(self, old_entry: str, new_entry: str) -> None:
        """Log a contradiction resolution to today's daily log."""
        from contextmd.memory.types import MemoryEntry

        log_content = f"Contradiction resolved: '{old_entry}' replaced with '{new_entry}'"
        entry = MemoryEntry(
            content=log_content,
            memory_type=MemoryType.EPISODIC,
            timestamp=datetime.now(),
        )
        self._save_episodic(entry)
