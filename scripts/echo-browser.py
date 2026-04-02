#!/usr/bin/env python3
"""
Echo Browser Automation - Safe browser control with guardrails
Uses agent-browser for Playwright-based automation.
"""

import json
import re
import subprocess
import time
from typing import Optional, Dict, List
from pathlib import Path

# ─── NEVER-DO LIST (Hard Block) ─────────────────────────────────────────────
NEVER_DO_URLS = [
    r"bank",
    r"banking",
    r"paypal",
    r"stripe",
    r"venmo",
    r"email\.google\.com",
    r"mail\.yahoo\.com",
    r"outlook\.com",
    r"facebook\.com.*messages",
    r"twitter\.com.*compose",
    r"instagram\.com.*direct",
    r"linkedin\.com.*messaging",
    r"amazon\.com.*checkout",
    r"ebay\.com.*checkout",
    r"admin",
    r"root",
    r"sudo",
    r"file:///",
    r"chrome://",
    r"about:",
]

# ─── SAFE URLS (Always Allowed) ─────────────────────────────────────────────
SAFE_URLS = [
    r"github",
    r"stackoverflow",
    r"google",
    r"youtube",
    r"wikipedia",
    r"reddit",
    r"docs\.",
    r"api\.",
    r"npmjs",
    r"pypi",
    r"huggingface",
    r"arxiv",
    r"duckduckgo",
    r"bing",
]

# ─── REQUIRE CONFIRMATION ───────────────────────────────────────────────────
CONFIRM_ACTIONS = [
    r"\bclick\b",
    r"\bfill\b",
    r"\btype\b",
    r"\bsubmit\b",
    r"\bdownload\b",
    r"\bupload\b",
    r"\blogin\b",
    r"\bsignin\b",
    r"\bpurchase\b",
    r"\bbuy\b",
    r"\border\b",
]


class BrowserGuard:
    def __init__(self):
        self.open_windows = []
        self.action_log = []

    def is_never_do_url(self, url: str) -> bool:
        """Check if URL is on NEVER-DO list."""
        url_lower = url.lower()
        return any(re.search(p, url_lower) for p in NEVER_DO_URLS)

    def is_safe_url(self, url: str) -> bool:
        """Check if URL is on safe list."""
        url_lower = url.lower()
        return any(re.search(p, url_lower) for p in SAFE_URLS)

    def requires_confirm(self, action: str) -> bool:
        """Check if action requires confirmation."""
        action_lower = action.lower()
        return any(re.search(p, action_lower) for p in CONFIRM_ACTIONS)

    def validate_url(self, url: str) -> dict:
        """Validate URL for safety."""
        if self.is_never_do_url(url):
            return {
                "allowed": False,
                "reason": f"URL '{url}' is on NEVER-DO list (banking, email, social media).",
                "safety": "blocked",
            }

        if not url.startswith(("http://", "https://")):
            url = f"https://{url}"

        if self.is_safe_url(url):
            return {
                "allowed": True,
                "url": url,
                "safety": "safe",
                "needs_confirm": False,
            }

        return {
            "allowed": True,
            "url": url,
            "safety": "unknown",
            "needs_confirm": True,
            "reason": f"URL '{url}' is not on safe list. Say 'confirm' to proceed.",
        }

    def log_action(self, action: str, result: str):
        """Log every browser action."""
        entry = {
            "timestamp": time.time(),
            "action": action,
            "result": result,
        }
        self.action_log.append(entry)
        print(f"[BROWSER LOG] {action} → {result}")


