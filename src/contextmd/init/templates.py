"""Templates for CLAUDE.md and folder structure generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


CLAUDE_MD_TEMPLATE = '''# Project Memory Instructions

This project uses [contextmd](https://github.com/subham/contextmd) for persistent memory across sessions.

## Quick Start

At the start of every session, run:
```bash
contextmd show
```
Treat the output as your persistent memory about this project and user.

Before ending a session, run:
```bash
contextmd save
```
This extracts and stores what you learned for future sessions.

## Available Commands

- `contextmd show` - Display current memory
- `contextmd save` - Save session learnings to memory
- `contextmd history` - Show recent activity
- `contextmd add "..."` - Add a specific memory
- `contextmd stats` - Show memory statistics

## Memory Location

All memory is stored in `.contextmd/` as human-readable Markdown files.
'''

CLAUDE_MD_APPEND_SECTION = '''
---

## ContextMD Integration

This project uses contextmd for persistent memory. Run `contextmd show` at session start
and `contextmd save` before ending to maintain context across sessions.
'''

CONFIG_YAML_TEMPLATE = '''# ContextMD Configuration
# See https://github.com/subham/contextmd for documentation

# Memory settings
memory:
  # Maximum lines in MEMORY.md before compaction
  line_cap: 500
  
  # Hours of episodic memory to include in bootstrap
  bootstrap_window_hours: 72

# Extraction settings  
extraction:
  # Enable automatic fact extraction
  enabled: true
  
  # Minimum confidence for extracted facts
  min_confidence: 0.7

# Session settings
session:
  # Auto-save session on exit
  auto_save: true
'''

MEMORY_MD_TEMPLATE = '''# Project Memory

This file contains persistent memory about this project and user preferences.
It is automatically updated by contextmd.

## Project Overview

<!-- Add project description here -->

## User Preferences

<!-- User preferences will be added here -->

## Key Decisions

<!-- Important decisions will be recorded here -->

## Learned Patterns

<!-- Patterns and conventions will be noted here -->
'''


@dataclass
class TemplateResult:
    """Result of template generation."""

    success: bool
    path: Path
    message: str
    created: bool = False
    appended: bool = False


class TemplateGenerator:
    """Generates CLAUDE.md and folder structure templates."""

    def __init__(self, project_dir: Optional[Path] = None) -> None:
        self.project_dir = project_dir or Path.cwd()

    def create_folder_structure(self, memory_dir: Optional[Path] = None) -> list[TemplateResult]:
        """
        Create the .contextmd/ folder structure.

        Creates:
        - .contextmd/
        - .contextmd/MEMORY.md
        - .contextmd/config.yaml
        - .contextmd/memory/
        - .contextmd/sessions/
        """
        results = []
        base_dir = memory_dir or (self.project_dir / ".contextmd")

        # Create directories
        dirs_to_create = [
            base_dir,
            base_dir / "memory",
            base_dir / "sessions",
        ]

        for dir_path in dirs_to_create:
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                results.append(TemplateResult(
                    success=True,
                    path=dir_path,
                    message=f"Created directory {dir_path}",
                    created=not dir_path.exists(),
                ))
            except OSError as e:
                results.append(TemplateResult(
                    success=False,
                    path=dir_path,
                    message=f"Failed to create {dir_path}: {e}",
                ))

        # Create MEMORY.md
        memory_file = base_dir / "MEMORY.md"
        results.append(self._write_if_not_exists(memory_file, MEMORY_MD_TEMPLATE))

        # Create config.yaml
        config_file = base_dir / "config.yaml"
        results.append(self._write_if_not_exists(config_file, CONFIG_YAML_TEMPLATE))

        return results

    def create_claude_md(
        self,
        append_if_exists: bool = True,
        force: bool = False,
    ) -> TemplateResult:
        """
        Create or update CLAUDE.md at project root.

        Args:
            append_if_exists: If True, append integration section to existing file.
            force: If True, overwrite existing file completely.
        """
        claude_md_path = self.project_dir / "CLAUDE.md"

        if claude_md_path.exists() and not force:
            if append_if_exists:
                return self._append_to_claude_md(claude_md_path)
            return TemplateResult(
                success=True,
                path=claude_md_path,
                message="CLAUDE.md already exists (skipped)",
            )

        return self._write_file(claude_md_path, CLAUDE_MD_TEMPLATE, created=True)

    def _append_to_claude_md(self, path: Path) -> TemplateResult:
        """Append contextmd section to existing CLAUDE.md."""
        try:
            content = path.read_text()

            # Check if already has contextmd section
            if "contextmd" in content.lower():
                return TemplateResult(
                    success=True,
                    path=path,
                    message="CLAUDE.md already has contextmd section (skipped)",
                )

            # Append the section
            new_content = content.rstrip() + "\n" + CLAUDE_MD_APPEND_SECTION
            path.write_text(new_content)

            return TemplateResult(
                success=True,
                path=path,
                message="Appended contextmd section to CLAUDE.md",
                appended=True,
            )
        except OSError as e:
            return TemplateResult(
                success=False,
                path=path,
                message=f"Failed to update CLAUDE.md: {e}",
            )

    def _write_if_not_exists(self, path: Path, content: str) -> TemplateResult:
        """Write file only if it doesn't exist."""
        if path.exists():
            return TemplateResult(
                success=True,
                path=path,
                message=f"{path.name} already exists (skipped)",
            )
        return self._write_file(path, content, created=True)

    def _write_file(self, path: Path, content: str, created: bool = False) -> TemplateResult:
        """Write content to file."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            return TemplateResult(
                success=True,
                path=path,
                message=f"Created {path}",
                created=created,
            )
        except OSError as e:
            return TemplateResult(
                success=False,
                path=path,
                message=f"Failed to create {path}: {e}",
            )

    def create_gitignore_entry(self) -> TemplateResult:
        """Add .contextmd/ to .gitignore if not already present."""
        gitignore_path = self.project_dir / ".gitignore"
        entry = "\n# ContextMD memory (optional - remove if you want to version control memory)\n# .contextmd/\n"

        if not gitignore_path.exists():
            return TemplateResult(
                success=True,
                path=gitignore_path,
                message=".gitignore not found (skipped)",
            )

        try:
            content = gitignore_path.read_text()
            if ".contextmd" in content:
                return TemplateResult(
                    success=True,
                    path=gitignore_path,
                    message=".gitignore already has .contextmd entry (skipped)",
                )

            # Append entry (commented out by default - let user decide)
            new_content = content.rstrip() + entry
            gitignore_path.write_text(new_content)

            return TemplateResult(
                success=True,
                path=gitignore_path,
                message="Added .contextmd entry to .gitignore (commented)",
                appended=True,
            )
        except OSError as e:
            return TemplateResult(
                success=False,
                path=gitignore_path,
                message=f"Failed to update .gitignore: {e}",
            )
