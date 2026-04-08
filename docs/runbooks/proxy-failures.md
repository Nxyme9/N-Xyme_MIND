# Proxy Failures Runbook

## Symptoms
- Agent reports "proxy connection failed" or "SOCKS5 error"
- Model requests timeout or return 403/407 errors
- Health check shows proxy offline
- Rate limiting kicks in unexpectedly

## Diagnosis Steps

### 1. Check if proxy processes are running
```bash
ps aux | grep -E "(proxy|rotator)" | grep -v grep
```

### 2. Check proxy ports
```bash
for port in 1080 1081 1082 1083 1084 1085 1086 1087; do
  nc -zv localhost $port 2>&1 | grep -q succeeded && echo "Port $port: OK" || echo "Port $port: FAILED"
done
```

### 3. Test proxy connectivity
```bash
curl -x socks5://localhost:1080 https://api.openai.com/v1/models --max-time 5
```

### 4. Check VPN/proxy logs
```bash
tail -50 logs/proxy.log 2>/dev/null
python3 -c "import src.vpn.rotator; print('Rotator OK')"
```

## Resolution

### Restart proxy rotator:
```bash
# Kill existing proxy processes
pkill -f rotator || true
pkill -f proxy || true

# Restart the rotator
cd /home/nxyme/N-Xyme_CODE/N-Xyme_MIND
python3 src/vpn/rotator.py &

# Or use the service
systemctl --user restart proxy-rotator.service
```

### Restart a specific proxy port:
```bash
# Check which proxy is on port 1080
ps aux | grep 1080
# Restart specific proxy
```

### Check VPN configuration:
```bash
# Verify VPN is working
curl -I https://api.openai.com --max-time 10
```

## Prevention
- Monitor proxy health: `bash bin/health-monitor.sh`
- Rotate proxies regularly
- Check VPN connectivity before heavy tasks
- Review rate limits in `src/vpn/rotator.py`
