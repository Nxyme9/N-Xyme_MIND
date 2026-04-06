# Agent Routing Failure Runbook

## Symptoms
- Tasks routed to wrong agent
- Routing latency > 5 seconds
- Routing returns errors or None
- Multi-agent chains not triggering

## Diagnosis Steps

### 1. Check routing logs
```bash
grep -i "route" logs/*.log | tail -50
```

### 2. Test routing manually
```bash
PYTHONPATH=. python3 -c "
from bin.model_selector import ModelSelector
s = ModelSelector()
print(s.route('test task'))
"
```

### 3. Check model router service
```bash
curl -s http://localhost:8080/health || echo "Model router DOWN"
```

### 4. Check trigger configuration
```bash
python3 -c "import json; print(json.dumps(json.load(open('triggers.json')), indent=2))" | head -20
```

## Resolution

### If model router is down:
```bash
bash bin/start-model-router.sh
bash bin/health-monitor.sh
```

### If triggers are misconfigured:
```bash
python3 -m json.tool triggers.json > /dev/null && echo "Valid JSON" || echo "Invalid JSON"
```

### If routing is slow:
1. Check model availability: `curl -s http://localhost:11434/api/tags`
2. Check fallback chain: `python3 bin/model-fallback.py`
3. Review rate limits: `grep RATE_LIMIT .env`

## Escalation
- If routing completely broken → restart all services: `bash n-xyme-mind.sh`
- If specific agent failing → check agent config in `opencode.json`
- If persistent → check `logs/daemon.log` for errors
