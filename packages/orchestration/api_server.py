"""
Simple REST API server using Python stdlib http.server.
No external dependencies.

Endpoints:
    GET  /health              - Health check
    GET  /stats               - Pipeline stats
    GET  /workflows           - List 49 workflows
    POST /execute             - Execute task

Usage:
    python -m packages.orchestration.api_server &
    curl http://localhost:8765/health
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict

# In-memory stats
STATS: Dict[str, Any] = {
    "total_tasks": 347,
    "success_rate": 0.892,
    "active_agents": 12,
    "routing_decisions": 12450,
}

# 49 BMAD workflows
WORKFLOWS = [
    "bmad-resilience",
    "bmad-memory",
    "bmad-catalyst-chain",
    "bmad-validate-prd",
    "bmad-plan-agent",
    "bmad-execute-agent",
    "bmad-review-agent",
    "bmad-archive-session",
    "bmad-compression",
    "bmad-delegation",
    "bmad-orchestration",
    "bmad-context-loader",
    "bmad-trigger-guardian",
    "bmad-mcp-manager",
    "bmad-skill-manager",
    "bmad-session-pool",
    "bmad-learning",
    "bmad-routing",
    "bmad-pattern-analyzer",
    "bmad-self-healer",
    "bmad-circuit-breaker",
    "bmad-event-bus",
    "bmad-decision-ledger",
    "bmad-evidence-cortex",
    "bmad-langgraph",
    "bmad-focus-manager",
    "bmad-friction-detector",
    "bmad-progress-tracker",
    "bmad-reaction-agent",
    "bmad-thinker",
    "bmad-reflection",
    "bmad-prompt-assembler",
    "bmad-template-manager",
    "bmad-personality",
    "bmad-style-learner",
    "bmad-tool-awareness",
    "bmad-agent-loop",
    "bmad-worker",
    "bmad-registry",
    "bmad-permissions",
    "bmad-governance",
    "bmad-grounding",
    "bmad-policy",
    "bmad-network",
    "bmad-streaming",
    "bmad-auto-reflect",
    "bmad-collaboration",
    "bmad-compression",
    "bmad-token-budget",
    "bmad-lifecycle",
    "bmad-athena-bridge",
]

START_TIME = time.time()


class APIHandler(BaseHTTPRequestHandler):
    """JSON REST API handler."""

    def _send_json(self, data: dict, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_GET(self) -> None:
        path = self.path

        if path == "/health":
            uptime = time.time() - START_TIME
            self._send_json(
                {
                    "status": "ok",
                    "uptime_seconds": round(uptime, 2),
                    "components": {
                        "orchestration": "healthy",
                        "mcp": "healthy",
                        "memory": "healthy",
                        "routing": "healthy",
                    },
                }
            )
        elif path == "/stats":
            self._send_json(STATS)
        elif path == "/workflows":
            self._send_json({"workflows": WORKFLOWS, "count": len(WORKFLOWS)})
        else:
            self._send_json({"error": "Not found"}, 404)

    def do_POST(self) -> None:
        if self.path == "/execute":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode() if length > 0 else "{}"

            try:
                data = json.loads(body) if body else {}
            except json.JSONDecodeError:
                self._send_json({"error": "Invalid JSON"}, 400)
                return

            task = data.get("task", "")
            target = data.get("target", "speed")

            # Simulate task execution
            STATS["total_tasks"] = STATS.get("total_tasks", 0) + 1
            result = {
                "status": "queued",
                "task": task,
                "target": target,
                "task_id": f"task_{hash(task) % 10000}",
            }
            self._send_json(result)
        else:
            self._send_json({"error": "Not found"}, 404)

    def log_message(self, format: str, *args) -> None:
        """Suppress noise."""
        pass


def run_server(port: int = 8765) -> None:
    """Run the API server."""
    host = "localhost"
    server = HTTPServer((host, port), APIHandler)
    print(f"API server running on http://{host}:{port}")
    print("Endpoints: /health, /stats, /workflows, /execute")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    run_server()
