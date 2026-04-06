"""
Grounding/Verification Layer — Prevents hallucination cascades.

After tool execution, verifies LLM's claimed result against actual output.
Catches cases where the LLM claims success but nothing actually happened.

Verification is lightweight — just checking if claimed outcomes occurred.
Does NOT block on failures; logs and continues with correction context.
"""

import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.request import urlopen
from urllib.error import URLError

import logging

logger = logging.getLogger(__name__)


# ── Data Classes ───────────────────────────────────────────────────────


@dataclass
class VerificationResult:
    """Result of a claim verification attempt."""

    verified: bool
    claim: str
    evidence: str
    confidence: float  # 0.0 to 1.0
    timestamp: float = field(default_factory=time.time)
    correction_hint: str = ""  # Hint for LLM if verification failed


@dataclass
class ClaimPattern:
    """Pattern for matching LLM claims to verification actions."""

    pattern: re.Pattern
    verify_fn: str  # Name of the verification method to call
    extract_fn: Optional[Callable[[re.Match], Dict[str, str]]] = None


# ── Claim Extractors ───────────────────────────────────────────────────


def _extract_process_name(match: re.Match) -> Dict[str, str]:
    """Extract process name from 'opened/started/launched X' claims."""
    return {"process_name": match.group(1).strip()}


def _extract_file_path(match: re.Match) -> Dict[str, str]:
    """Extract file path from 'saved/created/wrote file' claims."""
    return {"path": match.group(1).strip()}


def _extract_url(match: re.Match) -> Dict[str, str]:
    """Extract URL from 'opened/navigated to website' claims."""
    return {"url": match.group(1).strip()}


# ── Grounding Verifier ────────────────────────────────────────────────


