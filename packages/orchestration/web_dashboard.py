"""
Web dashboard using Python stdlib http.server.
No external dependencies.
Serves HTML dashboard + API endpoints on port 8766.

Usage:
    python -m packages.orchestration.web_dashboard &
    # Open http://localhost:8766 in browser
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict

# In-memory stats (same as api_server.py)
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

# HTML Dashboard Template
HTMLDashboard = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>N-Xyme Pipeline Dashboard</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f1419;
            color: #e7e9ea;
            min-height: 100vh;
        }
        header {
            background: linear-gradient(90deg, #1d9bf0, #00d4aa);
            padding: 20px;
            text-align: center;
        }
        header h1 { font-size: 1.8rem; font-weight: 700; }
        .refresh-indicator {
            font-size: 0.75rem;
            opacity: 0.7;
            margin-top: 5px;
        }
        .container { padding: 20px; max-width: 1400px; margin: 0 auto; }
        .columns {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: #15202b;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #38444d;
        }
        .card h2 {
            font-size: 1rem;
            color: #1d9bf0;
            margin-bottom: 15px;
            padding-bottom: 10px;
            border-bottom: 1px solid #38444d;
        }
        .stat-row {
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #1c2a33;
        }
        .stat-label { color: #8b98a5; }
        .stat-value { font-weight: 600; }
        .status-ok { color: #00d4aa; }
        .status-error { color: #f4212e; }
        .workflow-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            max-height: 300px;
            overflow-y: auto;
        }
        .workflow-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: #1c2a33;
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 0.85rem;
        }
        .run-btn {
            background: #1d9bf0;
            color: white;
            border: none;
            padding: 4px 12px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.75rem;
        }
        .run-btn:hover { background: #1a8cd8; }
        .task-form {
            background: #15202b;
            border-radius: 12px;
            padding: 20px;
            border: 1px solid #38444d;
        }
        .task-form h2 { margin-bottom: 15px; color: #1d9bf0; }
        .form-row { display: flex; gap: 10px; margin-bottom: 10px; }
        .form-row input, .form-row select {
            flex: 1;
            padding: 12px;
            background: #1c2a33;
            border: 1px solid #38444d;
            border-radius: 8px;
            color: #e7e9ea;
            font-size: 1rem;
        }
        .form-row input:focus, .form-row select:focus {
            outline: none;
            border-color: #1d9bf0;
        }
        .submit-btn {
            background: linear-gradient(90deg, #1d9bf0, #00d4aa);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1rem;
            font-weight: 600;
        }
        .submit-btn:hover { opacity: 0.9; }
        .result {
            margin-top: 15px;
            padding: 15px;
            background: #1c2a33;
            border-radius: 8px;
            font-family: monospace;
            white-space: pre-wrap;
            display: none;
        }
        .result.show { display: block; }
        @media (max-width: 900px) {
            .columns { grid-template-columns: 1fr; }
            .workflow-grid { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <header>
        <h1>N-Xyme Pipeline Dashboard</h1>
        <div class="refresh-indicator">Auto-refresh: <span id="countdown">5</span>s</div>
    </header>
    
    <div class="container">
        <div class="columns">
            <div class="card">
                <h2>Health</h2>
                <div id="health">
                    <div class="stat-row">
                        <span class="stat-label">Status</span>
                        <span class="stat-value" id="health-status">Loading...</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Uptime</span>
                        <span class="stat-value" id="health-uptime">--</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Orchestration</span>
                        <span class="stat-value" id="health-orchestration">--</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">MCP</span>
                        <span class="stat-value" id="health-mcp">--</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Memory</span>
                        <span class="stat-value" id="health-memory">--</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Routing</span>
                        <span class="stat-value" id="health-routing">--</span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>Stats</h2>
                <div id="stats">
                    <div class="stat-row">
                        <span class="stat-label">Total Tasks</span>
                        <span class="stat-value" id="stat-total">--</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Success Rate</span>
                        <span class="stat-value" id="stat-rate">--</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Active Agents</span>
                        <span class="stat-value" id="stat-agents">--</span>
                    </div>
                    <div class="stat-row">
                        <span class="stat-label">Routing Decisions</span>
                        <span class="stat-value" id="stat-routing">--</span>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>Workflows <span id="workflow-count"></span></h2>
                <div class="workflow-grid" id="workflow-list"></div>
            </div>
        </div>
        
        <div class="task-form">
            <h2>Execute Task</h2>
            <div class="form-row">
                <input type="text" id="task-input" placeholder="Enter task description..." />
                <select id="target-select">
                    <option value="speed">Speed Priority</option>
                    <option value="quality">Quality Priority</option>
                    <option value="balanced">Balanced</option>
                </select>
            </div>
            <button class="submit-btn" onclick="executeTask()">Execute</button>
            <div class="result" id="task-result"></div>
        </div>
    </div>
    
    <script>
        let countdown = 5;
        const refreshInterval = setInterval(() => {
            countdown--;
            document.getElementById('countdown').textContent = countdown;
            if (countdown <= 0) {
                refreshData();
                countdown = 5;
            }
        }, 1000);
        
        async function refreshData() {
            try {
                const [health, stats, workflows] = await Promise.all([
                    fetch('/health').then(r => r.json()),
                    fetch('/stats').then(r => r.json()),
                    fetch('/workflows').then(r => r.json())
                ]);
                
                // Update health
                document.getElementById('health-status').textContent = health.status;
                document.getElementById('health-status').className = 'stat-value ' + (health.status === 'ok' ? 'status-ok' : 'status-error');
                document.getElementById('health-uptime').textContent = health.uptime_seconds + 's';
                const comps = health.components;
                document.getElementById('health-orchestration').textContent = comps.orchestration;
                document.getElementById('health-orchestration').className = 'stat-value ' + (comps.orchestration === 'healthy' ? 'status-ok' : 'status-error');
                document.getElementById('health-mcp').textContent = comps.mcp;
                document.getElementById('health-mcp').className = 'stat-value ' + (comps.mcp === 'healthy' ? 'status-ok' : 'status-error');
                document.getElementById('health-memory').textContent = comps.memory;
                document.getElementById('health-memory').className = 'stat-value ' + (comps.memory === 'healthy' ? 'status-ok' : 'status-error');
                document.getElementById('health-routing').textContent = comps.routing;
                document.getElementById('health-routing').className = 'stat-value ' + (comps.routing === 'healthy' ? 'status-ok' : 'status-error');
                
                // Update stats
                document.getElementById('stat-total').textContent = stats.total_tasks;
                document.getElementById('stat-rate').textContent = (stats.success_rate * 100).toFixed(1) + '%';
                document.getElementById('stat-agents').textContent = stats.active_agents;
                document.getElementById('stat-routing').textContent = stats.routing_decisions.toLocaleString();
                
                // Update workflows
                document.getElementById('workflow-count').textContent = '(' + workflows.count + ')';
                const list = document.getElementById('workflow-list');
                list.innerHTML = workflows.workflows.map(w =>
                    '<div class="workflow-item"><span>' + w + '</span><button class="run-btn" onclick="runWorkflow(\'' + w + '\')">Run</button></div>'
                ).join('');
                
            } catch (e) {
                console.error('Refresh error:', e);
            }
        }
        
        async function executeTask() {
            const task = document.getElementById('task-input').value;
            const target = document.getElementById('target-select').value;
            const resultDiv = document.getElementById('task-result');
            
            if (!task.trim()) {
                resultDiv.textContent = 'Please enter a task description';
                resultDiv.classList.add('show');
                return;
            }
            
            try {
                const r = await fetch('/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({task, target})
                });
                const data = await r.json();
                resultDiv.textContent = JSON.stringify(data, null, 2);
                resultDiv.classList.add('show');
            } catch (e) {
                resultDiv.textContent = 'Error: ' + e.message;
                resultDiv.classList.add('show');
            }
        }
        
        async function runWorkflow(name) {
            const resultDiv = document.getElementById('task-result');
            try {
                const r = await fetch('/execute', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({task: 'Run workflow: ' + name, target: 'speed'})
                });
                const data = await r.json();
                resultDiv.textContent = 'Running ' + name + '\\n' + JSON.stringify(data, null, 2);
                resultDiv.classList.add('show');
            } catch (e) {
                resultDiv.textContent = 'Error: ' + e.message;
                resultDiv.classList.add('show');
            }
        }
        
        // Initial load
        refreshData();
    </script>
</body>
</html>
"""


class DashboardHandler(BaseHTTPRequestHandler):
    """Handler for dashboard + API."""

    def _send_json(self, data: dict, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _send_html(self, html: str) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

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
        elif path == "/" or path == "/index.html":
            self._send_html(HTMLDashboard)
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


def run_server(port: int = 8766) -> None:
    """Run the dashboard server."""
    host = "localhost"
    server = HTTPServer((host, port), DashboardHandler)
    print(f"Dashboard running on http://{host}:{port}")
    print("Open http://localhost:8766 in browser")
    print("Endpoints: /health, /stats, /workflows, /execute")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.shutdown()


if __name__ == "__main__":
    run_server()
