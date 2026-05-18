#!/usr/bin/env python3
"""Digest generator for OpenCode sessions.

Takes parsed session data and generates human-readable markdown summaries.
Includes: session duration, tools used, files modified, errors encountered,
subagent completions.
Saves to data/sessions/digests/{date}-{session-id}.md
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from parser import SessionLogParser

DIGEST_DIR = Path(__file__).parent.parent.parent / "data" / "sessions" / "digests"


class DigestGenerator:
    """Generates markdown digests from parsed session data."""

    def __init__(self, digest_dir=None):
        self.digest_dir = Path(digest_dir) if digest_dir else DIGEST_DIR
        self.digest_dir.mkdir(parents=True, exist_ok=True)

    def generate_from_parsed(self, parsed_data):
        """Generate digests from already-parsed session data."""
        digests = []
        sessions = parsed_data.get("sessions", {})

        for session_id, session in sessions.items():
            digest = self._generate_digest(session_id, session)
            filepath = self._save_digest(session_id, digest)
            digests.append({
                "session_id": session_id,
                "filepath": str(filepath),
                "content": digest,
            })

        return digests

    def generate_from_logs(self, log_dir=None, session_id=None):
        """Parse logs and generate digests in one step."""
        parser = SessionLogParser(log_dir=log_dir)

        if log_dir and Path(log_dir).is_file():
            parsed = parser.parse_file(log_dir)
        else:
            parsed = parser.parse_all()

        if session_id:
            if session_id in parsed.get("sessions", {}):
                parsed["sessions"] = {session_id: parsed["sessions"][session_id]}
            else:
                return [{"error": f"Session '{session_id}' not found"}]

        return self.generate_from_parsed(parsed)

    def generate_latest(self, log_dir=None):
        """Generate digest for the most recent session."""
        parser = SessionLogParser(log_dir=log_dir)
        parsed = parser.parse_all()
        sessions = parsed.get("sessions", {})

        if not sessions:
            return {"error": "No sessions found"}

        latest_id = max(sessions.keys(), key=lambda sid: sessions[sid].get("end_time") or "")
        latest = sessions[latest_id]

        digest = self._generate_digest(latest_id, latest)
        filepath = self._save_digest(latest_id, digest)

        return {
            "session_id": latest_id,
            "filepath": str(filepath),
            "content": digest,
        }

    def _generate_digest(self, session_id, session):
        """Generate markdown digest for a single session."""
        lines = []

        lines.append(f"# Session Digest: `{session_id}`")
        lines.append("")

        lines.append(self._format_header(session))
        lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append(self._format_summary(session))
        lines.append("")

        lines.append("## Tools Used")
        lines.append("")
        lines.append(self._format_tools(session))
        lines.append("")

        lines.append("## Files Modified")
        lines.append("")
        lines.append(self._format_files(session))
        lines.append("")

        lines.append("## Errors Encountered")
        lines.append("")
        lines.append(self._format_errors(session))
        lines.append("")

        lines.append("## Subagent Tasks")
        lines.append("")
        lines.append(self._format_subagents(session))
        lines.append("")

        lines.append("## Key Decisions")
        lines.append("")
        lines.append(self._format_decisions(session))
        lines.append("")

        lines.append("## Recent Prompts")
        lines.append("")
        lines.append(self._format_prompts(session))
        lines.append("")

        lines.append("---")
        lines.append(f"*Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}*")

        return "\n".join(lines)

    def _format_header(self, session):
        """Format session header with timing info."""
        start = session.get("start_time", "N/A")
        end = session.get("end_time", "N/A")
        duration = session.get("duration_seconds")

        duration_str = self._format_duration(duration) if duration else "Unknown"

        lines = [
            "| Field | Value |",
            "|-------|-------|",
            f"| **Session ID** | `{session.get('session_id', 'N/A')}` |",
            f"| **Start** | {start} |",
            f"| **End** | {end} |",
            f"| **Duration** | {duration_str} |",
        ]
        return "\n".join(lines)

    def _format_summary(self, session):
        """Format summary statistics."""
        summary = session.get("summary", {})
        lines = [
            f"- **Total Events**: {summary.get('total_events', 0)}",
            f"- **User Prompts**: {summary.get('user_prompts_count', 0)}",
            f"- **Tool Calls**: {summary.get('tool_calls_count', 0)}",
            f"- **Files Modified**: {summary.get('files_modified_count', 0)}",
            f"- **Errors**: {summary.get('errors_count', 0)}",
            f"- **Subagent Tasks**: {summary.get('subagent_tasks_count', 0)}",
        ]
        return "\n".join(lines)

    def _format_tools(self, session):
        """Format tools used section."""
        tools = session.get("tools_used", [])
        if not tools:
            return "_No tool calls recorded._"

        tool_counts = {}
        for tc in session.get("tool_calls", []):
            tool = tc.get("tool", "unknown")
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        lines = []
        for tool in tools:
            count = tool_counts.get(tool, 0)
            lines.append(f"- `{tool}` ({count} calls)")
        return "\n".join(lines)

    def _format_files(self, session):
        """Format files modified section."""
        files = session.get("files_modified", [])
        if not files:
            return "_No files modified._"

        file_ops = {}
        for fc in session.get("file_changes", []):
            path = fc.get("path", "unknown")
            op = fc.get("operation", "unknown")
            if path not in file_ops:
                file_ops[path] = set()
            file_ops[path].add(op)

        lines = []
        for f in files:
            ops = ", ".join(sorted(file_ops.get(f, ["modified"])))
            lines.append(f"- `{f}` ({ops})")
        return "\n".join(lines)

    def _format_errors(self, session):
        """Format errors section."""
        errors = session.get("errors", [])
        if not errors:
            return "_No errors encountered._"

        lines = []
        for i, err in enumerate(errors, 1):
            msg = err.get("message", "Unknown error")
            ts = err.get("timestamp", "")
            lines.append(f"{i}. **{msg}**")
            if ts:
                lines.append(f"   - Time: {ts}")
            stack = err.get("stack_trace")
            if stack:
                lines.append(f"   - Stack: `{stack}`")
        return "\n".join(lines)

    def _format_subagents(self, session):
        """Format subagent tasks section."""
        tasks = session.get("subagent_tasks", [])
        if not tasks:
            return "_No subagent tasks._"

        lines = []
        for task in tasks:
            agent = task.get("agent", "unknown")
            status = task.get("status", "unknown")
            task_preview = task.get("task_preview", "")
            ts = task.get("timestamp", "")

            status_icon = {
                "completed": "[DONE]",
                "success": "[DONE]",
                "error": "[FAIL]",
                "failed": "[FAIL]",
                "spawned": "[RUN]",
                "running": "[RUN]",
            }.get(status.lower(), "[?]")

            lines.append(f"- {status_icon} **{agent}**: {status}")
            if task_preview:
                lines.append(f"  - Task: {task_preview}")
            if ts:
                lines.append(f"  - Time: {ts}")
        return "\n".join(lines)

    def _format_decisions(self, session):
        """Format key decisions section."""
        decisions = session.get("decisions", [])
        if not decisions:
            return "_No key decisions detected._"

        lines = []
        for i, dec in enumerate(decisions, 1):
            text = dec.get("decision", "")
            ts = dec.get("timestamp", "")
            lines.append(f"{i}. {text}")
            if ts:
                lines.append(f"   - Time: {ts}")
        return "\n".join(lines)

    def _format_prompts(self, session):
        """Format recent prompts section."""
        prompts = session.get("recent_prompts", [])
        if not prompts:
            return "_No prompts recorded._"

        lines = []
        for i, prompt in enumerate(prompts, 1):
            content = prompt.get("content", "")
            ts = prompt.get("timestamp", "")
            lines.append(f"{i}. > {content}")
            if ts:
                lines.append(f"   - Time: {ts}")
        return "\n".join(lines)

    def _save_digest(self, session_id, content):
        """Save digest to file."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        safe_session_id = session_id.replace("/", "_").replace("\\", "_")
        filename = f"{date_str}-{safe_session_id}.md"
        filepath = self.digest_dir / filename

        filepath.parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return filepath

    def _format_duration(self, seconds):
        """Format duration in seconds to human-readable string."""
        if seconds is None:
            return "Unknown"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if secs > 0 or not parts:
            parts.append(f"{secs}s")

        return " ".join(parts)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate session digests")
    parser.add_argument("--log-dir", help="Log directory or single log file")
    parser.add_argument("--session", help="Generate digest for specific session ID")
    parser.add_argument("--latest", action="store_true", help="Generate digest for latest session only")
    parser.add_argument("--output-dir", help="Custom output directory for digests")
    parser.add_argument("--stdout", action="store_true", help="Print digest to stdout instead of saving")

    args = parser.parse_args()

    generator = DigestGenerator(digest_dir=args.output_dir)

    if args.latest:
        result = generator.generate_latest(log_dir=args.log_dir)
    elif args.session:
        result = generator.generate_from_logs(log_dir=args.log_dir, session_id=args.session)
    else:
        result = generator.generate_from_logs(log_dir=args.log_dir)

    if args.stdout:
        if isinstance(result, list):
            for digest in result:
                if "content" in digest:
                    print(digest["content"])
                    print("\n---\n")
                elif "error" in digest:
                    print(f"Error: {digest['error']}", file=sys.stderr)
        elif isinstance(result, dict):
            if "content" in result:
                print(result["content"])
            elif "error" in result:
                print(f"Error: {result['error']}", file=sys.stderr)
    else:
        if isinstance(result, list):
            for digest in result:
                if "filepath" in digest:
                    print(f"Digest saved: {digest['filepath']}", file=sys.stderr)
                elif "error" in digest:
                    print(f"Error: {digest['error']}", file=sys.stderr)
        elif isinstance(result, dict):
            if "filepath" in result:
                print(f"Digest saved: {result['filepath']}", file=sys.stderr)
            elif "error" in result:
                print(f"Error: {result['error']}", file=sys.stderr)


if __name__ == "__main__":
    main()