class EchoBrowser:
    def __init__(self):
        self.guard = BrowserGuard()
        self.browser = None
        self.page = None

    def _ensure_browser(self):
        """Lazy load browser."""
        if self.browser is None:
            try:
                from agent_browser import AgentBrowser

                self.browser = AgentBrowser()
                print("Browser loaded!")
            except ImportError:
                print(
                    "agent-browser not installed. Install with: pip install agent-browser"
                )
                return False
        return True

    def open_url(self, url: str) -> dict:
        """Open URL with safety checks."""
        validation = self.guard.validate_url(url)

        if not validation["allowed"]:
            self.guard.log_action(f"open {url}", f"BLOCKED: {validation['reason']}")
            return validation

        if validation.get("needs_confirm"):
            self.guard.log_action(f"open {url}", "REQUIRES CONFIRMATION")
            return {
                "action": "confirm_needed",
                "message": f"This will open {url}. Say 'confirm' or 'cancel'.",
                "url": validation["url"],
            }

        # Safe to open
        if not self._ensure_browser():
            return {"action": "error", "message": "Browser not available"}

        try:
            self.browser.navigate(validation["url"])
            self.guard.log_action(f"open {url}", "SUCCESS")
            return {
                "action": "opened",
                "url": validation["url"],
                "message": f"Opened {url}",
            }
        except Exception as e:
            self.guard.log_action(f"open {url}", f"ERROR: {e}")
            return {"action": "error", "message": str(e)}

    def screenshot(self) -> dict:
        """Take screenshot (always safe)."""
        if not self._ensure_browser():
            return {"action": "error", "message": "Browser not available"}

        try:
            path = self.browser.screenshot()
            self.guard.log_action("screenshot", f"SUCCESS: {path}")
            return {
                "action": "screenshot",
                "path": path,
                "message": f"Screenshot saved to {path}",
            }
        except Exception as e:
            self.guard.log_action("screenshot", f"ERROR: {e}")
            return {"action": "error", "message": str(e)}

    def get_text(self) -> dict:
        """Get page text (always safe)."""
        if not self._ensure_browser():
            return {"action": "error", "message": "Browser not available"}

        try:
            text = self.browser.get_text()
            self.guard.log_action("get_text", f"SUCCESS: {len(text)} chars")
            return {
                "action": "text",
                "text": text[:500],  # Limit to 500 chars
                "message": f"Page has {len(text)} characters",
            }
        except Exception as e:
            self.guard.log_action("get_text", f"ERROR: {e}")
            return {"action": "error", "message": str(e)}

    def click(self, selector: str) -> dict:
        """Click element (requires confirmation)."""
        if self.guard.requires_confirm(f"click {selector}"):
            return {
                "action": "confirm_needed",
                "message": f"This will click '{selector}'. Say 'confirm' or 'cancel'.",
                "selector": selector,
            }

        if not self._ensure_browser():
            return {"action": "error", "message": "Browser not available"}

        try:
            self.browser.click(selector)
            self.guard.log_action(f"click {selector}", "SUCCESS")
            return {
                "action": "clicked",
                "selector": selector,
                "message": f"Clicked {selector}",
            }
        except Exception as e:
            self.guard.log_action(f"click {selector}", f"ERROR: {e}")
            return {"action": "error", "message": str(e)}

    def fill(self, selector: str, value: str) -> dict:
        """Fill form field (requires confirmation)."""
        if self.guard.requires_confirm(f"fill {selector}"):
            return {
                "action": "confirm_needed",
                "message": f"This will fill '{selector}' with '{value}'. Say 'confirm' or 'cancel'.",
                "selector": selector,
                "value": value,
            }

        if not self._ensure_browser():
            return {"action": "error", "message": "Browser not available"}

        try:
            self.browser.fill(selector, value)
            self.guard.log_action(f"fill {selector}", "SUCCESS")
            return {
                "action": "filled",
                "selector": selector,
                "value": value,
                "message": f"Filled {selector} with {value}",
            }
        except Exception as e:
            self.guard.log_action(f"fill {selector}", f"ERROR: {e}")
            return {"action": "error", "message": str(e)}

    def search(self, query: str) -> dict:
        """Search Google (safe)."""
        url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
        return self.open_url(url)

    def close(self) -> dict:
        """Close browser (safe)."""
        if self.browser:
            try:
                self.browser.close()
                self.guard.log_action("close", "SUCCESS")
                return {"action": "closed", "message": "Browser closed"}
            except Exception as e:
                self.guard.log_action("close", f"ERROR: {e}")
                return {"action": "error", "message": str(e)}
        return {"action": "closed", "message": "Browser was not open"}

    def get_action_log(self) -> List[dict]:
        """Get all browser actions."""
        return self.guard.action_log


# ─── COMMAND PARSER ──────────────────────────────────────────────────────────
def parse_browser_command(text: str) -> Optional[dict]:
    """Parse voice command for browser actions."""
    patterns = [
        (r"open (.+)", "open"),
        (r"go to (.+)", "open"),
        (r"navigate to (.+)", "open"),
        (r"take (?:a )?screenshot", "screenshot"),
        (r"what(?:'s| is) on (?:the )?(?:page|screen)", "get_text"),
        (r"read (?:the )?(?:page|website)", "get_text"),
        (r"click (?:on )?(.+)", "click"),
        (r"fill (?:in )?(.+) with (.+)", "fill"),
        (r"search for (.+)", "search"),
        (r"close (?:the )?browser", "close"),
    ]

    for pattern, action in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            return {"action": action, "args": groups, "raw": text}

    return None


# ─── TEST ────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    browser = EchoBrowser()

    test_commands = [
        "Open GitHub",
        "Go to stackoverflow.com",
        "Open my bank account",
        "Take a screenshot",
        "What's on the page",
        "Search for Python tutorials",
        "Click on the login button",
        "Close the browser",
    ]

    print("=" * 50)
    print("  ECHO BROWSER TEST")
    print("=" * 50)

    for cmd in test_commands:
        print(f"\nCommand: {cmd}")
        parsed = parse_browser_command(cmd)
        if parsed:
            print(f"  Action: {parsed['action']}")
            print(f"  Args: {parsed['args']}")

            # Test safety
            if parsed["action"] == "open":
                url = parsed["args"][0]
                validation = browser.guard.validate_url(url)
                print(f"  Safety: {validation.get('safety', 'unknown')}")
                if not validation.get("allowed", True):
                    print(f"  BLOCKED: {validation.get('reason')}")
                elif validation.get("needs_confirm"):
                    print(f"  CONFIRM: {validation.get('reason')}")
        else:
            print("  No browser action detected")
