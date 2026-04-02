#!/usr/bin/env bash
# N-Xyme Catalyst CPU Pinning Script
# Pins services to specific CPU cores

set -e

echo "CPU Pinning for N-Xyme Catalyst"

# Check if running as root (needed for taskset)
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run as root or with sudo"
    exit 1
fi

# Find Ollama process
OLLAMA_PID=$(pgrep -f "ollama serve" | head -1)
if [ -n "$OLLAMA_PID" ]; then
    echo "Pinning Ollama (PID $OLLAMA_PID) to cores 0-3"
    taskset -cp 0-3 $OLLAMA_PID
else
    echo "Ollama process not found, skipping"
fi

# Find Neo4j process (Java)
NEO4J_PID=$(pgrep -f "neo4j" | head -1)
if [ -n "$NEO4J_PID" ]; then
    echo "Pinning Neo4j (PID $NEO4J_PID) to cores 4-7"
    taskset -cp 4-7 $NEO4J_PID
else
    echo "Neo4j process not found, skipping"
fi

# Find Docker processes (optional)
DOCKER_PIDS=$(pgrep -f "dockerd" | head -1)
if [ -n "$DOCKER_PIDS" ]; then
    echo "Pinning Docker daemon to cores 0-3"
    for pid in $DOCKER_PIDS; do
        taskset -cp 0-3 $pid
    done
fi

echo "CPU pinning complete!"
echo "Run 'taskset -cp <PID>' to verify"