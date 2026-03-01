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


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize ContextMD in the current directory."""
    memory_dir = Path(args.memory_dir)

    if memory_dir.exists():
        print(f"Memory directory already exists at {memory_dir}")
        return

    config = ContextMDConfig(memory_dir=memory_dir)
    config.ensure_directories()

    print(f"Initialized ContextMD at {memory_dir}")
    print("\nCreated:")
    print(f"  - {memory_dir}/MEMORY.md")
    print(f"  - {memory_dir}/config.md")
    print(f"  - {memory_dir}/memory/")
    print(f"  - {memory_dir}/sessions/")


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

    subparsers.add_parser("init", help="Initialize ContextMD in current directory")

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
