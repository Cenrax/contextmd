"""Markdown file storage operations."""

from __future__ import annotations

from pathlib import Path

from contextmd.storage.base import StorageBackend


class MarkdownStorage(StorageBackend):
    """File system storage backend for Markdown files."""

    def read(self, path: Path) -> str:
        """Read content from a file."""
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write(self, path: Path, content: str) -> None:
        """Write content to a file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def append(self, path: Path, content: str) -> None:
        """Append content to a file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(content)

    def exists(self, path: Path) -> bool:
        """Check if a file exists."""
        return path.exists()

    def list_files(self, directory: Path, pattern: str = "*") -> list[Path]:
        """List files in a directory matching a pattern."""
        if not directory.exists():
            return []
        return sorted(directory.glob(pattern))

    def count_lines(self, path: Path) -> int:
        """Count the number of lines in a file."""
        content = self.read(path)
        if not content:
            return 0
        return len(content.splitlines())

    def read_lines(self, path: Path, start: int = 0, end: int | None = None) -> list[str]:
        """Read specific lines from a file."""
        content = self.read(path)
        if not content:
            return []
        lines = content.splitlines()
        return lines[start:end]
