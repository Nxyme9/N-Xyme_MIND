# Ollama Not Responding Runbook

## Symptoms
- Agent reports "Ollama not responding" or "connection refused"
- Model inference requests timeout
- `curl http://localhost:11434/api/tags` returns connection error
- Health check shows Ollama offline

## Diagnosis Steps

### 1. Check if Ollama process is running
```bash
ps aux | grep ollama | grep -v grep
```

### 2. Check if Ollama is listening on port 11434
```bash
curl -s http://localhost:11434/api/tags || echo "Connection failed"
```

### 3. Check available models
```bash
ollama list
```

### 4. Check Ollama logs
```bash
journalctl --user -u ollama -n 50 2>/dev/null
# or
ps aux | grep ollama
```

## Resolution

### Restart Ollama:
```bash
# Kill existing Ollama processes
pkill -f ollama || true

# Start Ollama in background
ollama serve &
```

### If Ollama won't start:
```bash
# Check for port conflicts
lsof -i :11434

# Check for model corruption
ollama list

# Pull a fresh model if needed
ollama pull llama3.2:3b
```

### Check model status:
```bash
# Verify models are loaded
curl -s http://localhost:11434/api/tags | python3 -m json.tool
```

## Prevention
- Monitor Ollama: `bash bin/health-l1-pulse.sh`
- Keep models updated: `ollama pull` periodically
- Check logs regularly: `journalctl --user -u ollama`
