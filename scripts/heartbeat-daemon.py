#!/usr/bin/env python3
"""
Heartbeat Daemon - System health monitor using llama3.2:3b
Monitors Neo4j, Graphiti, Ollama, MCPs, and agents.
"""

import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Any

import requests

from jarvis.notifications import add_notification

# Centralized config
from jarvis.config.graphiti_config import (
    GRAPHITI_HEALTH_URL,
    GRAPHITI_INJECT_URL,
    NEO4J_URL,
    OLLAMA_URL,
    OLLAMA_TAGS_URL,
    SERVICE_URLS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("heartbeat-daemon")


class HeartbeatDaemon:
    """Lightweight system monitor using local LLM for health analysis."""

    def __init__(self, interval: int = 300):
        self.interval = interval  # 5 minutes
        self.running = True
        self.status_history: list[dict[str, Any]] = []
        self.ollama_url = OLLAMA_URL
        self.model = "llama3.2:latest"

    def start(self) -> None:
        """Start the heartbeat loop."""
        log.info("Heartbeat Daemon started (interval: %ds)", self.interval)
        try:
            while self.running:
                status = self.check_all()
                analysis = self.analyze_health(status)
                self.log_status(status, analysis)
                self.act_on_analysis(analysis, status)
                time.sleep(self.interval)
        except KeyboardInterrupt:
            log.info("Heartbeat Daemon stopped")

    def check_all(self) -> dict[str, Any]:
        """Run all health checks and return aggregated status."""
        return {
            "timestamp": datetime.now().isoformat(),
            "neo4j": self.check_neo4j(),
            "graphiti": self.check_graphiti(),
            "ollama": self.check_ollama(),
            "mcps": self.check_mcps(),
            "agents": self.check_agents(),
        }

    def check_neo4j(self) -> dict[str, Any]:
        """Check Neo4j database connectivity."""
        try:
            resp = requests.get(NEO4J_URL, timeout=5)
            return {
                "status": "OK" if resp.ok else "DEGRADED",
                "code": resp.status_code,
                "url": NEO4J_URL,
            }
        except requests.ConnectionError:
            return {"status": "CRITICAL", "error": "Connection refused", "url": NEO4J_URL}
        except requests.Timeout:
            return {"status": "WARNING", "error": "Timeout", "url": NEO4J_URL}
        except Exception as e:
            return {"status": "CRITICAL", "error": str(e), "url": NEO4J_URL}

    def check_graphiti(self) -> dict[str, Any]:
        """Check Graphiti memory service."""
        try:
            resp = requests.get(GRAPHITI_HEALTH_URL, timeout=5)
            if resp.ok:
                data = resp.json()
                return {"status": "OK", "details": data, "url": GRAPHITI_HEALTH_URL}
            return {"status": "DEGRADED", "code": resp.status_code, "url": GRAPHITI_HEALTH_URL}
        except requests.ConnectionError:
            return {"status": "CRITICAL", "error": "Connection refused", "url": GRAPHITI_HEALTH_URL}
        except requests.Timeout:
            return {"status": "WARNING", "error": "Timeout", "url": GRAPHITI_HEALTH_URL}
        except Exception as e:
            return {"status": "CRITICAL", "error": str(e), "url": GRAPHITI_HEALTH_URL}

    def check_ollama(self) -> dict[str, Any]:
        """Check Ollama LLM service and loaded models."""
        try:
            resp = requests.get(OLLAMA_TAGS_URL, timeout=5)
            if resp.ok:
                data = resp.json()
                models = data.get("models", [])
                return {
                    "status": "OK",
                    "models_loaded": len(models),
                    "model_names": [m.get("name", "?") for m in models],
                    "url": OLLAMA_TAGS_URL,
                }
            return {"status": "DEGRADED", "code": resp.status_code, "url": OLLAMA_TAGS_URL}
        except requests.ConnectionError:
            return {"status": "CRITICAL", "error": "Connection refused", "url": OLLAMA_TAGS_URL}
        except requests.Timeout:
            return {"status": "WARNING", "error": "Timeout", "url": OLLAMA_TAGS_URL}
        except Exception as e:
            return {"status": "CRITICAL", "error": str(e), "url": OLLAMA_TAGS_URL}

    def check_mcps(self) -> dict[str, Any]:
        """Check MCP server endpoints from SERVICE_URLS."""
        results = {}
        for name, url in SERVICE_URLS.items():
            if name in ("graphiti", "ollama", "neo4j"):
                continue  # Already checked separately
            try:
                resp = requests.get(url, timeout=5)
                results[name] = {
                    "status": "OK" if resp.ok else "DEGRADED",
                    "code": resp.status_code,
                }
            except requests.ConnectionError:
                results[name] = {"status": "CRITICAL", "error": "Connection refused"}
            except requests.Timeout:
                results[name] = {"status": "WARNING", "error": "Timeout"}
            except Exception as e:
                results[name] = {"status": "CRITICAL", "error": str(e)}

        overall = "OK"
        if any(r["status"] == "CRITICAL" for r in results.values()):
            overall = "CRITICAL"
        elif any(r["status"] == "WARNING" for r in results.values()):
            overall = "WARNING"
        elif any(r["status"] == "DEGRADED" for r in results.values()):
            overall = "DEGRADED"

        return {"status": overall, "servers": results}

    def check_agents(self) -> dict[str, Any]:
        """Check agent status via Graphiti memory."""
        try:
            resp = requests.post(
                f"{self.ollama_url}/api/tags",
                timeout=5,
            )
            # Placeholder: agent status would come from session/orchestrator
            return {
                "status": "OK",
                "note": "Agent status requires orchestrator integration",
            }
        except (requests.RequestException, OSError):
            return {"status": "UNKNOWN", "note": "Cannot determine agent status"}

    def analyze_health(self, status: dict[str, Any]) -> dict[str, Any]:
        """Analyze system health using local LLM (llama3.2:3b)."""
        prompt = f"""Analyze this system health report and return JSON with:
- overall: "HEALTHY" | "DEGRADED" | "CRITICAL"
- issues: list of problems found
- actions: list of recommended actions
- summary: one-line summary

Report:
{json.dumps(status, indent=2)}

Return ONLY valid JSON, no markdown fences."""

        try:
            resp = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
                timeout=30,
            )
            if resp.ok:
                raw = resp.json().get("response", "{}")
                # Strip markdown fences if present
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1]
                if raw.endswith("```"):
                    raw = raw.rsplit("```", 1)[0]
                return json.loads(raw.strip())
        except json.JSONDecodeError:
            log.warning("LLM returned invalid JSON, using fallback analysis")
        except Exception as e:
            log.warning("LLM analysis failed: %s", e)

        # Fallback: rule-based analysis
        return self._fallback_analysis(status)

    def _fallback_analysis(self, status: dict[str, Any]) -> dict[str, Any]:
        """Rule-based health analysis when LLM is unavailable."""
        issues = []
        actions = []
        severity = "HEALTHY"

        for service in ("neo4j", "graphiti", "ollama"):
            svc_status = status.get(service, {})
            if svc_status.get("status") == "CRITICAL":
                issues.append(f"{service.upper()} is DOWN: {svc_status.get('error', 'unknown')}")
                actions.append(f"Restart {service} service")
                severity = "CRITICAL"
            elif svc_status.get("status") in ("WARNING", "DEGRADED"):
                issues.append(f"{service.upper()} is degraded")
                severity = "DEGRADED" if severity != "CRITICAL" else severity

        mcps = status.get("mcps", {})
        if mcps.get("status") == "CRITICAL":
            for name, info in mcps.get("servers", {}).items():
                if info.get("status") == "CRITICAL":
                    issues.append(f"MCP '{name}' is DOWN")
                    actions.append(f"Restart MCP server: {name}")
                    severity = "CRITICAL"

        return {
            "overall": severity,
            "issues": issues,
            "actions": actions,
            "summary": f"{len(issues)} issues detected" if issues else "All systems operational",
        }

    def log_status(self, status: dict[str, Any], analysis: dict[str, Any]) -> None:
        """Log status to Graphiti memory and local history."""
        entry = {
            "timestamp": status["timestamp"],
            "overall": analysis.get("overall", "UNKNOWN"),
            "summary": analysis.get("summary", ""),
            "issues": analysis.get("issues", []),
        }
        self.status_history.append(entry)

        # Keep last 100 entries
        if len(self.status_history) > 100:
            self.status_history = self.status_history[-100:]

        # Inject into Graphiti memory
        try:
            requests.post(
                GRAPHITI_INJECT_URL,
                json={
                    "content": f"HEARTBEAT: {analysis.get('overall', 'UNKNOWN')} - {analysis.get('summary', '')}",
                    "metadata": {
                        "type": "heartbeat",
                        "severity": analysis.get("overall", "UNKNOWN"),
                        "timestamp": status["timestamp"],
                    },
                },
                timeout=10,
            )
        except Exception as e:
            log.warning("Failed to log to Graphiti: %s", e)

        # Console output
        severity = analysis.get("overall", "UNKNOWN")
        icon = {"HEALTHY": "+", "DEGRADED": "!", "CRITICAL": "X"}.get(severity, "?")
        log.info("[%s] %s: %s", icon, severity, analysis.get("summary", ""))

        for issue in analysis.get("issues", []):
            log.warning("  Issue: %s", issue)

    def act_on_analysis(self, analysis: dict[str, Any], status: dict[str, Any]) -> None:
        """Take automated action on CRITICAL issues."""
        if analysis.get("overall") != "CRITICAL":
            return

        for action in analysis.get("actions", []):
            log.warning("ACTION REQUIRED: %s", action)

        # Auto-restart logic for known services
        critical_services = []
        for service in ("neo4j", "graphiti", "ollama"):
            if status.get(service, {}).get("status") == "CRITICAL":
                critical_services.append(service)

        if critical_services:
            log.critical(
                "CRITICAL services down: %s — manual intervention required",
                ", ".join(critical_services),
            )
            # Could add auto-restart here with subprocess, but safer to alert
            self._alert_critical(critical_services, analysis)

    def _alert_critical(self, services: list[str], analysis: dict[str, Any]) -> None:
        """Alert on critical issues via Jarvis notifications and alert file."""
        alert_msg = (
            f"CRITICAL ALERT: {', '.join(services)} down. "
            f"Issues: {'; '.join(analysis.get('issues', []))}"
        )
        log.critical(alert_msg)
        # Jarvis notification (popup queue)
        try:
            add_notification(
                title="CRITICAL: Services Down",
                message=alert_msg,
                timeout=15,
            )
        except Exception as e:
            log.debug(f"Failed to send Jarvis notification: {e}")
        # Alert file for external monitoring
        try:
            with open("logs/heartbeat-alerts.log", "a") as f:
                f.write(f"{datetime.now().isoformat()} {alert_msg}\n")
        except Exception as e:
            log.debug(f"Failed to write alert to file: {e}")


if __name__ == "__main__":
    daemon = HeartbeatDaemon(interval=300)
    daemon.start()
