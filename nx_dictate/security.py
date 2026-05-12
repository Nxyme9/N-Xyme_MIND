# N-Xyme Dictate - Security Review Module
# Red team security checks for the dictation system

from __future__ import annotations

import logging
import os
import re
import subprocess
from dataclasses import dataclass
from typing import List, Optional, Callable

logger = logging.getLogger("nxyme_dictate.security")


@dataclass
class SecurityIssue:
    """Security issue found during review."""

    severity: str  # critical, high, medium, low, info
    category: str  # input_validation, injection, privacy, etc.
    title: str
    description: str
    file: str
    line: int = 0
    fix_suggestion: str = ""


class SecurityReviewer:
    """Red team security review for N-Xyme Dictate."""

    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._issues: List[SecurityIssue] = []

    def run_full_review(self) -> List[SecurityIssue]:
        """Run full security review."""
        logger.info("Starting security review...")

        self._issues = []

        # Run all checks
        self._check_audio_input_validation()
        self._check_command_injection()
        self._check_path_traversal()
        self._check_secrets_exposure()
        self._check_clipboard_access()
        self._check_keyboard_input()
        self._check_process_injection()
        self._check_config_permissions()

        # Log results
        self._log_results()

        return self._issues

    def _add_issue(self, issue: SecurityIssue):
        """Add security issue."""
        self._issues.append(issue)

    def _check_audio_input_validation(self):
        """Check audio input validation."""
        audio_file = os.path.join(self.base_path, "core", "audio.py")

        if not os.path.exists(audio_file):
            return

        with open(audio_file, "r") as f:
            content = f.read()

        # Check for proper audio validation
        if "max_recording_seconds" not in content:
            self._add_issue(
                SecurityIssue(
                    severity="medium",
                    category="input_validation",
                    title="Missing audio duration limit",
                    description="Audio recording should have a maximum duration to prevent DoS",
                    file=audio_file,
                    fix_suggestion="Add max_recording_seconds to AudioConfig",
                )
            )

        # Check for chunk size limits
        if "chunk_seconds" not in content:
            self._add_issue(
                SecurityIssue(
                    severity="low",
                    category="input_validation",
                    title="Missing chunk size limit",
                    description="Audio chunk size should be configurable and limited",
                    file=audio_file,
                )
            )

    def _check_command_injection(self):
        """Check for command injection vulnerabilities."""
        injection_file = os.path.join(self.base_path, "injection.py")

        if not os.path.exists(injection_file):
            return

        with open(injection_file, "r") as f:
            content = f.read()

        # Check subprocess usage with shell=True
        if re.search(
            r"subprocess\.(run|Popen|call|check_output)\s*\([^)]*shell\s*=\s*True", content
        ):
            self._add_issue(
                SecurityIssue(
                    severity="high",
                    category="injection",
                    title="Shell=True subprocess usage",
                    description="Using shell=True in subprocess can allow command injection",
                    file=injection_file,
                    fix_suggestion="Use shell=False and pass arguments as list",
                )
            )

        # Check for proper argument passing
        if "xdotool" in content and "shell=True" not in content:
            # xdotool should use proper escaping
            if "xdotool" in content and "key" in content:
                logger.info("xdotool usage found - ensure proper escaping")

    def _check_path_traversal(self):
        """Check for path traversal vulnerabilities."""
        # Check for file operations with user-controlled paths
        for filename in ["audio.py", "injection.py"]:
            filepath = (
                os.path.join(self.base_path, "core", filename)
                if "core" in filename
                else os.path.join(self.base_path, filename)
            )
            if not os.path.exists(filepath):
                continue

            with open(filepath, "r") as f:
                content = f.read()

            # Check for open() with user input
            if re.search(r"open\s*\([^)]*\)", content):
                # Verify there's proper path sanitization
                if "os.path.normpath" not in content and "Path(" not in content:
                    self._add_issue(
                        SecurityIssue(
                            severity="medium",
                            category="path_traversal",
                            title="Potential path traversal",
                            description="File operations should validate and sanitize paths",
                            file=filepath,
                            fix_suggestion="Use os.path.normpath or pathlib.Path for path validation",
                        )
                    )

    def _check_secrets_exposure(self):
        """Check for secrets exposure in code."""
        # Check config files for hardcoded secrets
        config_files = ["config.py", "settings.py", "engine.py"]

        for config_file in config_files:
            filepath = os.path.join(self.base_path, config_file)
            if not os.path.exists(filepath):
                continue

            with open(filepath, "r") as f:
                content = f.read()

            # Check for API keys, passwords, tokens
            patterns = [
                (r'api[_-]?key\s*=\s*["\'].+["\']', "API key found in code"),
                (r'password\s*=\s*["\'].+["\']', "Password found in code"),
                (r'token\s*=\s*["\'].+["\']', "Token found in code"),
                (r'secret\s*=\s*["\'].+["\']', "Secret found in code"),
            ]

            for pattern, desc in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    # Make sure it's not an example/placeholder
                    if "example" not in content.lower() and "placeholder" not in content.lower():
                        self._add_issue(
                            SecurityIssue(
                                severity="critical",
                                category="secrets",
                                title=f"Potential secret exposure: {desc}",
                                description=f"Found potential {desc}. Use environment variables instead.",
                                file=filepath,
                                fix_suggestion="Use os.environ.get() or .env files for secrets",
                            )
                        )

    def _check_clipboard_access(self):
        """Check clipboard access security."""
        injection_file = os.path.join(self.base_path, "injection.py")

        if not os.path.exists(injection_file):
            return

        with open(injection_file, "r") as f:
            content = f.read()

        # Check if clipboard access is properly sandboxed
        if "pyperclip" in content or "QClipboard" in content:
            self._add_issue(
                SecurityIssue(
                    severity="info",
                    category="privacy",
                    title="Clipboard access",
                    description="Application accesses system clipboard - ensure clipboard clearing after use",
                    file=injection_file,
                    fix_suggestion="Consider clearing clipboard after pasting sensitive data",
                )
            )

    def _check_keyboard_input(self):
        """Check keyboard input security."""
        hotkey_file = os.path.join(self.base_path, "core", "hotkey.py")

        if not os.path.exists(hotkey_file):
            return

        with open(hotkey_file, "r") as f:
            content = f.read()

        # Check for pynput keyboard controller usage
        if "Controller" in content and "keyboard" in content:
            self._add_issue(
                SecurityIssue(
                    severity="medium",
                    category="input_validation",
                    title="Keyboard input simulation",
                    description="Application can simulate keyboard input - ensure proper access controls",
                    file=hotkey_file,
                    fix_suggestion="Document required permissions and potential abuse vectors",
                )
            )

    def _check_process_injection(self):
        """Check for process injection vulnerabilities."""
        injection_file = os.path.join(self.base_path, "injection.py")

        if not os.path.exists(injection_file):
            return

        with open(injection_file, "r") as f:
            content = f.read()

        # Check for proper process spawning
        if "subprocess" in content:
            # Ensure environment is sanitized
            if "env=" not in content and "environ" in content.lower():
                self._add_issue(
                    SecurityIssue(
                        severity="low",
                        category="process",
                        title="Process environment handling",
                        description="Ensure subprocess environment is controlled and not inherited from untrusted sources",
                        file=injection_file,
                        fix_suggestion="Explicitly set environment variables when spawning processes",
                    )
                )

    def _check_config_permissions(self):
        """Check configuration file permissions."""
        config_dir = os.path.expanduser("~/.config/nxyme-dictate")

        if os.path.exists(config_dir):
            # Check if config is world-readable
            stat_info = os.stat(config_dir)
            mode = stat_info.st_mode

            if mode & 0o077:  # If any group/other permissions
                self._add_issue(
                    SecurityIssue(
                        severity="medium",
                        category="permissions",
                        title="Insecure config directory permissions",
                        description=f"Config directory has overly permissive permissions: {oct(mode)}",
                        file=config_dir,
                        fix_suggestion="Restrict permissions to owner only: chmod 700",
                    )
                )

    def _log_results(self):
        """Log security review results."""
        if not self._issues:
            logger.info("Security review: No issues found")
            return

        # Group by severity
        by_severity = {"critical": [], "high": [], "medium": [], "low": [], "info": []}
        for issue in self._issues:
            by_severity[issue.severity].append(issue)

        for severity in ["critical", "high", "medium", "low", "info"]:
            issues = by_severity[severity]
            if issues:
                logger.warning(f"Security review [{severity.upper()}]: {len(issues)} issue(s)")
                for issue in issues:
                    logger.warning(f"  - {issue.title}: {issue.description}")

    def get_issues_by_severity(self, severity: str) -> List[SecurityIssue]:
        """Get issues by severity."""
        return [i for i in self._issues if i.severity == severity]

    @property
    def has_critical_issues(self) -> bool:
        """Check if there are critical security issues."""
        return any(i.severity == "critical" for i in self._issues)


# Convenience function
def run_security_review(base_path: str = None) -> List[SecurityIssue]:
    """Run security review."""
    reviewer = SecurityReviewer(base_path)
    return reviewer.run_full_review()


if __name__ == "__main__":
    # Run security review
    issues = run_security_review()

    if issues:
        print(f"\nFound {len(issues)} security issues:")
        for issue in issues:
            print(f"  [{issue.severity.upper()}] {issue.title}")
            print(f"    {issue.description}")
            if issue.fix_suggestion:
                print(f"    Fix: {issue.fix_suggestion}")
    else:
        print("No security issues found!")
