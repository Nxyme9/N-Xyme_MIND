# NO SILENT RETURNS MASTER PLAN
## Zero Tolerance for Unverified "OK"

---

## The Problem

**Current State:**
```
curl -s http://localhost:8001/health
→ {"status": "ok"}

ASSUMPTION: Graphiti is working
REALITY: Might not be storing data
```

**We need PROOF, not claims.**

---

## The Rule

**EVERY test must:**
1. Call the API
2. Verify response structure
3. Verify data integrity
4. Verify functionality
5. Report ACTUAL evidence

**NEVER accept:**
- Just "ok" without proof
- Just status codes without data
- Just "listening" without responding
- Just "running" without working

---

## Implementation

### Level 1: Response Structure Verification

```python
def verify_response(response: dict, expected_keys: list) -> dict:
    """Verify response has expected structure."""
    
    missing_keys = [k for k in expected_keys if k not in response]
    
    if missing_keys:
        return {
            "valid": False,
            "error": f"Missing keys: {missing_keys}",
            "got": list(response.keys()),
            "expected": expected_keys
        }
    
    return {"valid": True, "data": response}
```

### Level 2: Data Integrity Verification

```python
def verify_data(response: dict, validators: dict) -> dict:
    """Verify response data is valid."""
    
    errors = []
    
    for key, validator in validators.items():
        if key in response:
            if not validator(response[key]):
                errors.append(f"{key} failed validation")
    
    if errors:
        return {"valid": False, "errors": errors}
    
    return {"valid": True}
```

### Level 3: Functionality Verification

```python
def verify_functionality(endpoint: str, test_payload: dict) -> dict:
    """Verify endpoint actually works."""
    
    # Send test request
    response = call_endpoint(endpoint, test_payload)
    
    # Verify it processed
    if not response.get("processed"):
        return {"valid": False, "error": "Not processed"}
    
    # Verify result
    if not response.get("result"):
        return {"valid": False, "error": "No result"}
    
    return {"valid": True, "result": response["result"]}
```

---

## Applied to Each Service

### Graphiti Memory

**BAD (Current):**
```bash
curl -s http://localhost:8001/health
→ {"status": "ok"}
```

**GOOD (Required):**
```bash
# 1. Health check
curl -s http://localhost:8001/health
→ {"status": "ok"}

# 2. Verify can store
curl -s -X POST http://localhost:8001/json-rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"graphiti_add_episode","params":{"text":"test"},"id":"1"}'
→ {"result": {"success": true, "episodeId": "ep_xxx"}}

# 3. Verify can retrieve
curl -s -X POST http://localhost:8001/json-rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"graphiti_search_nodes","params":{"query":"test"},"id":"2"}'
→ {"result": {"nodes": [...]}}

# 4. Verify data integrity
# Check that stored episode exists in search results
```

### Ollama AI

**BAD (Current):**
```bash
curl -s http://localhost:11434/api/tags
→ {"models": [...]}
```

**GOOD (Required):**
```bash
# 1. List models
curl -s http://localhost:11434/api/tags
→ {"models": [{"name": "llama3.2:3b", ...}, ...]}

# 2. Verify can generate
curl -s -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2:3b","prompt":"Say hello","stream":false}'
→ {"response": "Hello!"}

# 3. Verify response is non-empty
# Check that response has actual text
```

### Jarvis API

**BAD (Current):**
```bash
curl -s http://localhost:8088/health
→ {"status": "healthy"}
```

**GOOD (Required):**
```bash
# 1. Health check
curl -s http://localhost:8088/health
→ {"status": "healthy", "uptime": 1234, "ws_connections": 0}

# 2. Verify can process command
curl -s -X POST http://localhost:8088/command \
  -H "Authorization: Bearer xxx" \
  -H "Content-Type: application/json" \
  -d '{"message":"test"}'
→ {"status": "accepted", "timestamp": 1773957000}

# 3. Verify command was queued
# Check that command appears in history
```

---

## Test Script Implementation

