#!/usr/bin/env python3
"""
Frankenstein Engine Launcher
High-performance local LLM inference with dynamic batching
"""

import subprocess
import sys
import os
import argparse
import time
import socket
import signal

# Paths
ENGINE = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/src/engine/build/frankenstein-engine"
MODEL_DIR = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models"
LLAMA_MODEL_DIR = "/home/nxyme/llama.cpp/models"

MODELS = {
    "0.5b": f"{LLAMA_MODEL_DIR}/qwen2.5-0.5b-q4.gguf",
    "1.5b": f"{LLAMA_MODEL_DIR}/qwen2.5-1.5b-q4.gguf",
    "7b": f"{MODEL_DIR}/qwen2.5-coder-7b-q4_k_m.gguf",
    "14b": f"{MODEL_DIR}/Qwen2.5-Coder-14B-Q4_K_M.gguf",
}

PORT = 8080
SERVER_PID_FILE = "/tmp/frankenstein.pid"


def check_port(port):
    """Check if port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def stop_server():
    """Stop running server."""
    try:
        with open(SERVER_PID_FILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, signal.SIGTERM)
        print(f"Stopped server (PID: {pid})")
        time.sleep(1)
    except:
        pass

    if check_port(PORT):
        # Force kill
        subprocess.run(["pkill", "-f", "frankenstein-engine"], check=False)


def start_server(
    model_name="7b", port=PORT, n_parallel=64, ctx_size=2048, threads=8, gpu_layers=99
):
    """Start the Frankenstein engine server."""
    if check_port(PORT):
        print(f"Server already running on port {PORT}")
        return False

    model_path = MODELS.get(model_name)
    if not model_path or not os.path.exists(model_path):
        print(f"Model not found: {model_name}")
        print(f"Available: {list(MODELS.keys())}")
        return False

    # Build command
    cmd = [
        ENGINE,
        "-m",
        model_path,
        "-ngl",
        str(gpu_layers),
        "-np",
        str(n_parallel),
        "-c",
        str(ctx_size),
        "-t",
        str(threads),
        "--port",
        str(port),
        "--host",
        "0.0.0.0",
        "--log-disable",
    ]

    print(f"Starting Frankenstein Engine...")
    print(f"Model: {model_name} ({model_path})")
    print(f"Port: {port}, Parallel: {n_parallel}, CTX: {ctx_size}")

    # Start in background
    with open("/tmp/frankenstein.log", "w") as f:
        proc = subprocess.Popen(cmd, stdout=f, stderr=f)

    with open(SERVER_PID_FILE, "w") as f:
        f.write(str(proc.pid))

    # Wait for server to start
    for i in range(20):
        if check_port(port):
            print(f"✅ Server running on http://localhost:{port}")
            return True
        time.sleep(0.5)

    print("❌ Server failed to start")
    return False


def status():
    """Check server status."""
    if check_port(PORT):
        print(f"✅ Server running on port {PORT}")
        return True
    else:
        print(f"❌ Server not running on port {PORT}")
        return False


def benchmark(model_name="7b", n_tokens=256):
    """Run quick benchmark."""
    model_path = MODELS.get(model_name)
    if not model_path:
        print(f"Unknown model: {model_name}")
        return

    cmd = [
        ENGINE,
        "-m",
        model_path,
        "-ngl",
        "99",
        "-np",
        "64",
        "-c",
        "2048",
        "-t",
        "8",
        "-p",
        "Write code:",
        "-n",
        str(n_tokens),
        "--perf",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    # Extract speed
    for line in result.stderr.split("\n"):
        if "speed:" in line and "t/s" in line:
            print(f"Model: {model_name} -> {line.strip()}")
            break


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Frankenstein Engine Launcher")
    parser.add_argument(
        "action",
        choices=["start", "stop", "status", "benchmark"],
        help="Action to perform",
    )
    parser.add_argument(
        "--model", "-m", default="7b", choices=list(MODELS.keys()), help="Model to use"
    )
    parser.add_argument("--port", "-p", type=int, default=PORT, help="Port")
    parser.add_argument("--parallel", "-n", type=int, default=64, help="N parallel")
    parser.add_argument("--ctx", "-c", type=int, default=2048, help="Context size")

    args = parser.parse_args()

    if args.action == "start":
        start_server(args.model, args.port, args.parallel, args.ctx)
    elif args.action == "stop":
        stop_server()
    elif args.action == "status":
        status()
    elif args.action == "benchmark":
        benchmark(args.model)
