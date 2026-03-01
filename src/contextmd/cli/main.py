"""CLI commands for ContextMD."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from contextmd.config import ContextMDConfig
from contextmd.storage.markdown import MarkdownStorage
from contextmd.storage.memory import MemoryStore


def get_memory_dir() -> Path:
    """Get the memory directory from args or default."""
    return Path(".contextmd")


def cmd_show(args: argparse.Namespace) -> None:
    """Show current memory contents."""
    memory_dir = Path(args.memory_dir)
    config = ContextMDConfig(memory_dir=memory_dir)
    store = MemoryStore(config)

    print("\n" + "=" * 60)
    print("CONTEXTMD MEMORY")
    print("=" * 60)

    semantic = store.load_semantic_memory()
    if semantic.strip():
        print("\n" + semantic)
    else:
        print("\n(No memory stored yet)")

    print("\n" + "=" * 60)


def cmd_history(args: argparse.Namespace) -> None:
    """Show recent episodic memory (daily logs)."""
    memory_dir = Path(args.memory_dir)
    config = ContextMDConfig(memory_dir=memory_dir)
    store = MemoryStore(config)

    hours = args.hours or config.bootstrap_window_hours

    print("\n" + "=" * 60)
    print(f"RECENT ACTIVITY (last {hours} hours)")
    print("=" * 60)

    episodic = store.load_episodic_memory(hours)
    if episodic.strip():
        print("\n" + episodic)
    else:
        print("\n(No recent activity)")

    print("\n" + "=" * 60)


def cmd_sessions(args: argparse.Namespace) -> None:
    """List saved session snapshots."""
    memory_dir = Path(args.memory_dir)
    sessions_dir = memory_dir / "sessions"
    storage = MarkdownStorage()

    print("\n" + "=" * 60)
    print("SAVED SESSIONS")
    print("=" * 60)

    session_files = storage.list_files(sessions_dir, "*.md")

    if not session_files:
        print("\n(No sessions saved yet)")
    else:
        for f in session_files:
            print(f"\n- {f.stem}")

    print("\n" + "=" * 60)


def cmd_reset(args: argparse.Namespace) -> None:
    """Reset memory (with confirmation)."""
    memory_dir = Path(args.memory_dir)

    if not args.force:
        confirm = input(f"This will delete all memory in {memory_dir}. Continue? [y/N] ")
        if confirm.lower() != "y":
            print("Aborted.")
            return

    import shutil

    if memory_dir.exists():
        shutil.rmtree(memory_dir)
        print(f"Deleted {memory_dir}")

    config = ContextMDConfig(memory_dir=memory_dir)
    config.ensure_directories()
    print(f"Recreated empty memory structure at {memory_dir}")


def _confirm_global_write(tool_name: str, path: Path, config_entry: dict) -> bool:
    """Prompt user to confirm writing to global config."""
    import json

    print(f"\n⚠️  {tool_name} requires writing to global config:")
    print(f"   Path: {path}")
    print(f"   Entry: {json.dumps(config_entry, indent=2)}")
    response = input("   Proceed? [y/N] ").strip().lower()
    return response == "y"


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize ContextMD in the current directory with full tool integration."""
    from contextmd.init import MCPConfigWriter, TemplateGenerator, ToolDetector

    memory_dir = Path(args.memory_dir)
    project_dir = Path.cwd()

    print("\n" + "=" * 60)
    print("CONTEXTMD INIT")
    print("=" * 60)

    # Step 1: Create folder structure
    print("\n📁 Creating folder structure...")
    template_gen = TemplateGenerator(project_dir)
    folder_results = template_gen.create_folder_structure(memory_dir)

    for result in folder_results:
        if result.success:
            status = "✓" if result.created else "○"
            print(f"   {status} {result.path.name}")
        else:
            print(f"   ✗ {result.message}")

    # Step 2: Create CLAUDE.md
    print("\n📄 Setting up CLAUDE.md...")
    claude_result = template_gen.create_claude_md(append_if_exists=True)
    if claude_result.success:
        if claude_result.created:
            print("   ✓ Created CLAUDE.md")
        elif claude_result.appended:
            print("   ✓ Appended contextmd section to existing CLAUDE.md")
        else:
            print("   ○ CLAUDE.md already configured")
    else:
        print(f"   ✗ {claude_result.message}")

    # Step 3: Update .gitignore
    gitignore_result = template_gen.create_gitignore_entry()
    if gitignore_result.appended:
        print("   ✓ Added .contextmd to .gitignore (commented)")

    # Step 4: Detect tools
    print("\n🔍 Detecting AI coding tools...")
    detector = ToolDetector(project_dir)
    detection = detector.detect_all()

    detected = detection.detected_tools
    if not detected:
        print("   No supported tools detected.")
        print("   Tier 1 mode: Use CLI commands (contextmd show/save) directly.")
    else:
        for tool in detected:
            print(f"   • {tool.name}")

    # Step 5: Write MCP configs
    if detected and not args.skip_mcp:
        print("\n⚙️  Configuring MCP servers...")

        # Use confirmation callback for global configs
        confirm_fn = None if args.yes else _confirm_global_write
        writer = MCPConfigWriter(confirm_callback=confirm_fn)

        mcp_tools = detection.mcp_capable_tools
        results = writer.write_all(mcp_tools, prefer_project=True)

        for result in results:
            if result.success:
                status = "✓" if not result.was_merged else "↻"
                print(f"   {status} {result.path}")
            elif result.skipped:
                print(f"   ○ {result.message}")
            else:
                print(f"   ✗ {result.message}")

    # Step 6: Generate fallback script if requested
    if args.fallback:
        print("\n📜 Generating fallback script...")
        writer = MCPConfigWriter()
        fallback_result = writer.generate_fallback_script(
            project_dir / ".contextmd" / "context-inject.sh"
        )
        if fallback_result.success:
            print(f"   ✓ {fallback_result.path}")
        else:
            print(f"   ✗ {fallback_result.message}")

    # Summary
    print("\n" + "=" * 60)
    print("✅ ContextMD initialized!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Run 'contextmd add \"Your first memory\"' to add context")
    print("  2. Start a coding session - your AI will have persistent memory")
    print("\nTier 1 (CLI):  contextmd show / contextmd save")
    if detected:
        print("Tier 2 (MCP):  Full tool integration configured")
    print()


