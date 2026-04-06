"""
Dashboard AI Brain — Unified AI orchestration layer for N-Xyme MIND Dashboard.

Provides AI-powered features for the dashboard including:
- System health analysis
- Log summarization
- Issue diagnosis
- Natural language chat
- Predictive alerts
- Auto-troubleshooting

Uses Ollama (llama3.2:3b for general, qwen2.5-coder:7b for code analysis).

Usage:
    from src.dashboard.ai_brain import DashboardAIBrain

    brain = DashboardAIBrain()
    if brain.is_available():
        health_summary = await brain.analyze_system_health(live_data)
        print(health_summary)
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from src.dashboard.error_delegator import ErrorAgentDelegator
from src.health.health_ai import Diagnosis, HealthAIDiagnostics
from src.health.health_core import ComponentStatus, ComponentHealth
from src.health.health_schema import HealthStatus
from src.infrastructure.anomaly_detection import AnomalyDetector, Forecast
from src.model_router.ollama_manager import OllamaManager

logger = logging.getLogger(__name__)


# System prompts specific to N-Xyme MIND context
SYSTEM_PROMPT_HEALTH = """You are the N-Xyme MIND system health analyzer.
You analyze system metrics and generate natural language health summaries.
N-Xyme MIND is a personal AI coding workspace powered by OpenCode + OMO multi-agent orchestration.

Components you analyze:
- daemon: The main N-Xyme orchestration daemon
- ollama: Local LLM inference server (localhost:11434)
- memory: Athena memory system (semantic search, knowledge graph)
- router: Model routing system (IP rotation, proxy management)
- agents: OMO agent pool (Sisyphus, Hephaestus, Oracle, etc.)

Respond with a concise health summary in format:
"System Health: XX% - [component status], [component status]..."

Use severity levels: healthy, warning, critical.
"""

SYSTEM_PROMPT_LOGS = """You are the N-Xyme MIND log analyzer.
You summarize daemon log entries and identify key issues.
Focus on:
- Errors and exceptions
- Warnings and deprecations
- Component failures
- Performance issues

Respond with a concise summary:
"Last N log lines summary: X errors, Y warnings - [key issues]..."
"""

SYSTEM_PROMPT_CHAT = """You are the N-Xyme MIND AI Brain - the central intelligence of a sophisticated AI-powered workflow orchestration system.

Your role is to help users understand, manage, and debug their backend system through natural language conversation.

## System Architecture You Know:
- OMO v3.14.0 multi-agent orchestration with 11 specialized agents
- Model router with local Ollama models + 8 SOCKS5 proxies for IP rotation
- Athena memory system with semantic search, 22K+ files indexed
- OpenCode TUI dashboard with 17 tabs and 61 actions
- Self-learning system with Q-Learning routing optimization
- Security sandbox with circuit breakers and rate limiters

## Your Capabilities:
1. Answer questions about system architecture and components
2. Explain agent interactions, routing decisions, and orchestration flows
3. Help debug issues with daemons, proxies, memory, and model routing
4. Provide insights into memory retrieval, learning outcomes, and routing performance
5. Execute basic commands (start/stop services, check status)

## Context You Have Access To:
- Current dashboard state and active tab
- Daemon, Ollama, and proxy status
- Memory/knowledge base stats (files, chunks, sources)
- Routing system state (backends, outcomes)
- Recent logs and error patterns

## Response Guidelines:
- Be technically accurate but concise
- Reference specific files/functions when discussing code
- Suggest concrete commands when applicable
- If you don't know something, say so directly
"""

SYSTEM_PROMPT_PREDICT = """You are the N-Xyme MIND predictive analytics engine.
You analyze metric history and predict future issues.
Use the provided forecast data to generate predictions.
Focus on:
- Resource trends (CPU, memory, VRAM)
- Service availability
- Performance degradation