```bash
#!/bin/bash
# scripts/test-all-verified.sh

PASS=0
FAIL=0
ERRORS=""

test_service() {
    local name=$1
    local url=$2
    local verify_cmd=$3
    
    echo "Testing $name..."
    
    # Basic health
    health=$(curl -s "$url/health" 2>/dev/null)
    if [ -z "$health" ]; then
        FAIL=$((FAIL+1))
        ERRORS="$ERRORS\n$name: No response"
        echo "  [FAIL] No response"
        return
    fi
    
    # Verify functionality
    result=$(eval "$verify_cmd" 2>/dev/null)
    if [ -z "$result" ]; then
        FAIL=$((FAIL+1))
        ERRORS="$ERRORS\n$name: Functionality check failed"
        echo "  [FAIL] Functionality failed"
        return
    fi
    
    PASS=$((PASS+1))
    echo "  [PASS] Verified working"
}

# Test all services
test_service "Graphiti" "http://localhost:8001" \
    "curl -s -X POST http://localhost:8001/json-rpc -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"graphiti_add_episode\",\"params\":{\"text\":\"test\"},\"id\":\"1\"}' | grep -q success"

test_service "Ollama" "http://localhost:11434" \
    "curl -s -X POST http://localhost:11434/api/generate -H 'Content-Type: application/json' -d '{\"model\":\"llama3.2:3b\",\"prompt\":\"hi\",\"stream\":false}' | grep -q response"

test_service "Jarvis" "http://localhost:8088" \
    "curl -s -X POST http://localhost:8088/command -H 'Authorization: Bearer h1_2qaF6NEK1XjNCNho1ToJvdmL5eRMJNEluKGOMBxg' -H 'Content-Type: application/json' -d '{\"message\":\"test\"}' | grep -q accepted"

# Report
echo ""
echo "=== RESULTS ==="
echo "PASS: $PASS"
echo "FAIL: $FAIL"
if [ $FAIL -gt 0 ]; then
    echo ""
    echo "ERRORS:"
    echo -e "$ERRORS"
fi
```

---

## Integration with Heartbeat

```python
class VerifiedHeartbeat:
    """Heartbeat that verifies functionality, not just status."""
    
    def check_service(self, name: str, url: str, test_func: callable) -> dict:
        """Check service with full verification."""
        
        # 1. Basic health
        health = self.check_health(url)
        if not health["ok"]:
            return {"status": "FAIL", "error": "No response"}
        
        # 2. Functionality test
        test_result = test_func()
        if not test_result["success"]:
            return {"status": "FAIL", "error": test_result["error"]}
        
        # 3. Data integrity
        integrity = self.verify_integrity(name)
        if not integrity["valid"]:
            return {"status": "FAIL", "error": integrity["error"]}
        
        return {"status": "PASS", "verified": True}
    
    def verify_integrity(self, service: str) -> dict:
        """Verify data integrity for service."""
        
        if service == "graphiti":
            # Verify can store and retrieve
            return self.verify_graphiti_integrity()
        elif service == "ollama":
            # Verify can generate
            return self.verify_ollama_integrity()
        elif service == "jarvis":
            # Verify can process commands
            return self.verify_jarvis_integrity()
        
        return {"valid": False, "error": "Unknown service"}
```

---

## The New Standard

### Every Test Must Show:

```
SERVICE: Graphiti
Health: OK (response time: 45ms)
Store test: PASS (episode ID: ep_xxx)
Retrieve test: PASS (found 1 node)
Data integrity: PASS (data matches)
VERDICT: VERIFIED WORKING
```

### Never Accept:

```
SERVICE: Graphiti
Status: ok
VERDICT: ???
```

---

## Enforcement

### In Every Agent Prompt:

```
**IMPORTANT:** 
- NEVER report "ok" without verification
- ALWAYS test functionality, not just status
- ALWAYS show evidence of working
- FAIL if verification fails
```

### In Every Heartbeat:

```
- Check health → Get status
- Test functionality → Verify works
- Check data integrity → Verify data
- Report VERIFIED or FAILED
```

---

## Implementation Plan

### Phase 1: Update Test Scripts (Today)
1. Create verified test script
2. Run against all services
3. Fix any failures

### Phase 2: Update Heartbeat (This Week)
1. Add verification to heartbeat
2. Add integrity checks
3. Add detailed reporting

### Phase 3: Update Agents (This Week)
1. Add verification to agent prompts
2. Add verification to agent outputs
3. Add verification to agent reports

### Phase 4: Enforcement (Ongoing)
1. Reject unverified reports
2. Require evidence
3. Track verification rate

---

## Expected Outcome

**Before:**
```
Tests: 20
Silent OK: 15 (75%)
Verified: 5 (25%)
Trust: LOW
```

**After:**
```
Tests: 20
Silent OK: 0 (0%)
Verified: 20 (100%)
Trust: HIGH
```

---

*Created: March 19, 2026*
*Type: No silent returns policy*
*Goal: 100% verification, 0% silent OK*
