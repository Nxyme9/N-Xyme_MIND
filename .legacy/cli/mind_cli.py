#!/usr/bin/env python3
"""N-Xyme MIND CLI — Custom frontend with full memory integration.

Usage:
    python3 -m src.cli.mind_cli [command] [args]

Commands:
    chat        Start interactive chat with memory context
    search      Search memory system
    index       Index drives into memory
    status      Show system status
    learn       Show learning stats
    skills      Show skill registry
"""

import argparse
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def cmd_chat(args):
    """Interactive chat with memory context."""
    from src.memory import search_memories, recall_session

    print("=" * 60)
    print("🧠 N-Xyme MIND — Interactive Chat")
    print("=" * 60)
    print()

    # Load recent context
    session = recall_session()
    if session.get("content"):
        print(f"📋 Loaded {len(session['content'])} chars of session context")
        print()

    print("Type your message (or 'quit' to exit):")
    print()

    while True:
        try:
            user_input = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Goodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("👋 Goodbye!")
            break

        # Search memory for context
        result = search_memories(user_input, limit=3)
        if result.get("total_found", 0) > 0:
            print(f"\n🔍 Found {result['total_found']} relevant memories:")
            for i, r in enumerate(result.get("results", [])[:3], 1):
                content = r.get("content", "")[:200].replace("\n", " ")
                print(f"  {i}. [{r.get('source', 'unknown')}] {content}...")
            print()

        # Here you would send to LLM and get response
        print(f"💬 Your query: '{user_input}'")
        print(f"   (LLM integration would go here)")
        print()


def cmd_search(args):
    """Search memory system."""
    from src.memory import search_memories

    query = " ".join(args.query)
    result = search_memories(query, limit=args.limit)

    print(f"🔍 Search: '{query}'")
    print(f"   Found: {result.get('total_found', 0)} results")
    print(f"   Time: {result.get('query_time_ms', 0):.1f}ms")
    print()

    for i, r in enumerate(result.get("results", []), 1):
        source = r.get("source", "unknown")
        content = r.get("content", "")[:300].replace("\n", " ")
        score = r.get("score", 0)
        print(f"  {i}. [{source}] (score: {score:.3f})")
        print(f"     {content}")
        print()


def cmd_index(args):
    """Index drives into memory."""
    from src.memory.indexer import main as indexer_main

    # Build args for indexer
    sys.argv = ["indexer"]
    if args.drive:
        sys.argv.extend(["--drive", args.drive])
    if args.limit:
        sys.argv.extend(["--limit", str(args.limit)])
    if args.dry_run:
        sys.argv.append("--dry-run")

    indexer_main()


def cmd_status(args):
    """Show system status."""
    from src.memory import get_memory_stats, get_indexed_count, get_learning_stats

    print("=" * 60)
    print("🧠 N-Xyme MIND — System Status")
    print("=" * 60)
    print()

    # Memory stats
    stats = get_memory_stats()
    print("📊 Memory Sources:")
    for s in stats.get("sources", []):
        status = "✅" if s["status"] == "healthy" else "⚠️"
        print(f"  {status} {s['name']}: {s['status']}")

    print()

    # Drive index stats
    try:
        index_stats = get_indexed_count()
        print("📁 Drive Index:")
        print(f"  Files: {index_stats['total_files']}")
        print(f"  Chunks: {index_stats['total_chunks']}")
        print(f"  By drive: {index_stats['by_drive']}")
        print(f"  By type: {index_stats['by_type']}")
    except Exception as e:
        print(f"  ⚠️  Drive index error: {e}")

    print()

    # Learning stats
    try:
        learning = get_learning_stats()
        print("🎓 Learning System:")
        fb = learning.get("feedback_stats", {})
        print(f"  Feedback events: {fb.get('total_feedback', 0)}")
        print(f"  Unique queries: {fb.get('unique_queries', 0)}")
    except Exception as e:
        print(f"  ⚠️  Learning stats error: {e}")

    print()
    print("=" * 60)


def cmd_learn(args):
    """Show learning stats."""
    from src.memory import get_learning_stats, get_skill_status

    print("=" * 60)
    print("🎓 Learning System Stats")
    print("=" * 60)
    print()

    # Learning stats
    learning = get_learning_stats()
    fb = learning.get("feedback_stats", {})
    print(f"Feedback events: {fb.get('total_feedback', 0)}")
    print(f"Unique queries: {fb.get('unique_queries', 0)}")
    if fb.get("top_queries"):
        print(f"Top queries: {fb['top_queries'][:5]}")

    print()

    # Skill status
    skills = get_skill_status()
    if skills.get("skills"):
        print("Skills:")
        for s in skills["skills"]:
            m = s.get("metrics", {})
            print(
                f"  - {s['name']}: {s['state']} ({m.get('success_rate', 0):.0%} success, {m.get('invocation_count', 0)} calls)"
            )

    print()
    print("=" * 60)


def cmd_skills(args):
    """Show skill registry."""
    from src.memory import get_skill_status

    skills = get_skill_status()
    if skills.get("skills"):
        print("Registered Skills:")
        for s in skills["skills"]:
            m = s.get("metrics", {})
            print(f"  - {s['name']}: {s['state']}")
            print(
                f"    Success: {m.get('success_rate', 0):.0%}, Calls: {m.get('invocation_count', 0)}, Avg latency: {m.get('avg_latency_ms', 0):.0f}ms"
            )
    else:
        print("No skills registered yet.")
def cmd_save(args):
    """Save content to memory (CLI write-back)."""
    from src.memory import create_memory
    content = " ".join(args.content)
    tags = args.tags or []
    result = create_memory(content, kind=args.kind, scope="global", tags=tags)
    if result.get("status") == "ok":
        print(f"✅ Memory saved: {result.get('memory_id', 'unknown')}")
    else:
        print(f"❌ Failed to save: {result.get('error', 'unknown error')}")


def main():
    parser = argparse.ArgumentParser(description="N-Xyme MIND CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # chat
    chat_parser = subparsers.add_parser("chat", help="Interactive chat with memory")
    chat_parser.set_defaults(func=cmd_chat)

    # search
    search_parser = subparsers.add_parser("search", help="Search memory system")
    search_parser.add_argument("query", nargs="+", help="Search query")
    search_parser.add_argument("--limit", type=int, default=10, help="Max results")
    search_parser.set_defaults(func=cmd_search)

    # index
    index_parser = subparsers.add_parser("index", help="Index drives into memory")
    index_parser.add_argument("--drive", type=str, help="Single drive to scan")
    index_parser.add_argument("--limit", type=int, help="Max files to process")
    index_parser.add_argument(
        "--dry-run", action="store_true", help="Scan without indexing"
    )
    index_parser.set_defaults(func=cmd_index)

    # status
    status_parser = subparsers.add_parser("status", help="Show system status")
    status_parser.set_defaults(func=cmd_status)

    # learn
    learn_parser = subparsers.add_parser("learn", help="Show learning stats")
    learn_parser.set_defaults(func=cmd_learn)

    # skills
    skills_parser = subparsers.add_parser("skills", help="Show skill registry")
    skills_parser.set_defaults(func=cmd_skills)

    # save (write-back)
    save_parser = subparsers.add_parser("save", help="Save content to memory")
    save_parser.add_argument("content", nargs="+", help="Content to save")
    save_parser.add_argument("--kind", default="note", help="Memory type")
    save_parser.add_argument("--tags", nargs="*", help="Tags")
    save_parser.set_defaults(func=cmd_save)
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    args.func(args)


if __name__ == "__main__":
    main()