Respond with actionable predictions:
"Predicted: [metric] [trend], may [issue] in N minutes"
"""

SYSTEM_PROMPT_TROUBLESHOOT = """You are the N-Xyme MIND troubleshooting guide.
You generate step-by-step fix instructions for component errors.
N-Xyme MIND components:
- daemon: Run 'bash n-xyme-mind.sh'
- ollama: Run 'ollama serve' or 'systemctl --user start ollama'
- memory: Check Athena health with 'python -m athena health'
- router: Run 'systemctl --user start model-router.service'
- agents: Check agent status in dashboard

Respond with a numbered list of actionable steps.
Each step should be a command or specific action.
"""


@dataclass
class CachedResult:
    """Cached AI result with TTL."""

    result: str
    timestamp: float


class DashboardAIBrain:
    """
    Unified AI orchestration layer for N-Xyme MIND Dashboard.

    Provides all AI-powered features for the dashboard by integrating:
    - HealthAIDiagnostics for issue diagnosis
    - OllamaManager for model lifecycle
    - AnomalyDetector for predictive alerts

    Args:
        ollama_url: URL of the Ollama server (default: http://localhost:11434)
        general_model: Model for general tasks (default: llama3.2:3b)
        code_model: Model for code analysis (default: qwen2.5-coder:7b)
        cache_ttl: Cache duration in seconds (default: 60)
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        general_model: str = "llama3.2:3b",
        code_model: str = "qwen2.5-coder:7b",
        cache_ttl: int = 60,
    ) -> None:
        self.ollama_url = ollama_url
        self.general_model = general_model
        self.code_model = code_model
        self.cache_ttl = cache_ttl

        # Initialize components
        self._health_ai = HealthAIDiagnostics(
            ollama_url=ollama_url, model=general_model
        )
        self._ollama_manager = OllamaManager(ollama_url=ollama_url)
        self._anomaly_detector = AnomalyDetector()

        # Error delegator - auto-delegates errors to AI agents
        self._error_delegator = ErrorAgentDelegator(
            ollama_url=ollama_url,
            general_model=general_model,
            code_model=code_model,
        )

        # HTTP client
        self._http_client: Optional[httpx.AsyncClient] = None

        # Cache for AI responses
        self._cache: Dict[str, CachedResult] = {}

        # Check Ollama availability on init
        self._available = self._check_availability()

        logger.info(
            f"DashboardAIBrain: Initialized (general={general_model}, code={code_model}, "
            f"available={self._available})"
        )

    async def handle_error(
        self,
        error: Exception,
        source: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Handle an error by delegating to an AI agent for diagnosis.

        Args:
            error: The exception that occurred
            source: Where the error occurred (module/function name)
            context: Additional context about the error

        Returns:
            AI diagnosis and resolution instructions
        """
        result = await self._error_delegator.delegate(error, source, context or {})

        if result.success:
            return (
                f"DIAGNOSIS: {result.diagnosis}\n\n"
                f"RESOLUTION: {result.resolution}\n\n"
                f"ROOT CAUSE: {result.root_cause}\n\n"
                f"PREVENTION: {result.prevention}\n\n"
                f"Severity: {result.severity.value} | Category: {result.category.value}"
            )
        else:
            return f"Error delegation failed: {result.error}"

    @property
    def error_delegation_stats(self) -> Dict[str, Any]:
        """Get error delegation statistics."""
        return self._error_delegator.stats

    @property
    def error_delegation_enabled(self) -> bool:
        """Check if error delegation is enabled."""
        return self._error_delegator.enabled

    def enable_error_delegation(self) -> None:
        """Enable error delegation."""
        self._error_delegator.enabled = True

    def disable_error_delegation(self) -> None:
        """Disable error delegation."""
        self._error_delegator.enabled = False

    def _check_availability(self) -> bool:
        """Check if Ollama is reachable."""
        try:
            return self._ollama_manager.health_check()
        except Exception as e:
            logger.warning(f"DashboardAIBrain: Availability check failed: {e}")
            return False

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    def _get_cache_key(self, prefix: str, *args: str) -> str:
        """Generate cache key from prefix and arguments."""
        return f"{prefix}:{':'.join(str(a) for a in args)}"

    def _get_cached(self, key: str) -> Optional[str]:
        """Get cached result if not expired."""
        cached = self._cache.get(key)
        if cached and (time.time() - cached.timestamp) < self.cache_ttl:
            return cached.result
        return None

    def _set_cached(self, key: str, result: str) -> None:
        """Set cached result with current timestamp."""
        self._cache[key] = CachedResult(result=result, timestamp=time.time())

    async def _call_ollama(
        self,
        prompt: str,
        model: Optional[str] = None,
        system: Optional[str] = None,
    ) -> str:
        """Call Ollama for AI generation."""
        model = model or self.general_model
        client = self._get_client()

        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        if system:
            payload["system"] = system

        try:
            resp = await client.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
            )
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            logger.error(f"DashboardAIBrain: Ollama call failed: {e}")
            return f"AI service temporarily unavailable: {e}"

    async def _call_ollama_sync(
        self, prompt: str, model: Optional[str] = None, system: Optional[str] = None
    ) -> str:
        """Synchronous wrapper for Ollama calls using run_in_executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_wrapper, prompt, model, system
        )

    def _sync_wrapper(
        self, prompt: str, model: Optional[str] = None, system: Optional[str] = None
    ) -> str:
        """Sync wrapper that runs in executor."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self._call_ollama(prompt, model, system))
        finally:
            loop.close()

    # ── Public API ─────────────────────────────────────────────────────────────

    async def analyze_system_health(self, live_data: Dict[str, Any]) -> str:
        """
        Analyze system health from live metrics.

        Args:
            live_data: Dict containing daemon, ollama, memory, router, agents stats.
                       Example: {
                           "daemon": {"status": "running", "cpu": 12.5, "memory": 45.2},
                           "ollama": {"status": "running", "model": "llama3.2:3b"},
                           "memory": {"status": "healthy", "vectors": 1234},
                           "router": {"status": "running", "proxies": 8},
                           "agents": {"active": 3, "idle": 8}
                       }

        Returns:
            Natural language health summary string.
            Example: "System Health: 95% - Daemon running, Ollama OK, 2 warnings..."
        """
        # Check cache
        cache_key = self._get_cache_key("health", str(sorted(live_data.keys())))
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Build prompt from live data
        components = []
        for name, data in live_data.items():
            status = data.get("status", "unknown")
            components.append(f"- {name}: {status}")

        # Calculate health percentage
        healthy_count = sum(
            1
            for d in live_data.values()
            if d.get("status") in ("running", "healthy", "active")
        )
        total_count = len(live_data)
        health_pct = int((healthy_count / total_count) * 100) if total_count > 0 else 0

        # Build detailed prompt
        prompt = f"""System Health: {health_pct}%