def cmd_add(args: argparse.Namespace) -> None:
    """Add a memory entry manually."""
    memory_dir = Path(args.memory_dir)
    config = ContextMDConfig(memory_dir=memory_dir)
    config.ensure_directories()

    from contextmd.memory.router import MemoryRouter
    from contextmd.memory.types import MemoryType

    router = MemoryRouter(config)

    memory_type = MemoryType(args.type)
    router.remember(args.content, memory_type)

    print(f"Added {args.type} memory: {args.content}")


def cmd_save(args: argparse.Namespace) -> None:
    """Save current session learnings to memory."""
    from datetime import datetime

    memory_dir = Path(args.memory_dir)
    config = ContextMDConfig(memory_dir=memory_dir)
    config.ensure_directories()

    sessions_dir = memory_dir / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_file = sessions_dir / f"session_{timestamp}.md"

    print("\n" + "=" * 60)
    print("SAVE SESSION")
    print("=" * 60)
    print("\nEnter session notes (what you learned, decisions made, etc.).")
    print("Press Ctrl+D (Unix) or Ctrl+Z (Windows) when done:\n")

    try:
        lines = []
        while True:
            try:
                line = input()
                lines.append(line)
            except EOFError:
                break

        content = "\n".join(lines)

        if not content.strip():
            print("\nNo content provided. Session not saved.")
            return

        session_content = f"""# Session {timestamp}

## Notes

{content}

---
*Saved at {datetime.now().isoformat()}*
"""

        session_file.write_text(session_content)
        print(f"\n✓ Session saved to {session_file}")

    except KeyboardInterrupt:
        print("\n\nSession save cancelled.")


def cmd_stats(args: argparse.Namespace) -> None:
    """Show memory statistics."""
    memory_dir = Path(args.memory_dir)
    config = ContextMDConfig(memory_dir=memory_dir)
    store = MemoryStore(config)
    storage = MarkdownStorage()

    print("\n" + "=" * 60)
    print("MEMORY STATISTICS")
    print("=" * 60)

    memory_lines = store.get_memory_line_count()
    print(f"\nMEMORY.md lines: {memory_lines}/{config.memory_line_cap}")

    semantic_entries = store.get_all_semantic_entries()
    print(f"Semantic entries: {len(semantic_entries)}")

    daily_logs = storage.list_files(memory_dir / "memory", "*.md")
    print(f"Daily log files: {len(daily_logs)}")

    sessions = storage.list_files(memory_dir / "sessions", "*.md")
    print(f"Session snapshots: {len(sessions)}")

    print("\n" + "=" * 60)


def main() -> None:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="contextmd",
        description="ContextMD - Markdown-Based Memory Layer for LLM APIs",
    )
    parser.add_argument(
        "--memory-dir",
        "-d",
        default=".contextmd",
        help="Memory directory (default: .contextmd)",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    init_parser = subparsers.add_parser("init", help="Initialize ContextMD with full tool integration")
    init_parser.add_argument(
        "--skip-mcp",
        action="store_true",
        help="Skip MCP server configuration (Tier 1 only)",
    )
    init_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Auto-confirm all prompts (including global config writes)",
    )
    init_parser.add_argument(
        "--fallback",
        action="store_true",
        help="Generate fallback shell script for tools without MCP support",
    )

    subparsers.add_parser("show", help="Show current memory contents")

    history_parser = subparsers.add_parser("history", help="Show recent activity")
    history_parser.add_argument(
        "--hours",
        "-n",
        type=int,
        help="Number of hours to show (default: from config)",
    )

    subparsers.add_parser("sessions", help="List saved session snapshots")

    subparsers.add_parser("stats", help="Show memory statistics")

    add_parser = subparsers.add_parser("add", help="Add a memory entry manually")
    add_parser.add_argument("content", help="Content to remember")
    add_parser.add_argument(
        "--type",
        "-t",
        choices=["semantic", "episodic", "procedural"],
        default="semantic",
        help="Memory type (default: semantic)",
    )

    # 'remember' is an alias for 'add' (more intuitive for users)
    remember_parser = subparsers.add_parser("remember", help="Add a memory (alias for 'add')")
    remember_parser.add_argument("content", help="Content to remember")
    remember_parser.add_argument(
        "--type",
        "-t",
        choices=["semantic", "episodic", "procedural"],
        default="semantic",
        help="Memory type (default: semantic)",
    )

    subparsers.add_parser("save", help="Save current session learnings to memory")

    reset_parser = subparsers.add_parser("reset", help="Reset all memory")
    reset_parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "init": cmd_init,
        "show": cmd_show,
        "history": cmd_history,
        "sessions": cmd_sessions,
        "stats": cmd_stats,
        "add": cmd_add,
        "remember": cmd_add,  # Alias
        "save": cmd_save,
        "reset": cmd_reset,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        cmd_func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
