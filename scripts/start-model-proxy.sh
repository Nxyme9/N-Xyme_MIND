#!/usr/bin/env bash
# Start Model Router Proxy and VPN Rotator

export PYTHONPATH=/home/nxyme/N-Xyme_MIND
export OPENCODE_API_KEY=${OPENCODE_API_KEY:-$(cat ~/.config/opencode/secrets/opencode-api-key 2>/dev/null)}
export OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-$(cat ~/.config/opencode/secrets/openrouter-api-key 2>/dev/null)}

echo "Starting Model Router Proxy on port 8080..."
cd /home/nxyme/N-Xyme_MIND
python3 -m uvicorn src.proxy.model_router:app --host 0.0.0.0 --port 8080
