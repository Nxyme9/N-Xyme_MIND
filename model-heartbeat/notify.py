#!/usr/bin/env python3
"""
Model Heartbeat — Notifier
Formats a diff result into a human-readable notification message
and delivers it via Telegram (if configured) or stdout.

Usage:
    python notify.py diff.json                     # read diff from file
    python notify.py --stdin                       # read diff JSON from stdin
    python notify.py --telegram                    # force Telegram send
    python notify.py --stdout                      # force stdout (default)
"""

import json
import os
import sys
import argparse
from typing import Any
from urllib.request import Request, urlopen
from urllib.error import URLError


# ── Formatting ──────────────────────────────────────────────────────────────

def format_message(diff: dict) -> str:
    """Build a human-readable notification message from a diff dict."""
    stats = diff.get("stats", {})
    added = stats.get("added_count", 0)
    removed = stats.get("removed_count", 0)
    changed = stats.get("changed_count", 0)
    expiring = stats.get("expiring_soon_count", 0)

    total_changes = added + removed + changed + expiring
    if total_changes == 0:
        period = _fmt_period(diff)
        return (
            f"✅ Model Heartbeat — No Changes\n"
            f"   Period: {period}\n"
            f"   All models stable across all providers."
        )

    period = _fmt_period(diff)
    lines = [f"🔔 Model Heartbeat — Changes Detected\n   Period: {period}\n"]

    # Summary bar
    parts = []
    if added:
        parts.append(f"➕ +{added}")
    if removed:
        parts.append(f"➖ -{removed}")
    if changed:
        parts.append(f"🔄 ~{changed}")
    if expiring:
        parts.append(f"⏳ !{expiring}")
    lines.append(f"   {'  |  '.join(parts)}\n")

    # New models
    if added:
        lines.append(f"── New Models ({added}) ──")
        for m in diff.get("added", [])[:15]:
            lines.append(f"  ➕ {m['model_id']}  [{m['provider']}]")
        if added > 15:
            lines.append(f"  ... and {added - 15} more")
        lines.append("")

    # Removed models
    if removed:
        lines.append(f"── Removed Models ({removed}) ──")
        for m in diff.get("removed", [])[:15]:
            lines.append(f"  ➖ {m['model_id']}  [{m['provider']}]")
        if removed > 15:
            lines.append(f"  ... and {removed - 15} more")
        lines.append("")

    # Changed models
    if changed:
        lines.append(f"── Changed Models ({changed}) ──")
        for c in diff.get("changed", [])[:15]:
            descs = []
            for field, vals in c.get("changes", {}).items():
                label = _field_label(field)
                old = _brief(vals.get("old"))
                new = _brief(vals.get("new"))
                descs.append(f"{label}: {old} → {new}")
            lines.append(f"  🔄 {c['model_id']}  [{', '.join(descs)}]")
        if changed > 15:
            lines.append(f"  ... and {changed - 15} more")
        lines.append("")

    # Expiring models
    if expiring:
        lines.append(f"── Expiring Models ({expiring}) ──")
        for m in diff.get("expiring_soon", [])[:15]:
            exp = m.get("expiration_date", "unknown")[:10]
            lines.append(f"  ⏳ {m['model_id']}  expires {exp}")
        if expiring > 15:
            lines.append(f"  ... and {expiring - 15} more")
        lines.append("")

    return "\n".join(lines).strip()


def format_html_message(diff: dict) -> str:
    """Build an HTML version suitable for Telegram parse_mode=HTML."""
    stats = diff.get("stats", {})
    added = stats.get("added_count", 0)
    removed = stats.get("removed_count", 0)
    changed = stats.get("changed_count", 0)
    expiring = stats.get("expiring_soon_count", 0)

    total_changes = added + removed + changed + expiring
    period = _fmt_period(diff)

    if total_changes == 0:
        return (
            f"<b>✅ Model Heartbeat — No Changes</b>\n"
            f"Period: {period}\n"
            f"All models stable across all providers."
        )

    lines = [
        f"<b>🔔 Model Heartbeat — Changes Detected</b>",
        f"Period: {period}",
        "",
    ]

    # Summary bar
    parts = []
    if added:
        parts.append(f"➕ +{added}")
    if removed:
        parts.append(f"➖ -{removed}")
    if changed:
        parts.append(f"🔄 ~{changed}")
    if expiring:
        parts.append(f"⏳ !{expiring}")
    lines.append(f"{'  |  '.join(parts)}")
    lines.append("")

    # Helper to truncate model_id for display
    def _short_id(mid: str, max_len: int = 45) -> str:
        return mid if len(mid) <= max_len else mid[: max_len - 3] + "..."

    if added:
        lines.append(f"<b>New Models ({added})</b>")
        for m in diff.get("added", [])[:15]:
            lines.append(f"  ➕ <code>{_short_id(m['model_id'])}</code>  [{m['provider']}]")
        if added > 15:
            lines.append(f"  ... and {added - 15} more")
        lines.append("")

    if removed:
        lines.append(f"<b>Removed Models ({removed})</b>")
        for m in diff.get("removed", [])[:15]:
            lines.append(f"  ➖ <code>{_short_id(m['model_id'])}</code>  [{m['provider']}]")
        if removed > 15:
            lines.append(f"  ... and {removed - 15} more")
        lines.append("")

    if changed:
        lines.append(f"<b>Changed Models ({changed})</b>")
        for c in diff.get("changed", [])[:15]:
            descs = []
            for field, vals in c.get("changes", {}).items():
                label = _field_label(field)
                old = _brief(vals.get("old"))
                new = _brief(vals.get("new"))
                descs.append(f"{label}: {old} → {new}")
            lines.append(f"  🔄 <code>{_short_id(c['model_id'])}</code>  [{', '.join(descs)}]")
        if changed > 15:
            lines.append(f"  ... and {changed - 15} more")
        lines.append("")

    if expiring:
        lines.append(f"<b>Expiring Models ({expiring})</b>")
        for m in diff.get("expiring_soon", [])[:15]:
            exp = m.get("expiration_date", "unknown")[:10]
            lines.append(f"  ⏳ <code>{_short_id(m['model_id'])}</code>  expires {exp}")
        if expiring > 15:
            lines.append(f"  ... and {expiring - 15} more")
        lines.append("")

    return "<br>".join(lines)


