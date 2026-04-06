#!/usr/bin/env bash
# N-Xyme Catalyst Heartbeat Monitor
# Tests all services every 30 seconds

API_KEY="${JARVIS_API_KEY:-}"
INTERVAL=30
while true; do
    clear
    echo "=== N-Xyme Catalyst Heartbeat Monitor ==="
    echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="
    
    # Test Graphiti
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo "[OK] Graphiti Memory"
    else
        echo "[FAIL] Graphiti Memory"
    fi
    
    # Test Ollama
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "[OK] Ollama AI"
    else
        echo "[FAIL] Ollama AI"
    fi
    
    # Test Jarvis API
    if curl -s http://localhost:8088/health > /dev/null 2>&1; then
        echo "[OK] Jarvis API"
    else
        echo "[FAIL] Jarvis API"
    fi
    
    # Test Jarvis Status
    if curl -s -H "Authorization: Bearer $API_KEY" http://localhost:8088/status > /dev/null 2>&1; then
        echo "[OK] Jarvis Status"
    else
        echo "[FAIL] Jarvis Status"
    fi
    
    # Test Command API
    if curl -s -X POST -H "Authorization: Bearer $API_KEY" -H "Content-Type: application/json" -d '{"message":"test"}' http://localhost:8088/command > /dev/null 2>&1; then
        echo "[OK] Command API"
    else
        echo "[FAIL] Command API"
    fi
    
    echo "=========================================="
    echo "Next test in $INTERVAL seconds..."
    echo "Press Ctrl+C to stop"
    
    sleep $INTERVAL
done
