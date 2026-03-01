"""Init module for ContextMD - handles tool detection and MCP configuration."""

from contextmd.init.detector import ToolDetector
from contextmd.init.templates import TemplateGenerator
from contextmd.init.writers import MCPConfigWriter

__all__ = ["ToolDetector", "MCPConfigWriter", "TemplateGenerator"]