Components:
{chr(10).join(components)}

Details:
{live_data}

Generate a concise natural language summary of system health.
"""

        result = await self._call_ollama(
            prompt=prompt,
            system=SYSTEM_PROMPT_HEALTH,
        )

        self._set_cached(cache_key, result)
        return result

    async def summarize_logs(self, log_lines: List[str], max_lines: int = 50) -> str:
        """
        Summarize log entries.

        Args:
            log_lines: List of log lines from daemon.log
            max_lines: Maximum number of lines to summarize (default: 50)

        Returns:
            Summary string.
            Example: "Last 50 log lines summary: 3 errors, 2 warnings - Key issues: ..."
        """
        if not log_lines:
            return "No log lines provided."

        # Check cache
        cache_key = self._get_cache_key(
            "logs", str(hash(tuple(log_lines[-max_lines:])))
        )
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        # Truncate to max_lines
        lines_to_summarize = log_lines[-max_lines:]
        log_text = "\n".join(lines_to_summarize)

        prompt = f"""Summarize these log lines:

{log_text}

Provide a concise summary focusing on errors, warnings, and key issues."""

        result = await self._call_ollama(
            prompt=prompt,
            system=SYSTEM_PROMPT_LOGS,
        )

        self._set_cached(cache_key, result)
        return result

    async def diagnose_issue(
        self, component: str, error: str, context: str = ""
    ) -> str:
        """
        Diagnose an issue with a component.

        Wraps HealthAIDiagnostics.diagnose() with AI enhancement.

        Args:
            component: Component name (daemon, ollama, memory, router, agents)
            error: Error message or log entry
            context: Additional context (optional)

        Returns:
            AI diagnosis with severity and fix suggestion.
            Example: "Component: ollama | Severity: high | Fix: Restart with 'ollama serve'"
        """
        # Try to use HealthAIDiagnostics first
        try:
            status = ComponentStatus(
                name=component,
                health=ComponentHealth.UNHEALTHY,
                message=error,
                error=error,
            )
            diagnosis = self._health_ai.diagnose(status)

            # If AI suggestion is available, enhance it
            if (
                diagnosis.suggestion
                and diagnosis.suggestion != f"Manual intervention required: {error}"
            ):
                return (
                    f"Component: {diagnosis.component} | "
                    f"Severity: {diagnosis.severity} | "
                    f"Issue: {diagnosis.issue} | "
                    f"Fix: {diagnosis.suggestion}"
                )
        except Exception as e:
            logger.warning(f"DashboardAIDiagnostics: HealthAIDiagnostics failed: {e}")

        # Fallback to direct Ollama call
        prompt = f"""Diagnose this issue:

Component: {component}
Error: {error}
Context: {context}

Provide a diagnosis with severity (low/medium/high/critical) and specific fix suggestion."""

        result = await self._call_ollama(prompt=prompt)
        return result

    async def chat(self, query: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Natural language chat with system context.

        Args:
            query: User query
            context: Optional context dict with current system state

        Returns:
            AI response string.
        """
        # Build context if provided
        context_str = ""
        if context:
            context_str = f"""

Current System State:
{context}
"""

        prompt = f"""{query}{context_str}

Provide a helpful, concise response."""

        result = await self._call_ollama(
            prompt=prompt,
            system=SYSTEM_PROMPT_CHAT,
        )
        return result

    async def predict_issues(
        self,
        history: List[Dict[str, Any]],
        horizon_minutes: int = 5,
    ) -> str:
        """
        Predict future issues based on metric history.

        Uses AnomalyDetector._forecast() + Ollama for context.

        Args:
            history: List of metric data points (dict with timestamp, value, metric name)
            horizon_minutes: Prediction horizon in minutes (default: 5)

        Returns:
            Prediction string.
            Example: "Predicted: Memory usage trending up, may exceed 80% in 5 minutes"
        """
        if not history or len(history) < 5:
            return "Insufficient data for prediction (need at least 5 data points)"

        # Group by metric
        metrics_by_name: Dict[str, List[float]] = {}
        for entry in history:
            metric_name = entry.get("metric", "unknown")
            value = entry.get("value", 0)
            if metric_name not in metrics_by_name:
                metrics_by_name[metric_name] = []
            metrics_by_name[metric_name].append(value)

        # Forecast each metric
        forecasts = []
        for metric_name, values in metrics_by_name.items():
            if len(values) >= 5:
                # Use anomaly detector's forecast method
                forecast = self._anomaly_detector._forecast(values, horizon_minutes)
                if forecast:
                    forecasts.append(
                        {
                            "metric": metric_name,
                            "current": forecast.current_value,
                            "predicted": forecast.predicted_value,
                            "trend": forecast.trend,
                            "confidence": forecast.confidence,
                        }
                    )

        if not forecasts:
            return "No predictable trends detected."

        # Build prompt with forecast data
        forecast_text = "\n".join(
            f"- {f['metric']}: {f['current']:.2f} → {f['predicted']:.2f} "
            f"({f['trend']}, confidence: {f['confidence']:.2f})"
            for f in forecasts
        )

        prompt = f"""Based on these metric forecasts, predict potential issues:

{forecast_text}

Horizon: {horizon_minutes} minutes

Provide actionable predictions focusing on metrics that may cause problems."""

        result = await self._call_ollama(
            prompt=prompt,
            system=SYSTEM_PROMPT_PREDICT,
        )
        return result

    async def generate_troubleshooting(self, component: str, error: str) -> List[str]:
        """
        Generate auto-troubleshooting steps.

        Args:
            component: Component name (daemon, ollama, memory, router, agents)
            error: Error message

        Returns:
            List of actionable troubleshooting steps.
            Example: ["1. Check status: systemctl --user status n-xyme-daemon",
                      "2. Restart: systemctl --user restart n-xyme-daemon"]
        """
        prompt = f"""Generate troubleshooting steps for:

Component: {component}
Error: {error}

Provide a numbered list of specific, actionable steps.
Each step should be a command or concrete action.
Start with step 1."""

        result = await self._call_ollama(
            prompt=prompt,
            system=SYSTEM_PROMPT_TROUBLESHOOT,
        )

        # Parse result into list of steps
        steps = []
        for line in result.split("\n"):
            line = line.strip()
            if line and (line[0].isdigit() or line.startswith("-")):
                # Clean up the step
                step = line.lstrip("0123456789.-) ").strip()
                if step:
                    steps.append(step)

        return steps if steps else [result]

    def is_available(self) -> bool:
        """
        Check if Ollama is reachable.

        Returns:
            True if Ollama is available, False otherwise.
        """
        return self._available

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get current model information.

        Returns:
            Dict with name, status, VRAM usage.
            Example: {
                "general_model": "llama3.2:3b",
                "code_model": "qwen2.5-coder:7b",
                "ollama_status": "online",
                "loaded_models": ["llama3.2:3b"],
                "available_vram_gb": 12.5
            }
        """
        info = {
            "general_model": self.general_model,
            "code_model": self.code_model,
            "ollama_status": "online" if self._available else "offline",
            "loaded_models": [],
            "available_models": [],
        }

        try:
            # Get loaded models
            loaded = self._ollama_manager.get_loaded_models()
            info["loaded_models"] = [m.name for m in loaded]

            # Get available models
            available = self._ollama_manager.get_available_models()
            info["available_models"] = [m.name for m in available]

        except Exception as e:
            logger.warning(f"DashboardAIBrain: Failed to get model info: {e}")

        return info

    # ── Lifecycle ───────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        await self._error_delegator.close()
        self._health_ai.close()
        self._ollama_manager.close()
        logger.info("DashboardAIBrain: Closed")

    def __enter__(self) -> "DashboardAIBrain":
        return self

    def __exit__(self, *args: Any) -> None:
        # Run sync close
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.close())
        finally:
            loop.close()


# ── Convenience factory ─────────────────────────────────────────────────────


def create_dashboard_brain(
    ollama_url: str = "http://localhost:11434",
) -> DashboardAIBrain:
    """Create a DashboardAIBrain instance with defaults."""
    return DashboardAIBrain(ollama_url=ollama_url)


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 60)
    print("Dashboard AI Brain — Demo")
    print("=" * 60)

    brain = create_dashboard_brain()

    print(f"\n1. Availability check")
    print(f"   Ollama available: {brain.is_available()}")

    if brain.is_available():
        print(f"\n2. Model info")
        info = brain.get_model_info()
        print(f"   General model: {info['general_model']}")
        print(f"   Code model: {info['code_model']}")
        print(f"   Loaded: {info['loaded_models']}")
        print(f"   Available: {info['available_models']}")

        print(f"\n3. System health analysis")
        live_data = {
            "daemon": {"status": "running", "cpu": 12.5, "memory": 45.2},
            "ollama": {"status": "running", "model": "llama3.2:3b"},
            "memory": {"status": "healthy", "vectors": 1234},
            "router": {"status": "running", "proxies": 8},
            "agents": {"active": 3, "idle": 8},
        }
        health = asyncio.run(brain.analyze_system_health(live_data))
        print(f"   {health}")

        print(f"\n4. Chat demo")
        response = asyncio.run(brain.chat("What agents are running in N-Xyme MIND?"))
        print(f"   {response[:200]}...")

    else:
        print("\n   Ollama is not running. Start it with:")
        print("   ollama serve")

    print("\n" + "=" * 60)
    print("Demo complete")
    print("=" * 60)
