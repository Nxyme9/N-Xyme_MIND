#!/usr/bin/env python3
"""
ErrorAgentDelegator - Error-to-Agent Delegation System

Allows errors to be automatically delegated to AI agents for:
- Diagnosis: What went wrong and why
- Resolution: How to fix the error
- Analysis: Root cause identification
- Prevention: How to avoid similar errors

Usage:
    from src.dashboard.error_delegator import ErrorAgentDelegator

    delegator = ErrorAgentDelegator()
    result = await delegator.delegate(error, context)
    print(result.diagnosis)
    print(result.resolution)
"""

import asyncio
import logging
import traceback
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Severity classification for errors."""

    LOW = "low"  # Minor issue, continue operation
    MEDIUM = "medium"  # Moderate issue, may affect functionality
    HIGH = "high"  # Serious issue, immediate attention needed
    CRITICAL = "critical"  # System-threatening, requires immediate action


class ErrorCategory(Enum):
    """Categorization of error types."""

    NETWORK = "network"  # Network/connectivity issues
    MEMORY = "memory"  # Memory system errors
    AUTH = "auth"  # Authentication/authorization
    FILE_SYSTEM = "file_system"  # File operations
    AGENT = "agent"  # Agent execution failures
    PARSING = "parsing"  # Parse/format errors
    TIMEOUT = "timeout"  # Timeout errors
    CONFIG = "config"  # Configuration issues
    UNKNOWN = "unknown"  # Unclassified errors


@dataclass
class ErrorContext:
    """Context information for an error."""

    error: Exception
    source: str  # Where the error occurred
    timestamp: datetime = field(default_factory=datetime.now)
    stack_trace: str = ""
    additional_context: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.stack_trace:
            self.stack_trace = traceback.format_exc()


@dataclass
class DelegationResult:
    """Result from error delegation to agent."""

    success: bool
    diagnosis: str = ""  # What happened and why
    resolution: str = ""  # How to fix it
    root_cause: str = ""  # Root cause analysis
    prevention: str = ""  # How to prevent similar errors
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.UNKNOWN
    agent_model: str = "llama3.2:3b"
    latency_ms: float = 0.0
    error: str = ""  # If delegation itself failed

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "diagnosis": self.diagnosis,
            "resolution": self.resolution,
            "root_cause": self.root_cause,
            "prevention": self.prevention,
            "severity": self.severity.value,
            "category": self.category.value,
            "agent_model": self.agent_model,
            "latency_ms": self.latency_ms,
        }


class ErrorAgentDelegator:
    """
    Delegates errors to local AI agents for analysis and resolution.

    Uses Ollama to analyze errors and provide:
    - Diagnosis: What's wrong
    - Resolution: How to fix it
    - Root cause: Why it happened
    - Prevention: How to avoid recurrence
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        general_model: str = "llama3.2:3b",
        code_model: str = "qwen2.5-coder:7b",
        timeout: float = 30.0,
        enabled: bool = True,
    ):
        self.ollama_url = ollama_url
        self.general_model = general_model
        self.code_model = code_model
        self.timeout = timeout
        self.enabled = enabled
        self._http_client: Optional[httpx.AsyncClient] = None
        self._delegate_count = 0
        self._success_count = 0

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            "total_delegations": self._delegate_count,
            "successful": self._success_count,
            "success_rate": self._success_count / max(self._delegate_count, 1),
        }

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=self.timeout)
        return self._http_client

    def _categorize_error(self, error: Exception, source: str) -> ErrorCategory:
        """Categorize the error based on exception type and source."""
        error_str = str(error).lower()
        source_lower = source.lower()

        # Network errors
        if any(
            kw in error_str
            for kw in ["connection", "timeout", "network", "refused", "unreachable"]
        ):
            return ErrorCategory.NETWORK
        if any(kw in error_str for kw in ["socket", "http", "urlopen", "ssl"]):
            return ErrorCategory.NETWORK

        # Memory errors
        if "memory" in source_lower or "sqlite" in error_str:
            return ErrorCategory.MEMORY

        # File system errors
        if any(
            kw in error_str
            for kw in ["not found", "permission", "enoent", "file", "directory"]
        ):
            return ErrorCategory.FILE_SYSTEM
        if "FileNotFoundError" in type(error).__name__:
            return ErrorCategory.FILE_SYSTEM

        # Auth errors
        if any(
            kw in error_str
            for kw in ["auth", "permission", "denied", "unauthorized", "forbidden"]
        ):
            return ErrorCategory.AUTH

        # Agent/execution errors
        if "agent" in source_lower or "tool" in source_lower:
            return ErrorCategory.AGENT

        # Parsing errors
        if any(
            kw in error_str for kw in ["parse", "json", "decode", "format", "invalid"]
        ):
            return ErrorCategory.PARSING

        # Timeout errors
        if "timeout" in error_str or "timed out" in error_str:
            return ErrorCategory.TIMEOUT

        # Config errors
        if any(kw in error_str for kw in ["config", "setting", "value", "required"]):
            return ErrorCategory.CONFIG

        return ErrorCategory.UNKNOWN

    def _classify_severity(
        self, error: Exception, category: ErrorCategory
    ) -> ErrorSeverity:
        """Classify error severity."""
        error_type = type(error).__name__

        # Critical error types
        if error_type in ["SystemExit", "KeyboardInterrupt", "MemoryError"]:
            return ErrorSeverity.CRITICAL

        # High severity categories
        if category in [ErrorCategory.MEMORY, ErrorCategory.AUTH]:
            return ErrorSeverity.HIGH

        # Check for critical keywords
        if any(
            kw in str(error).lower()
            for kw in ["fatal", "crash", "kill", "oom", "out of memory"]
        ):
            return ErrorSeverity.CRITICAL

        return ErrorSeverity.MEDIUM

    def _build_prompt(self, context: ErrorContext) -> str:
        """Build the prompt for the AI agent."""
        category = self._categorize_error(context.error, context.source)

        prompt = f"""You are an expert system diagnostician. Analyze this error and provide:
1. DIAGNOSIS: What happened and why
2. RESOLUTION: How to fix it (specific steps)
3. ROOT CAUSE: The underlying reason
4. PREVENTION: How to avoid similar errors

Error Details:
- Error Type: {type(context.error).__name__}
- Error Message: {str(context.error)}
- Source: {context.source}
- Category: {category.value}
- Time: {context.timestamp.isoformat()}
"""

        if context.stack_trace:
            prompt += f"\nStack Trace:\n{context.stack_trace}"

        if context.additional_context:
            prompt += f"\nAdditional Context:\n"
            for k, v in context.additional_context.items():
                prompt += f"- {k}: {v}\n"

        prompt += """
Provide your analysis in this format:
DIAGNOSIS: <your diagnosis>
RESOLUTION: <specific steps to fix>
ROOT CAUSE: <underlying reason>
PREVENTION: <how to prevent recurrence>"""

        return prompt

    async def _call_ollama(self, prompt: str, model: str) -> str:
        """Call Ollama with the prompt."""
        client = await self._get_client()

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # More deterministic for diagnostics
                "num_predict": 512,
            },
        }

        response = await client.post(
            f"{self.ollama_url}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        result = response.json()
        return result.get("response", "").strip()

    def _parse_response(self, response: str) -> DelegationResult:
        """Parse the AI response into structured result."""
        result = DelegationResult(success=False)

        lines = response.split("\n")
        current_field = None
        value_lines = []

        # Strip markdown formatting from each line upfront
        def clean_line(line: str) -> str:
            # Remove bold markers **text** or __text__
            import re

            line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
            line = re.sub(r"__([^_]+)__", r"\1", line)
            # Remove # headers (## DIAGNOSIS -> DIAGNOSIS)
            line = re.sub(r"^#+\s*", "", line)
            return line.strip()

        for line in lines:
            original_line = line
            line = clean_line(line)
            if not line:
                continue

            # Check for field markers - handle both "DIAGNOSIS:" and "DIAGNOSIS"
            upper_line = line.upper()

            if upper_line.startswith("DIAGNOSIS") or upper_line.startswith(
                "DIAGNOSIS:"
            ):
                current_field = "diagnosis"
                # Handle both "DIAGNOSIS:" and "DIAGNOSIS" formats
                if ":" in line:
                    result.diagnosis = line.split(":", 1)[1].strip()
                else:
                    result.diagnosis = ""
            elif upper_line.startswith("RESOLUTION") or upper_line.startswith(
                "RESOLUTION:"
            ):
                current_field = "resolution"
                if ":" in line:
                    result.resolution = line.split(":", 1)[1].strip()
                else:
                    result.resolution = ""
            elif upper_line.startswith("ROOT CAUSE") or upper_line.startswith(
                "ROOT CAUSE:"
            ):
                current_field = "root_cause"
                if ":" in line:
                    result.root_cause = line.split(":", 1)[1].strip()
                else:
                    result.root_cause = ""
            elif upper_line.startswith("PREVENTION") or upper_line.startswith(
                "PREVENTION:"
            ):
                current_field = "prevention"
                if ":" in line:
                    result.prevention = line.split(":", 1)[1].strip()
                else:
                    result.prevention = ""
            elif current_field and line and not line.startswith("<"):
                # Continuation of current field
                if current_field == "diagnosis":
                    result.diagnosis += " " + line
                elif current_field == "resolution":
                    result.resolution += " " + line
                elif current_field == "root_cause":
                    result.root_cause += " " + line
                elif current_field == "prevention":
                    result.prevention += " " + line

        # If we got any useful info, mark as success
        if result.diagnosis or result.resolution:
            result.success = True
            self._success_count += 1

        return result

    async def delegate(
        self,
        error: Exception,
        source: str,
        additional_context: Optional[Dict[str, Any]] = None,
        force: bool = False,
    ) -> DelegationResult:
        """
        Delegate an error to an AI agent for analysis.

        Args:
            error: The exception that occurred
            source: Where the error occurred (module/function name)
            additional_context: Extra context about the error
            force: Force delegation even if disabled (for critical errors)

        Returns:
            DelegationResult with diagnosis, resolution, etc.
        """
        start_time = asyncio.get_event_loop().time()

        # Check if delegation is enabled (unless force=True for critical errors)
        if not self.enabled and not force:
            return DelegationResult(
                success=False,
                error="Error delegation disabled",
            )

        self._delegate_count += 1

        # Build context
        context = ErrorContext(
            error=error,
            source=source,
            additional_context=additional_context or {},
        )

        # Categorize and classify
        category = self._categorize_error(error, source)
        severity = self._classify_severity(error, category)

        # Build prompt and call Ollama
        try:
            prompt = self._build_prompt(context)

            # Use code model for technical errors, general for others
            model = (
                self.code_model
                if category
                in [
                    ErrorCategory.AGENT,
                    ErrorCategory.PARSING,
                    ErrorCategory.CONFIG,
                ]
                else self.general_model
            )

            response = await self._call_ollama(prompt, model)
            result = self._parse_response(response)

        except Exception as e:
            logger.warning(f"ErrorAgentDelegator: Ollama call failed: {e}")
            return DelegationResult(
                success=False,
                error=f"Delegation failed: {str(e)}",
            )

        # Set metadata
        result.category = category
        result.severity = severity
        result.latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
        result.agent_model = self.general_model

        return result

    async def delegate_sync(self, error: Exception, source: str) -> DelegationResult:
        """Synchronous wrapper for delegate (runs in thread pool)."""
        return await asyncio.get_event_loop().run_in_executor(
            None, lambda: asyncio.run(self.delegate(error, source))
        )

    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            await self._http_client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# ─── Convenience Functions ───────────────────────────────────────────────────


async def quick_delegate(error: Exception, source: str) -> DelegationResult:
    """Quick delegation using default settings."""
    async with ErrorAgentDelegator() as delegator:
        return await delegator.delegate(error, source)


def quick_delegate_sync(error: Exception, source: str) -> DelegationResult:
    """Synchronous quick delegation."""
    return asyncio.run(quick_delegate(error, source))
