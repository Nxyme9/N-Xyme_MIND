#!/usr/bin/env bash
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
export PYTHONPATH="/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/src:$PYTHONPATH"

echo "Starting N-Xyme Intelligent Router Proxy on port 8080..."
python3 -m uvicorn proxy.openai_proxy:app --host 127.0.0.1 --port 8080 &
PROXY_PID=$!
echo "Proxy started (PID: $PROXY_PID)"

sleep 3

# Test proxy
curl -sf http://127.0.0.1:8080/health > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Proxy is healthy"
else
    echo "❌ Proxy failed to start"
    exit 1
fi

echo ""
echo "To use with OpenCode, update ~/.config/opencode/opencode.json:"
echo '{'
echo '  "provider": {'
echo '    "local-proxy": {'
echo '      "name": "local-proxy",'
echo '      "options": {'
echo '        "baseURL": "http://127.0.0.1:8080/v1",'
echo '        "apiKey": "local"'
echo '      }'
echo '    }'
echo '  },'
echo '  "model": "local-proxy/qwen3.6-plus-free",'
echo '  "enabled_providers": ["local-proxy", "openrouter", "google"]'
echo '}'
