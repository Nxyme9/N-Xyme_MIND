#!/usr/bin/env python3
"""CLI tool for distributed trace visualization."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def find_traces_dir() -> Path:
    """Find the traces directory."""
    candidates = [
        Path(__file__).parent.parent / "traces",
        Path.cwd() / "traces",
        Path.home() / ".n-xyme-mind" / "traces",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def list_traces(traces_dir: Path, limit: int = 10) -> None:
    """List available trace files."""
    trace_files = sorted(traces_dir.glob("traces_*.json"), reverse=True)

    if not trace_files:
        print("No trace files found.")
        return

    print(f"Found {len(trace_files)} trace file(s):\n")

    for i, trace_file in enumerate(trace_files[:limit]):
        data = json.loads(trace_file.read_text())
        trace_count = data.get("trace_count", 0)
        exported_at = data.get("exported_at", "unknown")

        print(f"  [{i + 1}] {trace_file.name}")
        print(f"      Exported: {exported_at}")
        print(f"      Traces:   {trace_count}")
        print()

    if len(trace_files) > limit:
        print(f"  ... and {len(trace_files) - limit} more files\n")


def show_trace(traces_dir: Path, trace_id: str) -> None:
    """Show a specific trace by ID."""
    trace_files = sorted(traces_dir.glob("traces_*.json"), reverse=True)

    for trace_file in trace_files:
        data = json.loads(trace_file.read_text())
        for trace in data.get("traces", []):
            if trace.get("trace_id") == trace_id:
                print(f"Trace: {trace.get('name', 'unnamed')}")
                print(f"  Trace ID:    {trace.get('trace_id')}")
                print(f"  Spans:       {trace.get('span_count', 0)}")
                print(f"  Duration:    {trace.get('duration_ms', 0):.2f}ms")
                print()

                _print_span_tree(trace.get("spans", []), trace.get("root_span_id"))
                return

    print(f"Trace {trace_id} not found.")


def _print_span_tree(
    spans: list[dict], root_span_id: str | None, indent: int = 0
) -> None:
    """Print spans as a tree structure."""
    children_map: dict[str, list[dict]] = {}
    for span in spans:
        parent = span.get("parent_span_id")
        if parent:
            children_map.setdefault(parent, []).append(span)

    root_spans = [s for s in spans if s.get("span_id") == root_span_id]
    if not root_spans:
        root_spans = [s for s in spans if s.get("parent_span_id") is None]

    for root in root_spans:
        _print_span_node(root, children_map, indent)


def _print_span_node(span: dict, children_map: dict, indent: int) -> None:
    """Print a single span node and its children."""
    prefix = "  " * indent
    status = span.get("status", "unknown")
    duration = span.get("duration_ms")
    duration_str = f"{duration:.2f}ms" if duration is not None else "active"

    status_icon = {"ok": "✓", "error": "✗", "cancelled": "○"}.get(status, "?")

    print(f"{prefix}{status_icon} {span.get('name', 'unnamed')} [{duration_str}]")

    attrs = span.get("attributes", {})
    if attrs:
        for key, value in attrs.items():
            print(f"{prefix}    {key}: {value}")

    events = span.get("events", [])
    if events:
        for event in events:
            print(f"{prefix}    ⚡ {event.get('name')}")

    children = children_map.get(span.get("span_id"), [])
    for child in children:
        _print_span_node(child, children_map, indent + 1)


def show_stats(traces_dir: Path) -> None:
    """Show aggregate statistics across all traces."""
    trace_files = sorted(traces_dir.glob("traces_*.json"), reverse=True)

    total_traces = 0
    total_spans = 0
    total_duration = 0.0
    status_counts: dict[str, int] = {}

    for trace_file in trace_files:
        data = json.loads(trace_file.read_text())
        for trace in data.get("traces", []):
            total_traces += 1
            total_spans += trace.get("span_count", 0)
            duration = trace.get("duration_ms") or 0
            total_duration += duration

            for span in trace.get("spans", []):
                status = span.get("status", "unknown")
                status_counts[status] = status_counts.get(status, 0) + 1

    print("Trace Statistics")
    print("=" * 40)
    print(f"  Total traces:     {total_traces}")
    print(f"  Total spans:      {total_spans}")
    print(f"  Total duration:   {total_duration:.2f}ms")
    if total_traces > 0:
        print(f"  Avg trace duration: {total_duration / total_traces:.2f}ms")
    print()

    if status_counts:
        print("  Span Status Breakdown:")
        for status, count in sorted(status_counts.items()):
            print(f"    {status}: {count}")


def export_latest(traces_dir: Path) -> None:
    """Export the latest trace file as JSON to stdout."""
    trace_files = sorted(traces_dir.glob("traces_*.json"), reverse=True)

    if not trace_files:
        print("No trace files found.", file=sys.stderr)
        sys.exit(1)

    data = json.loads(trace_files[0].read_text())
    print(json.dumps(data, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Distributed trace visualization CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s list                  List all trace files
  %(prog)s show <trace-id>       Show a specific trace
  %(prog)s stats                 Show aggregate statistics
  %(prog)s export                Export latest trace to stdout
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    subparsers.add_parser("list", help="List available trace files")

    show_parser = subparsers.add_parser("show", help="Show a specific trace")
    show_parser.add_argument("trace_id", help="Trace ID to show")

    subparsers.add_parser("stats", help="Show aggregate statistics")
    subparsers.add_parser("export", help="Export latest trace to stdout")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    traces_dir = find_traces_dir()

    if args.command == "list":
        list_traces(traces_dir)
    elif args.command == "show":
        show_trace(traces_dir, args.trace_id)
    elif args.command == "stats":
        show_stats(traces_dir)
    elif args.command == "export":
        export_latest(traces_dir)


if __name__ == "__main__":
    main()
