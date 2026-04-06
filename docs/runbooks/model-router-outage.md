# Model Router Outage Runbook

## Symptoms
- All agent calls fail with connection errors
- `curl localhost:8080` returns connection refused
- Agents report "model unavailable"
- Fallback chain exhausted

## Diagnosis Steps

### 1. Check model router status
```bash
curl -s http://localhost:8080/health || echo "DOWN"
ps aux | grep model-router | grep -v grep
```

### 2. Check dependencies
```bash
# Ollama (local models)
curl -s http://localhost:11434/api/tags || echo "Ollama DOWN"

# OpenRouter (cloud models)
curl -s https://openrouter.ai/api/v1/models || echo "OpenRouter DOWN"
```

### 3. Check logs
```bash
tail -100 logs/daemon.log | grep -i "router\|model\|error"
```

## Resolution

### Restart model router:
```bash
bash bin/stop-model-router.sh
bash bin/start-model-router.sh
bash bin/status-model-router.sh
```

### If Ollama is down:
```bash
systemctl --user restart ollama
# Or if running directly:
ollama serve &
```

### If OpenRouter is down:
1. Check status: https://openrouter.ai/status
2. Switch to local models only:
   ```bash
   # Edit opencode.json to use ollama as primary
   ```

### If all providers are down:
1. Enable fallback to local models:
   ```bash
   export FALLBACK_TO_LOCAL=true
   ```
2. Pull required models:
   ```bash
   ollama pull qwen2.5-coder:7b
   ollama pull llama3.2:3b
   ```

## Prevention
- Monitor router health: `bash bin/health-l1-pulse.sh`
- Keep local models as fallback
- Set up alerting for router downtime
- Regular health checks in CI
