#!/usr/bin/env python3
"""Start llama-server on port 8090 for direct GGUF benchmarking."""

import os
import sys
import subprocess
import time
import socket


def check_port(port):
    """Check if port is open."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(("127.0.0.1", port))
    sock.close()
    return result == 0


def main():
    port = 8090

    # Kill any existing
    subprocess.run(["pkill", "-f", f"llama-server.*{port}"], capture_output=True)
    time.sleep(1)

    # Start the server
    cmd = [
        "/home/nxyme/llama.cpp/build/bin/llama-server",
        "-m",
        "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/models/qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "-ngl",
        "32",
        "-c",
        "2048",
        "--port",
        str(port),
        "--host",
        "127.0.0.1",
    ]

    print(f"Starting: {' '.join(cmd)}")

    # Start with nohup equivalent
    env = os.environ.copy()
    proc = subprocess.Popen(
        cmd,
        stdout=open(f"/tmp/llama-{port}.log", "w"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    print(f"Started with PID: {proc.pid}")

    # Wait for server to be ready
    for i in range(30):
        time.sleep(1)
        if check_port(port):
            print(f"Server ready on port {port}!")
            return 0
        print(f"Waiting... ({i + 1}/30)")

    print(f"Server failed to start after 30 seconds")
    return 1


if __name__ == "__main__":
    sys.exit(main())
