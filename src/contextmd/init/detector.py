"""Tool detection for AI coding assistants."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class ToolType(Enum):
    """Supported AI coding tools."""

    CLAUDE_CODE = "claude_code"
    CURSOR = "cursor"
    WINDSURF = "windsurf"
    CLINE = "cline"
    CONTINUE = "continue"


@dataclass
class ToolConfig:
    """Configuration for a detected tool."""

    tool_type: ToolType
    name: str
    installed: bool = False
    global_config_path: Optional[Path] = None
    project_config_path: Optional[Path] = None
    config_key: str = "mcpServers"
    supports_mcp: bool = True
    use_project_level: bool = True


@dataclass
class DetectionResult:
    """Result of tool detection."""

    tools: list[ToolConfig] = field(default_factory=list)
    project_dir: Path = field(default_factory=Path.cwd)

    @property
    def detected_tools(self) -> list[ToolConfig]:
        """Return only installed tools."""
        return [t for t in self.tools if t.installed]

    @property
    def mcp_capable_tools(self) -> list[ToolConfig]:
        """Return tools that support MCP."""
        return [t for t in self.detected_tools if t.supports_mcp]


class ToolDetector:
    """Detects installed AI coding tools and their config paths."""

    def __init__(self, project_dir: Optional[Path] = None) -> None:
        self.project_dir = project_dir or Path.cwd()
        self.home_dir = Path.home()

    def detect_all(self) -> DetectionResult:
        """Detect all supported tools."""
        result = DetectionResult(project_dir=self.project_dir)

        result.tools = [
            self._detect_claude_code(),
            self._detect_cursor(),
            self._detect_windsurf(),
            self._detect_cline(),
            self._detect_continue(),
        ]

        return result

    def _detect_claude_code(self) -> ToolConfig:
        """Detect Claude Code installation."""
        config = ToolConfig(
            tool_type=ToolType.CLAUDE_CODE,
            name="Claude Code",
            global_config_path=self.home_dir / ".claude" / "claude_desktop_config.json",
            project_config_path=self.project_dir / ".mcp.json",
        )

        # Check for global Claude directory
        if (self.home_dir / ".claude").exists():
            config.installed = True

        # Also consider installed if project has .mcp.json
        if config.project_config_path.exists():
            config.installed = True

        return config

    def _detect_cursor(self) -> ToolConfig:
        """Detect Cursor installation."""
        config = ToolConfig(
            tool_type=ToolType.CURSOR,
            name="Cursor",
            global_config_path=self.home_dir / ".cursor" / "mcp.json",
            project_config_path=self.project_dir / ".cursor" / "mcp.json",
        )

        # Check for global Cursor directory
        if (self.home_dir / ".cursor").exists():
            config.installed = True

        # Check for project-level .cursor directory
        if (self.project_dir / ".cursor").exists():
            config.installed = True
            config.use_project_level = True

        return config

    def _detect_windsurf(self) -> ToolConfig:
        """Detect Windsurf installation."""
        config = ToolConfig(
            tool_type=ToolType.WINDSURF,
            name="Windsurf",
            global_config_path=self.home_dir / ".windsurf" / "mcp.json",
            project_config_path=self.project_dir / ".windsurf" / "mcp.json",
        )

        # Check for global Windsurf directory
        if (self.home_dir / ".windsurf").exists():
            config.installed = True

        # Check for project-level .windsurf directory
        if (self.project_dir / ".windsurf").exists():
            config.installed = True
            config.use_project_level = True

        return config

    def _detect_cline(self) -> ToolConfig:
        """Detect Cline installation."""
        config = ToolConfig(
            tool_type=ToolType.CLINE,
            name="Cline",
            global_config_path=self.home_dir / ".cline" / "mcp_settings.json",
            project_config_path=self.project_dir / ".cline" / "mcp_settings.json",
        )

        # Check for global Cline directory
        if (self.home_dir / ".cline").exists():
            config.installed = True

        return config

    def _detect_continue(self) -> ToolConfig:
        """Detect Continue installation."""
        config = ToolConfig(
            tool_type=ToolType.CONTINUE,
            name="Continue",
            global_config_path=self.home_dir / ".continue" / "config.json",
            project_config_path=self.project_dir / ".continue" / "config.json",
            config_key="experimental.modelContextProtocolServers",
        )

        # Check for global Continue directory
        if (self.home_dir / ".continue").exists():
            config.installed = True

        return config