class GroundingVerifier:
    """
    Verifies LLM claims against actual system state.

    Prevents hallucination cascades by checking if claimed outcomes
    actually occurred. Lightweight verification — just reality checks.

    Usage:
        verifier = GroundingVerifier()
        result = verifier.verify_claim("I opened Chrome", tool_output)
        if not result.verified:
            # Feed correction back to LLM
    """

    # Patterns that indicate tool-related claims worth verifying
    CLAIM_PATTERNS: List[ClaimPattern] = [
        # Process claims: "I opened/started/launched X"
        ClaimPattern(
            pattern=re.compile(
                r"(?:opened|started|launched|ran|executed)\s+(?:the\s+)?(\w+(?:\.\w+)?)",
                re.IGNORECASE,
            ),
            verify_fn="check_process_exists",
            extract_fn=_extract_process_name,
        ),
        # File claims: "I saved/created/wrote file to X"
        ClaimPattern(
            pattern=re.compile(
                r"(?:saved|created|wrote|generated|downloaded)\s+(?:the\s+)?(?:file\s+)?(?:to\s+)?['\"]?([^\s'\"]+)['\"]?",
                re.IGNORECASE,
            ),
            verify_fn="check_file_exists",
            extract_fn=_extract_file_path,
        ),
        # URL claims: "I opened/navigated to X"
        ClaimPattern(
            pattern=re.compile(
                r"(?:opened|navigated\s+to|loaded|visited)\s+(?:the\s+)?(?:website\s+|page\s+|url\s+)?(https?://\S+)",
                re.IGNORECASE,
            ),
            verify_fn="check_url_accessible",
            extract_fn=_extract_url,
        ),
        # Command success claims: "The command succeeded/returned 0"
        ClaimPattern(
            pattern=re.compile(
                r"(?:command|script|process)\s+(?:succeeded|completed|finished|returned\s+0)",
                re.IGNORECASE,
            ),
            verify_fn="check_command_success",
        ),
    ]

    def __init__(self):
        self._verification_log: List[VerificationResult] = []

    def verify_claim(
        self,
        claim: str,
        actual_output: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        """
        Verify an LLM claim against actual tool output or system state.

        Args:
            claim: The LLM's textual claim about what happened
            actual_output: The actual tool execution result dict (optional)

        Returns:
            VerificationResult with verified status and evidence
        """
        if not claim:
            return VerificationResult(
                verified=True,
                claim="(empty)",
                evidence="No claim to verify",
                confidence=1.0,
            )

        # First check: does the actual tool output indicate success?
        if actual_output is not None:
            tool_success = actual_output.get("success", False)
            if not tool_success:
                result = VerificationResult(
                    verified=False,
                    claim=claim,
                    evidence=f"Tool reported failure: {actual_output.get('error', 'unknown')}",
                    confidence=0.95,
                    correction_hint=(
                        f"The tool execution failed. Don't claim success. "
                        f"Error: {actual_output.get('error', 'unknown')}"
                    ),
                )
                self._log_verification(result)
                return result

        # Second check: pattern-based verification against system state
        for pattern_def in self.CLAIM_PATTERNS:
            match = pattern_def.pattern.search(claim)
            if match:
                verify_method = getattr(self, pattern_def.verify_fn, None)
                if verify_method:
                    # Extract parameters if extractor exists
                    if pattern_def.extract_fn:
                        params = pattern_def.extract_fn(match)
                    else:
                        params = {}

                    result = verify_method(**params)
                    result.claim = claim
                    self._log_verification(result)
                    return result

        # No verifiable pattern found — assume true (don't block on unknown claims)
        result = VerificationResult(
            verified=True,
            claim=claim,
            evidence="No verifiable pattern matched; assuming true",
            confidence=0.5,
        )
        self._log_verification(result)
        return result

    def check_process_exists(self, process_name: str) -> VerificationResult:
        """
        Verify a process is actually running.

        Handles common app names (chrome, firefox, notepad, etc.)
        and executable names (chrome.exe, firefox.exe).
        """
        # Normalize process name
        name_lower = process_name.lower().rstrip(".exe")

        # Common app name mappings
        app_mappings = {
            "chrome": ["chrome", "googlechrome"],
            "firefox": ["firefox"],
            "edge": ["msedge", "microsoftedge"],
            "notepad": ["notepad", "notepad++", "notepadplusplus"],
            "vscode": ["code", "vscode"],
            "explorer": ["explorer"],
            "spotify": ["spotify"],
            "discord": ["discord"],
            "slack": ["slack"],
        }

        # Get possible process names to check
        possible_names = app_mappings.get(name_lower, [name_lower])

        try:
            # Use tasklist on Windows, ps on Unix
            if os.name == "nt":
                output = subprocess.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {possible_names[0]}.exe", "/NH"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                found = (
                    output.returncode == 0 and possible_names[0].lower() in output.stdout.lower()
                )
            else:
                output = subprocess.run(
                    ["pgrep", "-f", "|".join(possible_names)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                found = bool(output.returncode == 0 and output.stdout.strip())

            if found:
                return VerificationResult(
                    verified=True,
                    claim=f"Process {process_name} exists",
                    evidence=f"Found running process matching '{process_name}'",
                    confidence=0.9,
                )
            else:
                return VerificationResult(
                    verified=False,
                    claim=f"Process {process_name} exists",
                    evidence=f"No running process found matching '{process_name}'",
                    confidence=0.85,
                    correction_hint=(
                        f"Process '{process_name}' is not running. "
                        f"The launch may have failed silently."
                    ),
                )

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.warning(f"GroundingVerifier: Process check failed: {e}")
            return VerificationResult(
                verified=True,  # Don't fail on check errors
                claim=f"Process {process_name} exists",
                evidence=f"Could not verify: {e}",
                confidence=0.3,
            )

    def check_file_exists(self, path: str) -> VerificationResult:
        """
        Verify a file was actually created or modified.

        Checks both existence and recent modification time.
        """
        try:
            file_path = Path(path)

            # Handle relative paths and common patterns
            if not file_path.is_absolute():
                # Try common locations
                candidates = [
                    Path.cwd() / path,
                    Path.home() / "Downloads" / path,
                    Path.home() / "Desktop" / path,
                    Path.home() / "Documents" / path,
                ]
                for candidate in candidates:
                    if candidate.exists():
                        file_path = candidate
                        break

            if file_path.exists():
                # Check if recently modified (within last 60 seconds)
                mtime = file_path.stat().st_mtime
                age = time.time() - mtime
                if age < 60:
                    return VerificationResult(
                        verified=True,
                        claim=f"File {path} exists",
                        evidence=f"File exists at {file_path} (modified {age:.1f}s ago)",
                        confidence=0.95,
                    )
                else:
                    return VerificationResult(
                        verified=True,
                        claim=f"File {path} exists",
                        evidence=f"File exists at {file_path} but was modified {age:.0f}s ago",
                        confidence=0.7,
                    )
            else:
                return VerificationResult(
                    verified=False,
                    claim=f"File {path} exists",
                    evidence=f"File not found at {file_path}",
                    confidence=0.9,
                    correction_hint=(
                        f"File '{path}' does not exist. The save/create operation may have failed."
                    ),
                )

        except (OSError, ValueError) as e:
            logger.warning(f"GroundingVerifier: File check failed: {e}")
            return VerificationResult(
                verified=True,
                claim=f"File {path} exists",
                evidence=f"Could not verify: {e}",
                confidence=0.3,
            )

    def check_url_accessible(self, url: str) -> VerificationResult:
        """
        Verify a URL is actually reachable.

        Lightweight HEAD request to check accessibility.
        """
        try:
            # Ensure URL has scheme
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"

            # Quick HEAD-like check with timeout
            response = urlopen(url, timeout=5)
            status_code = response.getcode()

            if 200 <= status_code < 400:
                return VerificationResult(
                    verified=True,
                    claim=f"URL {url} accessible",
                    evidence=f"URL returned status {status_code}",
                    confidence=0.9,
                )
            else:
                return VerificationResult(
                    verified=False,
                    claim=f"URL {url} accessible",
                    evidence=f"URL returned status {status_code}",
                    confidence=0.85,
                    correction_hint=f"URL returned status {status_code}, not a success code.",
                )

        except URLError as e:
            return VerificationResult(
                verified=False,
                claim=f"URL {url} accessible",
                evidence=f"URL not accessible: {e}",
                confidence=0.8,
                correction_hint=f"Could not reach URL: {e}",
            )
        except Exception as e:
            logger.warning(f"GroundingVerifier: URL check failed: {e}")
            return VerificationResult(
                verified=True,
                claim=f"URL {url} accessible",
                evidence=f"Could not verify: {e}",
                confidence=0.3,
            )

    def check_command_success(self, return_code: int = 0) -> VerificationResult:
        """
        Verify a command succeeded based on return code.

        If no return code provided, checks the last tool output.
        """
        if return_code == 0:
            return VerificationResult(
                verified=True,
                claim="Command succeeded",
                evidence=f"Return code was {return_code}",
                confidence=0.95,
            )
        else:
            return VerificationResult(
                verified=False,
                claim="Command succeeded",
                evidence=f"Return code was {return_code} (non-zero indicates failure)",
                confidence=0.95,
                correction_hint=(
                    f"Command failed with return code {return_code}. "
                    f"Don't claim success when the command failed."
                ),
            )

    def _log_verification(self, result: VerificationResult) -> None:
        """Log a verification result for debugging."""
        self._verification_log.append(result)

        status = "PASS" if result.verified else "FAIL"
        logger.info(
            f"GroundingVerifier: [{status}] claim='{result.claim[:80]}' "
            f"evidence='{result.evidence[:80]}' confidence={result.confidence:.2f}"
        )

        if not result.verified:
            logger.warning(f"GroundingVerifier: HALLUCINATION DETECTED — {result.correction_hint}")

    def get_correction_prompt(self, result: VerificationResult) -> str:
        """
        Generate a correction prompt for the LLM if verification failed.

        This can be injected into the next LLM call to correct the hallucination.
        """
        if result.verified:
            return ""

        return (
            f"[GROUNDING CORRECTION]\n"
            f'Your previous claim was: "{result.claim}"\n'
            f"Reality check: {result.evidence}\n"
            f"Action: {result.correction_hint}\n"
            f"Do not claim success for operations that failed. "
            f"Acknowledge the failure and try a different approach."
        )

    def get_verification_log(self) -> List[VerificationResult]:
        """Get all verification results for debugging."""
        return self._verification_log.copy()

    def clear_log(self) -> None:
        """Clear the verification log."""
        self._verification_log.clear()


# ── Integration Helper ─────────────────────────────────────────────────


def verify_tool_result(
    verifier: GroundingVerifier,
    llm_claim: str,
    tool_output: Dict[str, Any],
) -> Tuple[bool, str]:
    """
    Convenience function for verifying tool results in the agent loop.

    Args:
        verifier: GroundingVerifier instance
        llm_claim: What the LLM said happened
        tool_output: The actual tool execution result

    Returns:
        Tuple of (verified: bool, correction_prompt: str)
        correction_prompt is empty if verified=True
    """
    result = verifier.verify_claim(llm_claim, tool_output)
    correction = verifier.get_correction_prompt(result) if not result.verified else ""
    return result.verified, correction
