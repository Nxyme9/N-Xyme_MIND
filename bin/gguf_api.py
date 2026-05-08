#!/usr/bin/env python3
"""
GGUF Model Server Manager API
Provides REST API for model switching and server management
"""

import subprocess
import json
import os
import signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import time
import httpx

# Configuration
PORT = 8888
LLAMA_PORT = 8080
MODEL_DIR = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models"
SERVER_BIN = "/home/nxyme/llama.cpp/build/bin/llama-server"
PID_FILE = "/tmp/llama-server.pid"
LOG_FILE = "/tmp/llama-server.log"

# Server state
current_model = None
server_process = None


def get_available_models():
    """List all GGUF models."""
    models = []
    for f in os.listdir(MODEL_DIR):
        if f.endswith(".gguf"):
            path = os.path.join(MODEL_DIR, f)
            size = os.path.getsize(path)
            models.append(
                {"name": f, "size": size, "size_mb": round(size / (1024 * 1024), 1)}
            )
    return models


def is_server_running():
    """Check if llama-server is running."""
    try:
        resp = httpx.get(f"http://localhost:{LLAMA_PORT}/health", timeout=2)
        return resp.status_code == 200
    except:
        return False


def get_server_model():
    """Get currently loaded model."""
    try:
        resp = httpx.get(f"http://localhost:{LLAMA_PORT}/models", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("data", [{}])[0].get("id", "unknown")
    except:
        pass
    return None


def start_server(model_name: str, background: bool = True):
    """Start llama-server with specified model."""
    global current_model, server_process

    model_path = os.path.join(MODEL_DIR, model_name)
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}")

    # Kill existing server
    try:
        subprocess.run(["fuser", "-k", f"{LLAMA_PORT}/tcp"], capture_output=True)
        time.sleep(1)
    except:
        pass

    cmd = [
        SERVER_BIN,
        "-m",
        model_path,
        "-c",
        "4096",
        "-np",
        "8",
        "-cb",
        "--jinja",
        "--tools",
        "all",
        "--port",
        str(LLAMA_PORT),
        "--host",
        "127.0.0.1",
    ]

    if background:
        server_process = subprocess.Popen(
            cmd, stdout=open(LOG_FILE, "w"), stderr=subprocess.STDOUT
        )
        with open(PID_FILE, "w") as f:
            f.write(str(server_process.pid))

        # Wait for server to be ready
        for i in range(30):
            if is_server_running():
                current_model = model_name
                return {"status": "ok", "model": model_name}
            time.sleep(1)
        raise TimeoutError("Server failed to start")
    else:
        subprocess.run(cmd)
        current_model = model_name
        return {"status": "ok", "model": model_name}


def stop_server():
    """Stop llama-server."""
    try:
        subprocess.run(["fuser", "-k", f"{LLAMA_PORT}/tcp"], capture_output=True)
    except:
        pass
    try:
        with open(PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
    except:
        pass
    return {"status": "stopped"}


class RequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/models":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            models = get_available_models()
            current = get_server_model()
            self.wfile.write(
                json.dumps(
                    {
                        "available": models,
                        "current": current,
                        "server_running": is_server_running(),
                    }
                ).encode()
            )

        elif path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            health = {
                "llama_server": is_server_running(),
                "current_model": get_server_model(),
            }
            self.wfile.write(json.dumps(health).encode())

        elif path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"""<!DOCTYPE html>
<html><head><title>GGUF Manager</title></head>
<body><h1>GGUF Model Server</h1>
<p><a href="/models">Models</a> | <a href="/health">Health</a></p>
</body></html>""")

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/switch":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length).decode()
            data = parse_qs(body)
            model = data.get("model", [None])[0]

            if not model:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": "model required"}).encode())
                return

            try:
                result = start_server(model)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif path == "/stop":
            stop_server()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "stopped"}).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass  # Suppress logging


def main():
    print(f"🚀 Starting GGUF Manager API on port {PORT}")
    print(f"   Llama server port: {LLAMA_PORT}")
    print(f"   Model directory: {MODEL_DIR}")
    print("")
    print("Endpoints:")
    print("  GET  /models     - List available models")
    print("  GET  /health     - Check server health")
    print("  POST /switch     - Switch model (param: model=<filename>)")
    print("  POST /stop       - Stop llama-server")
    print("")

    # Start llama-server with default model on first run
    if not is_server_running():
        print("⚡ Starting default llama-server...")
        try:
            start_server("qwen2.5-0.5b-instruct-q4_k_m.gguf")
            print("✅ Server started")
        except Exception as e:
            print(f"⚠️  Server start failed: {e}")

    # Start API server
    server = HTTPServer(("0.0.0.0", PORT), RequestHandler)
    print(f"✅ API listening on http://localhost:{PORT}")
    server.serve_forever()


if __name__ == "__main__":
    main()