# ── Delivery ────────────────────────────────────────────────────────────────

def send_telegram(message: str, parse_mode: str = "HTML") -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("[notify] TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set — skipping Telegram", file=sys.stderr)
        return False

    # Split message if longer than Telegram's 4096 char limit
    max_len = 4096
    chunks = [message[i : i + max_len] for i in range(0, len(message), max_len)]

    for i, chunk in enumerate(chunks):
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True,
        }).encode()

        req = Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read().decode())
                if not result.get("ok"):
                    print(f"[notify] Telegram API error: {result}", file=sys.stderr)
                    return False
        except URLError as e:
            print(f"[notify] Telegram connection error: {e}", file=sys.stderr)
            return False
        except Exception as e:
            print(f"[notify] Unexpected Telegram error: {e}", file=sys.stderr)
            return False

    print(f"[notify] Telegram message sent ({len(chunks)} chunk(s))", file=sys.stderr)
    return True


def print_stdout(message: str) -> None:
    """Print the message to stdout with a clear header."""
    print(message)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _fmt_period(diff: dict) -> str:
    t_prev = diff.get("timestamp_prev", "?")[:19]
    t_curr = diff.get("timestamp_curr", "?")[:19]
    return f"{t_prev} → {t_curr}"


FIELD_LABELS = {
    "expiration_date": "Expiration",
    "is_free": "Free tier",
    "pricing": "Pricing",
}


def _field_label(field: str) -> str:
    return FIELD_LABELS.get(field, field.replace("_", " ").title())


def _brief(val: Any, max_len: int = 40) -> str:
    if val is None:
        return "—"
    s = json.dumps(val, default=str)
    return s[:max_len] + "…" if len(s) > max_len else s


# ── CLI ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Format and deliver model heartbeat diff notifications")
    parser.add_argument("diff_file", nargs="?", help="Path to diff JSON file")
    parser.add_argument("--stdin", action="store_true", help="Read diff JSON from stdin")
    parser.add_argument("--stdout", action="store_true", help="Print notification to stdout (default)")
    parser.add_argument("--telegram", action="store_true", help="Send notification via Telegram")
    parser.add_argument("--html", action="store_true", help="Output HTML format (for Telegram)")
    args = parser.parse_args()

    # Read diff JSON
    diff: dict = {}
    if args.stdin or (not args.diff_file and not sys.stdin.isatty()):
        try:
            diff = json.load(sys.stdin)
        except json.JSONDecodeError as e:
            print(f"[notify] Error reading diff from stdin: {e}", file=sys.stderr)
            return 1
    elif args.diff_file:
        try:
            with open(args.diff_file) as f:
                diff = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"[notify] Error reading diff file: {e}", file=sys.stderr)
            return 1
    else:
        parser.print_help()
        return 1

    # Decide output mode
    use_telegram = args.telegram or os.environ.get("TELEGRAM_BOT_TOKEN") is not None
    use_html = args.html or use_telegram
    force_stdout = args.stdout

    if use_telegram and not force_stdout:
        msg = format_html_message(diff) if use_html else format_message(diff)
        sent = send_telegram(msg, parse_mode="HTML" if use_html else "")
        if not sent:
            # Fallback to stdout if Telegram fails
            print("[notify] Falling back to stdout", file=sys.stderr)
            print_stdout(format_message(diff))
        return 0
    else:
        if use_html:
            print_stdout(format_html_message(diff))
        else:
            print_stdout(format_message(diff))
        return 0


if __name__ == "__main__":
    sys.exit(main())
