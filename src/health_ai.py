"""
Health AI — AI-powered diagnostics

Uses local Ollama model to analyze errors and suggest fixes.

Usage:
    from health_ai import HealthAIDiagnostics

    ai = HealthAIDiagnostics()
    diagnosis = ai.diagnose(error_log)
    print(diagnosis.suggestion)
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import httpx

from health_core import ComponentStatus

logger = logging.getLogger(__name__)


@dataclass
class Diagnosis:
    """AI diagnosis result."""

    component: str
    issue: str
    severity: str  # low, medium, high, critical
    suggestion: str
    confidence: float = 0.0
    auto_fixable: bool = False


class HealthAIDiagnostics:
    """AI-powered health diagnostics using local Ollama."""

    def __init__(
        self, ollama_url: str = "http://localhost:11434", model: str = "llama3.2:3b-instruct-q4_K_M"
    ):
        self.ollama_url = ollama_url
        self.model = model
        self._http_client = None
        logger.info(f"HealthAIDiagnostics: Initialized (model={model})")

    def _get_client(self) -> httpx.Client:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.Client(timeout=30.0)
        return self._http_client

    def diagnose(self, component_status: ComponentStatus) -> Diagnosis:
        """Diagnose a component's health issue."""
        if component_status.health.value == "healthy":
            return Diagnosis(
                component=component_status.name,
                issue="No issues detected",
                severity="low",
                suggestion="Component is healthy",
                confidence=1.0,
            )

        # Build context for AI
        context = f"""
Component: {component_status.name}
Status: {component_status.health.value}
Message: {component_status.message}
Error: {component_status.error or "None"}

Suggest a fix for this issue. Be specific and actionable.
"""

        try:
            suggestion = self._call_ai(context)

            return Diagnosis(
                component=component_status.name,
                issue=component_status.message,
                severity=component_status.health.value,
                suggestion=suggestion,
                confidence=0.8,
                auto_fixable=self._is_auto_fixable(component_status),
            )
        except Exception as e:
            logger.error(f"HealthAIDiagnostics: Diagnosis failed: {e}")
            return Diagnosis(
                component=component_status.name,
                issue=component_status.message,
                severity="high",
                suggestion=f"Manual intervention required: {component_status.error}",
                confidence=0.3,
            )

    def diagnose_all(self, statuses: Dict[str, ComponentStatus]) -> List[Diagnosis]:
        """Diagnose all unhealthy components."""
        diagnoses = []
        for name, status in statuses.items():
            if status.health.value != "healthy":
                diagnosis = self.diagnose(status)
                diagnoses.append(diagnosis)
        return diagnoses

    async def diagnose_all_async(self, statuses: Dict[str, ComponentStatus]) -> List[Diagnosis]:
        """Diagnose all unhealthy components in parallel."""
        import asyncio

        unhealthy = {
            name: status for name, status in statuses.items() if status.health.value != "healthy"
        }

        async def _diagnose_one(status: ComponentStatus) -> Diagnosis:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.diagnose, status)

        tasks = [_diagnose_one(status) for status in unhealthy.values()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        diagnoses = []
        for result in results:
            if isinstance(result, Diagnosis):
                diagnoses.append(result)

        return diagnoses

    def get_report(self, statuses: Dict[str, ComponentStatus]) -> Dict:
        """Generate a diagnostic report."""
        diagnoses = self.diagnose_all(statuses)

        return {
            "total_issues": len(diagnoses),
            "critical": len([d for d in diagnoses if d.severity == "critical"]),
            "high": len([d for d in diagnoses if d.severity == "high"]),
            "medium": len([d for d in diagnoses if d.severity == "medium"]),
            "low": len([d for d in diagnoses if d.severity == "low"]),
            "auto_fixable": len([d for d in diagnoses if d.auto_fixable]),
            "diagnoses": [
                {
                    "component": d.component,
                    "issue": d.issue,
                    "severity": d.severity,
                    "suggestion": d.suggestion,
                    "confidence": d.confidence,
                    "auto_fixable": d.auto_fixable,
                }
                for d in diagnoses
            ],
        }

    def _call_ai(self, prompt: str) -> str:
        """Call Ollama for AI generation."""
        client = self._get_client()
        resp = client.post(
            f"{self.ollama_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json().get("response", "")

    def _is_auto_fixable(self, status: ComponentStatus) -> bool:
        """Check if the issue can be auto-fixed."""
        auto_fixable_patterns = [
            "not found",
            "not running",
            "closed",
            "timeout",
            "connection refused",
        ]
        return any(pattern in (status.message or "").lower() for pattern in auto_fixable_patterns)

    def close(self):
        if self._http_client and not self._http_client.is_closed:
            self._http_client.close()
