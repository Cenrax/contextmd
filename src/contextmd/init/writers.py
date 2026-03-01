"""MCP config writers for various AI coding tools."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from contextmd.init.detector import ToolConfig, ToolType


@dataclass
class WriteResult:
    """Result of a config write operation."""

    success: bool
    path: Path
    message: str
    was_merged: bool = False
    skipped: bool = False


class MCPConfigWriter:
    """Writes MCP configuration for detected tools."""

    MCP_ENTRY = {
        "command": "contextmd",
        "args": ["serve"],
        "transport": "stdio",
    }

    def __init__(
        self,
        confirm_callback: Optional[Callable[[str, Path, dict], bool]] = None,
    ) -> None:
        """
        Initialize the writer.

        Args:
            confirm_callback: Function to confirm writes to global configs.
                              Receives (tool_name, path, config_entry) and returns bool.
                              If None, global writes are skipped.
        """
        self.confirm_callback = confirm_callback

    def write_config(
        self,
        tool_config: ToolConfig,
        use_global: bool = False,
        force: bool = False,
    ) -> WriteResult:
        """
        Write MCP config for a tool.

        Args:
            tool_config: The tool configuration from detection.
            use_global: If True, write to global config instead of project.
            force: If True, skip confirmation for global configs.

        Returns:
            WriteResult with success status and details.
        """
        if use_global:
            path = tool_config.global_config_path
        else:
            path = tool_config.project_config_path

        if path is None:
            return WriteResult(
                success=False,
                path=Path(),
                message=f"No config path available for {tool_config.name}",
            )

        # Check if this is a global config and needs confirmation
        is_global = self._is_global_path(path)
        if is_global and not force:
            if self.confirm_callback is None:
                return WriteResult(
                    success=False,
                    path=path,
                    message=f"Skipped {tool_config.name} (global config requires confirmation)",
                    skipped=True,
                )

            entry = self._build_entry(tool_config)
            if not self.confirm_callback(tool_config.name, path, entry):
                return WriteResult(
                    success=False,
                    path=path,
                    message=f"Skipped {tool_config.name} (user declined)",
                    skipped=True,
                )

        return self._write_mcp_entry(path, tool_config)

    def write_all(
        self,
        tool_configs: list[ToolConfig],
        prefer_project: bool = True,
    ) -> list[WriteResult]:
        """
        Write MCP configs for all provided tools.

        Args:
            tool_configs: List of tool configurations.
            prefer_project: If True, prefer project-level configs.

        Returns:
            List of WriteResults.
        """
        results = []
        for config in tool_configs:
            if not config.installed or not config.supports_mcp:
                continue

            use_global = not prefer_project or not config.use_project_level
            result = self.write_config(config, use_global=use_global)
            results.append(result)

        return results

    def _is_global_path(self, path: Path) -> bool:
        """Check if path is in user's home directory (global config)."""
        try:
            path.relative_to(Path.home())
            # Check if it's directly in home config dirs
            parts = path.parts
            home_parts = Path.home().parts
            if len(parts) > len(home_parts):
                first_subdir = parts[len(home_parts)]
                return first_subdir.startswith(".")
            return False
        except ValueError:
            return False

    def _build_entry(self, tool_config: ToolConfig) -> dict[str, Any]:
        """Build the MCP entry for a tool."""
        if tool_config.tool_type == ToolType.CONTINUE:
            # Continue uses a different structure
            return {
                "contextmd": {
                    "transport": {
                        "type": "stdio",
                        "command": "contextmd",
                        "args": ["serve"],
                    }
                }
            }
        return {"contextmd": self.MCP_ENTRY.copy()}

    def _write_mcp_entry(self, path: Path, tool_config: ToolConfig) -> WriteResult:
        """Write or merge MCP entry into config file."""
        entry = self._build_entry(tool_config)

        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)

        # Read existing config
        existing: dict[str, Any] = {}
        was_merged = False

        if path.exists():
            try:
                existing = json.loads(path.read_text())
                was_merged = True
            except (json.JSONDecodeError, OSError):
                existing = {}

        # Merge the entry
        config_key = tool_config.config_key

        if tool_config.tool_type == ToolType.CONTINUE:
            # Continue uses nested key
            keys = config_key.split(".")
            current = existing
            for key in keys[:-1]:
                current = current.setdefault(key, {})
            current.setdefault(keys[-1], {}).update(entry)
        else:
            # Standard MCP structure
            existing.setdefault(config_key, {}).update(entry)

        # Write the config
        try:
            path.write_text(json.dumps(existing, indent=2) + "\n")
            return WriteResult(
                success=True,
                path=path,
                message=f"{'Updated' if was_merged else 'Created'} {path}",
                was_merged=was_merged,
            )
        except OSError as e:
            return WriteResult(
                success=False,
                path=path,
                message=f"Failed to write {path}: {e}",
            )

    def generate_fallback_script(self, output_path: Path) -> WriteResult:
        """
        Generate a fallback shell script for tools without MCP support.

        This script prepends MEMORY.md content to a prompt file.
        """
        script_content = '''#!/bin/bash
# context-inject.sh - Fallback for tools without MCP support
# Prepends contextmd memory to your prompt

MEMORY_FILE=".contextmd/MEMORY.md"
OUTPUT_FILE="${1:-prompt.txt}"

if [ -f "$MEMORY_FILE" ]; then
    echo "# Project Memory" > "$OUTPUT_FILE.tmp"
    echo "" >> "$OUTPUT_FILE.tmp"
    cat "$MEMORY_FILE" >> "$OUTPUT_FILE.tmp"
    echo "" >> "$OUTPUT_FILE.tmp"
    echo "---" >> "$OUTPUT_FILE.tmp"
    echo "" >> "$OUTPUT_FILE.tmp"
    
    if [ -f "$OUTPUT_FILE" ]; then
        cat "$OUTPUT_FILE" >> "$OUTPUT_FILE.tmp"
    fi
    
    mv "$OUTPUT_FILE.tmp" "$OUTPUT_FILE"
    echo "Injected memory into $OUTPUT_FILE"
else
    echo "No memory file found at $MEMORY_FILE"
    exit 1
fi
'''

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(script_content)
            output_path.chmod(0o755)
            return WriteResult(
                success=True,
                path=output_path,
                message=f"Created fallback script at {output_path}",
            )
        except OSError as e:
            return WriteResult(
                success=False,
                path=output_path,
                message=f"Failed to create fallback script: {e}",
            )
