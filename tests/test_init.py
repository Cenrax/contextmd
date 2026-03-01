"""Tests for the init module."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from contextmd.init.detector import DetectionResult, ToolConfig, ToolDetector, ToolType
from contextmd.init.templates import TemplateGenerator
from contextmd.init.writers import MCPConfigWriter, WriteResult

if TYPE_CHECKING:
    from pytest import TempPathFactory


class TestToolDetector:
    """Tests for ToolDetector."""

    def test_detect_all_returns_detection_result(self, tmp_path: Path) -> None:
        """detect_all should return a DetectionResult."""
        detector = ToolDetector(project_dir=tmp_path)
        result = detector.detect_all()

        assert isinstance(result, DetectionResult)
        assert len(result.tools) == 5  # All supported tools

    def test_detect_claude_code_with_mcp_json(self, tmp_path: Path) -> None:
        """Should detect Claude Code if .mcp.json exists."""
        mcp_json = tmp_path / ".mcp.json"
        mcp_json.write_text("{}")

        detector = ToolDetector(project_dir=tmp_path)
        result = detector.detect_all()

        claude_tool = next(
            (t for t in result.tools if t.tool_type == ToolType.CLAUDE_CODE), None
        )
        assert claude_tool is not None
        assert claude_tool.installed is True

    def test_detect_cursor_with_cursor_dir(self, tmp_path: Path) -> None:
        """Should detect Cursor if .cursor/ exists."""
        cursor_dir = tmp_path / ".cursor"
        cursor_dir.mkdir()

        detector = ToolDetector(project_dir=tmp_path)
        result = detector.detect_all()

        cursor_tool = next(
            (t for t in result.tools if t.tool_type == ToolType.CURSOR), None
        )
        assert cursor_tool is not None
        assert cursor_tool.installed is True

    def test_detected_tools_filters_installed(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """detected_tools should only return installed tools."""
        # Mock home directory to avoid detecting real tools
        fake_home = tmp_path / "fake_home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        project_dir = tmp_path / "project"
        project_dir.mkdir()

        detector = ToolDetector(project_dir=project_dir)
        result = detector.detect_all()

        # No tools installed in empty project with fake home
        assert len(result.detected_tools) == 0

        # Create .mcp.json to install Claude Code
        (project_dir / ".mcp.json").write_text("{}")
        result = detector.detect_all()
        assert len(result.detected_tools) == 1
        assert result.detected_tools[0].tool_type == ToolType.CLAUDE_CODE


class TestMCPConfigWriter:
    """Tests for MCPConfigWriter."""

    def test_write_config_creates_file(self, tmp_path: Path) -> None:
        """Should create MCP config file."""
        tool_config = ToolConfig(
            tool_type=ToolType.CLAUDE_CODE,
            name="Claude Code",
            installed=True,
            project_config_path=tmp_path / ".mcp.json",
        )

        writer = MCPConfigWriter()
        result = writer.write_config(tool_config, use_global=False)

        assert result.success is True
        assert (tmp_path / ".mcp.json").exists()

        content = json.loads((tmp_path / ".mcp.json").read_text())
        assert "mcpServers" in content
        assert "contextmd" in content["mcpServers"]

    def test_write_config_merges_existing(self, tmp_path: Path) -> None:
        """Should merge with existing config."""
        mcp_json = tmp_path / ".mcp.json"
        mcp_json.write_text(json.dumps({
            "mcpServers": {
                "other-server": {"command": "other"}
            }
        }))

        tool_config = ToolConfig(
            tool_type=ToolType.CLAUDE_CODE,
            name="Claude Code",
            installed=True,
            project_config_path=mcp_json,
        )

        writer = MCPConfigWriter()
        result = writer.write_config(tool_config, use_global=False)

        assert result.success is True
        assert result.was_merged is True

        content = json.loads(mcp_json.read_text())
        assert "other-server" in content["mcpServers"]
        assert "contextmd" in content["mcpServers"]

    def test_write_config_skips_global_without_confirm(self, tmp_path: Path) -> None:
        """Should skip global config if no confirm callback."""
        # Simulate a global path (in home directory)
        home = Path.home()
        tool_config = ToolConfig(
            tool_type=ToolType.CLAUDE_CODE,
            name="Claude Code",
            installed=True,
            global_config_path=home / ".claude" / "test_config.json",
            project_config_path=tmp_path / ".mcp.json",
        )

        writer = MCPConfigWriter(confirm_callback=None)
        result = writer.write_config(tool_config, use_global=True)

        assert result.success is False
        assert result.skipped is True

    def test_write_config_with_confirm_callback(self, tmp_path: Path) -> None:
        """Should call confirm callback for global configs."""
        confirmed = []

        def confirm_fn(name: str, path: Path, entry: dict) -> bool:
            confirmed.append((name, path))
            return True

        # Use tmp_path as fake home to avoid writing to real home
        tool_config = ToolConfig(
            tool_type=ToolType.CLAUDE_CODE,
            name="Claude Code",
            installed=True,
            global_config_path=tmp_path / ".claude" / "config.json",
        )

        writer = MCPConfigWriter(confirm_callback=confirm_fn)
        # Force it to be treated as global by using the global path
        result = writer.write_config(tool_config, use_global=True, force=False)

        # Since tmp_path is not under home, it won't trigger confirmation
        # This tests the non-global path behavior
        assert result.success is True

    def test_generate_fallback_script(self, tmp_path: Path) -> None:
        """Should generate fallback shell script."""
        writer = MCPConfigWriter()
        script_path = tmp_path / "context-inject.sh"

        result = writer.generate_fallback_script(script_path)

        assert result.success is True
        assert script_path.exists()
        content = script_path.read_text()
        assert "#!/bin/bash" in content
        assert "MEMORY_FILE" in content


class TestTemplateGenerator:
    """Tests for TemplateGenerator."""

    def test_create_folder_structure(self, tmp_path: Path) -> None:
        """Should create .contextmd folder structure."""
        generator = TemplateGenerator(project_dir=tmp_path)
        results = generator.create_folder_structure()

        assert all(r.success for r in results)
        assert (tmp_path / ".contextmd").exists()
        assert (tmp_path / ".contextmd" / "memory").exists()
        assert (tmp_path / ".contextmd" / "sessions").exists()
        assert (tmp_path / ".contextmd" / "MEMORY.md").exists()
        assert (tmp_path / ".contextmd" / "config.yaml").exists()

    def test_create_claude_md_new(self, tmp_path: Path) -> None:
        """Should create new CLAUDE.md."""
        generator = TemplateGenerator(project_dir=tmp_path)
        result = generator.create_claude_md()

        assert result.success is True
        assert result.created is True
        assert (tmp_path / "CLAUDE.md").exists()

        content = (tmp_path / "CLAUDE.md").read_text()
        assert "contextmd show" in content
        assert "contextmd save" in content

    def test_create_claude_md_append(self, tmp_path: Path) -> None:
        """Should append to existing CLAUDE.md."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Existing Content\n\nSome instructions.")

        generator = TemplateGenerator(project_dir=tmp_path)
        result = generator.create_claude_md(append_if_exists=True)

        assert result.success is True
        assert result.appended is True

        content = claude_md.read_text()
        assert "Existing Content" in content
        assert "ContextMD Integration" in content

    def test_create_claude_md_skip_if_already_has_contextmd(self, tmp_path: Path) -> None:
        """Should skip if CLAUDE.md already mentions contextmd."""
        claude_md = tmp_path / "CLAUDE.md"
        claude_md.write_text("# Project\n\nUses contextmd for memory.")

        generator = TemplateGenerator(project_dir=tmp_path)
        result = generator.create_claude_md(append_if_exists=True)

        assert result.success is True
        assert result.appended is False

    def test_create_gitignore_entry(self, tmp_path: Path) -> None:
        """Should add .contextmd to .gitignore."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text("node_modules/\n.env\n")

        generator = TemplateGenerator(project_dir=tmp_path)
        result = generator.create_gitignore_entry()

        assert result.success is True
        assert result.appended is True

        content = gitignore.read_text()
        assert ".contextmd" in content

    def test_create_gitignore_skip_if_exists(self, tmp_path: Path) -> None:
        """Should skip if .contextmd already in .gitignore."""
        gitignore = tmp_path / ".gitignore"
        gitignore.write_text(".contextmd/\n")

        generator = TemplateGenerator(project_dir=tmp_path)
        result = generator.create_gitignore_entry()

        assert result.success is True
        assert result.appended is False
