"""Fusion Bridge — JSON-RPC server routing to direct Python calls."""
import json, time, sys, os
from http.server import HTTPServer, BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(__file__))

PORT = 9999

def health(args):
    from direct_health import run_all_checks
    return run_all_checks()

def trigger(args):
    from trigger_router import TriggerRouter
    event = args.get("event", args)
    return TriggerRouter("triggers.json").process_event(event)

def velocity(args):
    from metrics_store import MetricsStore
    store = MetricsStore("data/nervous_system.db")
    return store.get_velocity(args.get("days", 7))

def context(args):
    from context_injector import ContextInjector
    ci = ContextInjector()
    ctx = ci.get_context(args.get("query", "preferences"), args.get("limit", 5))
    return {"episodes": len(ctx.episodes), "summary": ctx.summary[:300]}

TOOLS = {
    "catalyst_health": health,
    "catalyst_trigger": trigger,
    "catalyst_velocity": velocity,
    "catalyst_context": context,
}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "bridge": "fusion", "tools": list(TOOLS.keys())}).encode())

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length))
        method = body.get("method", "")
        params = body.get("params", {})
        rid = body.get("id", 1)

        if method == "tools/list":
            result = {"tools": [{"name": k, "description": f"Catalyst {k.replace('catalyst_', '')}"} for k in TOOLS]}
        elif method == "tools/call":
            tool_name = params.get("name", "")
            args = params.get("arguments", {})
            if tool_name in TOOLS:
                try:
                    data = TOOLS[tool_name](args)
                    result = {"content": [{"type": "text", "text": json.dumps(data)}]}
                except Exception as e:
                    result = {"content": [{"type": "text", "text": json.dumps({"error": str(e)})}]}
            else:
                result = {"content": [{"type": "text", "text": json.dumps({"error": f"Unknown tool: {tool_name}"})}]}
        else:
            result = {"error": f"Unknown method: {method}"}

        response = {"jsonrpc": "2.0", "id": rid, "result": result}
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(response).encode())

    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    print(f"Fusion Bridge starting on port {PORT}")
    print(f"Tools: {list(TOOLS.keys())}")
    server = HTTPServer(("localhost", PORT), Handler)
    server.serve_forever()
