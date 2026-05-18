#!/usr/bin/env python3
"""Session log parser for OpenCode.

Reads opencode logs from ~/.local/share/opencode/log/*.log
Extracts: tool calls, file changes, errors, key decisions, subagent tasks
Groups by session ID
Outputs structured JSON

Supports both JSON-L and plain-text log formats.
"""

import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class SessionLogParser:
    """Parses OpenCode log files and extracts structured session data."""

    LOG_DIR = Path.home() / ".local" / "share" / "opencode" / "log"

    TEXT_PATTERNS = {
        "tool_call": re.compile(r'tool(?:\.call|\.execute|\.registry)[\s:]+(\S+)', re.IGNORECASE),
        "file_write": re.compile(r'(?:write|edit|create)\s+(?:file\s+)?(\S+\.\w+)', re.IGNORECASE),
        "error": re.compile(r'(?:error|fail|exception|crash)[\s:]+(.+)', re.IGNORECASE),
        "subagent": re.compile(r'(?:agent|subagent|spawn)[\s:]+(\S+)', re.IGNORECASE),
        "permission": re.compile(r'permission[\s:]+(\S+)', re.IGNORECASE),
        "session_start": re.compile(r'session[\s.:]+start', re.IGNORECASE),
        "session_end": re.compile(r'session[\s.:]+end', re.IGNORECASE),
        "prompt": re.compile(r'(?:prompt|user|question)[\s:]+(.+)', re.IGNORECASE),
    }

    def __init__(self, log_dir=None):
        self.log_dir = Path(log_dir) if log_dir else self.LOG_DIR
        self.sessions = defaultdict(lambda: {
            "session_id": None,
            "start_time": None,
            "end_time": None,
            "user_prompts": [],
            "assistant_responses": [],
            "tool_calls": [],
            "file_changes": [],
            "errors": [],
            "decisions": [],
            "subagent_tasks": [],
            "permissions": [],
            "raw_events": 0,
        })

    def parse_all(self):
        if not self.log_dir.exists():
            return {"error": f"Log directory not found: {self.log_dir}", "sessions": {}}
        log_files = sorted(self.log_dir.glob("*.log"))
        if not log_files:
            return {"error": "No log files found", "sessions": {}}
        for log_file in log_files:
            self._parse_file(log_file)
        return self._build_output()

    def parse_file(self, filepath):
        self._parse_file(Path(filepath))
        return self._build_output()

    def _parse_file(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    self._process_line(line, filepath.stem)
        except (IOError, OSError) as e:
            print(f"Warning: Could not read {filepath}: {e}", file=sys.stderr)

    def _process_line(self, line, filename_hint):
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                self._process_json_event(event)
                return
        except (json.JSONDecodeError, AttributeError):
            pass
        self._process_text_line(line, filename_hint)

    def _process_json_event(self, event):
        event_type = event.get("type", "")
        timestamp = event.get("timestamp", event.get("time", ""))
        session_id = event.get("sessionId", event.get("session_id", event.get("session", "")))
        if not session_id:
            session_id = "unknown"
        session = self.sessions[session_id]
        session["raw_events"] += 1
        if session["session_id"] is None:
            session["session_id"] = session_id
        if timestamp:
            if session["start_time"] is None:
                session["start_time"] = timestamp
            session["end_time"] = timestamp
        if event_type == "session.prompt" or "prompt" in event_type:
            self._extract_prompt(session, event, timestamp)
        elif event_type == "message.part.delta" or "delta" in event_type:
            self._extract_response(session, event, timestamp)
        elif event_type == "tool.registry" or "tool.call" in event_type or "tool.execute" in event_type:
            self._extract_tool_call(session, event, timestamp)
        elif event_type == "permission" or "permission.check" in event_type:
            self._extract_permission(session, event, timestamp)
        elif event_type == "error" or "error" in event_type.lower():
            self._extract_error(session, event, timestamp)
        elif event_type == "agent.spawn" or "subagent" in event_type.lower() or "spawn" in event_type.lower():
            self._extract_subagent_task(session, event, timestamp)
        elif event_type == "session.start":
            session["start_time"] = timestamp
        elif event_type == "session.end":
            session["end_time"] = timestamp
        self._extract_file_changes(session, event, event_type)
        self._extract_decisions(session, event, event_type)

    def _process_text_line(self, line, filename_hint):
        session_id = filename_hint if filename_hint else "unknown"
        session = self.sessions[session_id]
        session["raw_events"] += 1
        if session["session_id"] is None:
            session["session_id"] = session_id
        ts_match = re.search(r'(\d{4}-\d{2}-\d{2}T[\d:]+)', line)
        timestamp = ts_match.group(1) if ts_match else ""
        if timestamp:
            if session["start_time"] is None:
                session["start_time"] = timestamp
            session["end_time"] = timestamp
        if self.TEXT_PATTERNS["session_start"].search(line):
            session["start_time"] = timestamp
        if self.TEXT_PATTERNS["session_end"].search(line):
            session["end_time"] = timestamp
        tool_match = self.TEXT_PATTERNS["tool_call"].search(line)
        if tool_match:
            session["tool_calls"].append({"timestamp": timestamp, "tool": tool_match.group(1), "input_preview": line[:100]})
        file_match = self.TEXT_PATTERNS["file_write"].search(line)
        if file_match:
            session["file_changes"].append({"path": file_match.group(1), "operation": "write", "timestamp": timestamp})
        error_match = self.TEXT_PATTERNS["error"].search(line)
        if error_match:
            session["errors"].append({"timestamp": timestamp, "message": error_match.group(1)[:300], "stack_trace": None})
        subagent_match = self.TEXT_PATTERNS["subagent"].search(line)
        if subagent_match:
            session["subagent_tasks"].append({"timestamp": timestamp, "agent": subagent_match.group(1), "task_preview": None, "status": "spawned"})
        perm_match = self.TEXT_PATTERNS["permission"].search(line)
        if perm_match:
            session["permissions"].append({"timestamp": timestamp, "action": perm_match.group(1), "granted": None})
        prompt_match = self.TEXT_PATTERNS["prompt"].search(line)
        if prompt_match:
            session["user_prompts"].append({"timestamp": timestamp, "content": prompt_match.group(1)[:500]})

    def _extract_prompt(self, session, event, timestamp):
        content = event.get("content", event.get("message", event.get("text", "")))
        if isinstance(content, list):
            content = " ".join(item.get("text", str(item)) for item in content if isinstance(item, dict))
        if content and len(str(content).strip()) > 0:
            session["user_prompts"].append({"timestamp": timestamp, "content": str(content)[:500]})

    def _extract_response(self, session, event, timestamp):
        content = event.get("content", event.get("delta", event.get("text", "")))
        if isinstance(content, list):
            content = " ".join(item.get("text", str(item)) for item in content if isinstance(item, dict))
        if content and len(str(content).strip()) > 0:
            session["assistant_responses"].append({"timestamp": timestamp, "content_preview": str(content)[:200]})

    def _extract_tool_call(self, session, event, timestamp):
        tool_name = event.get("toolName", event.get("tool", event.get("name", "")))
        tool_input = event.get("input", event.get("arguments", event.get("params", {})))
        if tool_name:
            session["tool_calls"].append({"timestamp": timestamp, "tool": str(tool_name), "input_preview": self._truncate_input(tool_input)})

    def _extract_permission(self, session, event, timestamp):
        action = event.get("action", event.get("type", ""))
        granted = event.get("granted", event.get("allowed", event.get("decision", None)))
        if action:
            session["permissions"].append({"timestamp": timestamp, "action": str(action), "granted": granted})

    def _extract_error(self, session, event, timestamp):
        message = event.get("message", event.get("error", event.get("reason", "")))
        stack = event.get("stack", "")
        if message:
            session["errors"].append({"timestamp": timestamp, "message": str(message)[:300], "stack_trace": str(stack)[:200] if stack else None})

    def _extract_subagent_task(self, session, event, timestamp):
        agent_name = event.get("agent", event.get("agentName", event.get("name", "")))
        task = event.get("task", event.get("prompt", event.get("message", "")))
        status = event.get("status", event.get("result", "spawned"))
        if agent_name or task:
            session["subagent_tasks"].append({"timestamp": timestamp, "agent": str(agent_name), "task_preview": str(task)[:300] if task else None, "status": str(status)})

    def _extract_file_changes(self, session, event, event_type):
        file_path = event.get("filePath", event.get("path", event.get("file", "")))
        if not file_path:
            content = event.get("content", event.get("input", {}))
            if isinstance(content, dict):
                file_path = content.get("filePath", content.get("path", ""))
        if file_path and any(kw in event_type.lower() for kw in ["write", "edit", "create", "delete", "bash"]):
            operation = "unknown"
            if "write" in event_type.lower(): operation = "write"
            elif "edit" in event_type.lower(): operation = "edit"
            elif "delete" in event_type.lower(): operation = "delete"
            elif "create" in event_type.lower(): operation = "create"
            elif "bash" in event_type.lower(): operation = "bash_exec"
            session["file_changes"].append({"path": str(file_path), "operation": operation, "timestamp": event.get("timestamp", event.get("time", ""))})

    def _extract_decisions(self, session, event, event_type):
        content = event.get("content", event.get("message", event.get("text", "")))
        if isinstance(content, dict):
            content = json.dumps(content)
        decision_patterns = [
            r"(?:decided|chose|opted|selected)\s+to\s+(.+?)(?:\.|$)",
            r"(?:approach|strategy|method|plan)\s*[:=]\s*(.+?)(?:\.|$)",
            r"(?:using|with)\s+(?:the\s+)?(?:pattern|architecture|design)\s+(.+?)(?:\.|$)",
        ]
        if isinstance(content, str) and len(content) > 20:
            for pattern in decision_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    decision_text = match.group(0).strip()
                    if len(decision_text) < 200:
                        session["decisions"].append({"timestamp": event.get("timestamp", event.get("time", "")), "decision": decision_text})
                        break

    def _truncate_input(self, tool_input, max_len=150):
        if isinstance(tool_input, str):
            return tool_input[:max_len] + ("..." if len(tool_input) > max_len else "")
        elif isinstance(tool_input, dict):
            truncated = {}
            for key, value in list(tool_input.items())[:3]:
                str_val = str(value)
                truncated[key] = str_val[:80] + ("..." if len(str_val) > 80 else "")
            return truncated
        return str(tool_input)[:max_len]

    def _build_output(self):
        output_sessions = {}
        for session_id, session in self.sessions.items():
            tool_names = list(set(tc["tool"] for tc in session["tool_calls"]))
            files_modified = list(set(fc["path"] for fc in session["file_changes"]))
            duration = self._calculate_duration(session["start_time"], session["end_time"])
            output_sessions[session_id] = {
                "session_id": session_id,
                "start_time": session["start_time"],
                "end_time": session["end_time"],
                "duration_seconds": duration,
                "summary": {
                    "total_events": session["raw_events"],
                    "user_prompts_count": len(session["user_prompts"]),
                    "tool_calls_count": len(session["tool_calls"]),
                    "files_modified_count": len(files_modified),
                    "errors_count": len(session["errors"]),
                    "subagent_tasks_count": len(session["subagent_tasks"]),
                },
                "tools_used": sorted(tool_names),
                "files_modified": sorted(files_modified),
                "errors": session["errors"],
                "decisions": session["decisions"],
                "subagent_tasks": session["subagent_tasks"],
                "recent_prompts": session["user_prompts"][-5:],
            }
        return {
            "parsed_at": datetime.utcnow().isoformat() + "Z",
            "log_directory": str(self.log_dir),
            "sessions": output_sessions,
            "total_sessions": len(output_sessions),
        }

    def _calculate_duration(self, start, end):
        if not start or not end:
            return None
        for fmt in ["%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]:
            try:
                start_dt = datetime.strptime(str(start).replace("+00:00", "").rstrip("Z") + "Z" if "T" in str(start) else str(start), fmt)
                end_dt = datetime.strptime(str(end).replace("+00:00", "").rstrip("Z") + "Z" if "T" in str(end) else str(end), fmt)
                return int((end_dt - start_dt).total_seconds())
            except (ValueError, TypeError):
                continue
        return None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Parse OpenCode session logs")
    parser.add_argument("--log-dir", help="Custom log directory")
    parser.add_argument("--file", help="Parse a single log file")
    parser.add_argument("--session", help="Filter by session ID")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()
    log_parser = SessionLogParser(log_dir=args.log_dir)
    if args.file:
        result = log_parser.parse_file(args.file)
    else:
        result = log_parser.parse_all()
    if args.session:
        if args.session in result.get("sessions", {}):
            result["sessions"] = {args.session: result["sessions"][args.session]}
            result["total_sessions"] = 1
        else:
            result["error"] = f"Session '{args.session}' not found"
            result["sessions"] = {}
    indent = 2 if args.pretty else None
    json_output = json.dumps(result, indent=indent, default=str)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output, "w") as f:
            f.write(json_output)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        print(json_output)


if __name__ == "__main__":
    main()
