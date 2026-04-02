# MASTER DELEGATION PROMPT: Hindsight Local Memory System

> **Use this prompt with Sisyphus or any executor to implement Hindsight in parallel.**
> Copy-paste the entire prompt. Each wave runs concurrently. Dependencies are explicit.

---

## CONTEXT

We are implementing **Hindsight** — the bleeding-edge AI agent memory system (91.4% LongMemEval, self-contained, Ollama native) in `/home/nxyme/nx_openmore/`.

**What we have:**
- Ollama running on port 11434 (8 models including qwen2.5:14b, nomic-embed-text 768 dims)
- Python 3.14 venv at `/home/nxyme/nx_openmore/athena/.venv/`
- OpenCode config at `/home/nxyme/nx_openmore/config/opencode.json` (uses `"mcp"` key)
- Neo4j installed but NOT needed for Hindsight

**What we need:**
1. Install `hindsight-all` in Athena venv
2. Configure Hindsight to use Ollama (no API keys)
3. Start Hindsight server on port 8888
4. Test retain → recall → reflect pipeline
5. Add MCP server to OpenCode config
6. Verify full integration

---

## EXECUTION INSTRUCTIONS

Run ALL tasks in **Wave 1** simultaneously. Wait for ALL to complete. Then run **Wave 2**. Then **Wave 3**. Each wave depends on the previous.

Mark each task as `in_progress` when starting, `completed` when done, `failed` if errors.

---

## WAVE 1: Foundation (All Parallel — No Dependencies)

### Task 1.1: Dry-run pip install
```
Command: cd /home/nxyme/nx_openmore && ./athena/.venv/bin/pip install --dry-run hindsight-all
Expected: Shows package list with no conflicts
On failure: Report Python version incompatibility, try `hindsight-api` instead
```

### Task 1.2: Check Ollama models
```
Command: curl -s http://localhost:11434/api/tags | python3 -c "import sys,json; [print(m['name']) for m in json.load(sys.stdin)['models']]"
Expected: Lists 8 models including qwen2.5:14b and nomic-embed-text:latest
On failure: Report which models are missing
```

### Task 1.3: Check OpenCode config structure
```
Command: python3 -c "import json; c=json.load(open('/home/nxyme/nx_openmore/config/opencode.json')); print('mcp' in c, list(c.get('mcp',{}).keys()))"
Expected: True ['existing-mcp-servers...']
On failure: Report config structure
```

### Task 1.4: Check available disk space
```
Command: df -h /home/nxyme/nx_openmore | tail -1 | awk '{print $4}'
Expected: >10GB free (hindsight-all is ~9GB with all deps)
On failure: Report available space
```

### Task 1.5: Check port 8888 availability
```
Command: ss -tlnp | grep 8888 || echo "PORT_FREE"
Expected: PORT_FREE
On failure: Report what's using port 8888, suggest alternative
```

---

## WAVE 2: Installation (After Wave 1 Passes)

### Task 2.1: Install hindsight-all
```
Command: cd /home/nxyme/nx_openmore && ./athena/.venv/bin/pip install hindsight-all --timeout 300
Timeout: 300s
Expected: Successfully installed hindsight-all-X.X.X
On failure: Try `hindsight-api` (slim) or `hindsight-all-slim`
```

### Task 2.2: Verify Python imports
```
Command: cd /home/nxyme/nx_openmore && ./athena/.venv/bin/python -c "from hindsight import HindsightServer; from hindsight_client import Hindsight; print('ALL IMPORTS OK')"
Expected: ALL IMPORTS OK
On failure: Report missing modules
```

### Task 2.3: Verify CLI commands exist
```
Command: cd /home/nxyme/nx_openmore && ./athena/.venv/bin/hindsight-api --help 2>&1 | head -5
Expected: Shows help text
On failure: Report command not found
```

---

## WAVE 3: Configuration (After Wave 2 Passes)

### Task 3.1: Create Hindsight config
```
Command: |
  cat > /home/nxyme/nx_openmore/.hindsight.env << 'EOF'
HINDSIGHT_API_LLM_PROVIDER=ollama
HINDSIGHT_API_LLM_MODEL=qwen2.5:14b
HINDSIGHT_API_LLM_BASE_URL=http://localhost:11434/v1
HINDSIGHT_API_LLM_API_KEY=ollama
HINDSIGHT_API_EMBEDDING_PROVIDER=ollama
HINDSIGHT_API_EMBEDDING_MODEL=nomic-embed-text:latest
HINDSIGHT_API_EMBEDDING_BASE_URL=http://localhost:11434/v1
HINDSIGHT_API_EMBEDDING_API_KEY=ollama
HINDSIGHT_API_PORT=8888
EOF
  echo "CONFIG_CREATED"
Expected: CONFIG_CREATED
On failure: Report write error
```

### Task 3.2: Start Hindsight server (background)
```
Command: |
  cd /home/nxyme/nx_openmore
  source .hindsight.env
  export $(cut -d= -f1 .hindsight.env)
  nohup ./athena/.venv/bin/hindsight-api > /tmp/hindsight.log 2>&1 &
  echo $! > /tmp/hindsight.pid
  sleep 5
  curl -s http://localhost:8888/health || echo "SERVER_NOT_READY"
Timeout: 30s
Expected: JSON health response or SERVER_NOT_READY
On failure: Check /tmp/hindsight.log for errors
```

### Task 3.3: Add MCP server to OpenCode config
```
Command: |
  python3 << 'PYEOF'
  import json
  config_path = "/home/nxyme/nx_openmore/config/opencode.json"
  with open(config_path) as f:
      config = json.load(f)
  
  config.setdefault("mcp", {})["hindsight-memory"] = {
      "type": "local",
      "command": ["uvx", "--from", "hindsight-api", "hindsight-local-mcp"],
      "environment": {
          "HINDSIGHT_API_LLM_PROVIDER": "ollama",
          "HINDSIGHT_API_LLM_MODEL": "qwen2.5:14b",
          "HINDSIGHT_API_LLM_BASE_URL": "http://localhost:11434/v1",
          "HINDSIGHT_API_LLM_API_KEY": "ollama",
          "HINDSIGHT_LOCAL_MCP_PORT": "8889",
      },
      "enabled": True,
  }
  
  with open(config_path, "w") as f:
      json.dump(config, f, indent=2)
  print("MCP_CONFIGURED")
  PYEOF
Expected: MCP_CONFIGURED
On failure: Report JSON error
```

---

## WAVE 4: Testing (After Wave 3 Passes)

### Task 4.1: Test retain
```
Command: |
  cd /home/nxyme/nx_openmore
  ./athena/.venv/bin/python << 'PYEOF'
  from hindsight_client import Hindsight
  c = Hindsight("http://localhost:8888")
  c.retain("test-bank", "I prefer functional programming over object-oriented programming")
  print("RETAIN_OK")
  PYEOF
Expected: RETAIN_OK
On failure: Report connection error or API error
```

### Task 4.2: Test recall
```
Command: |
  cd /home/nxyme/nx_openmore
  sleep 3  # Wait for indexing
  ./athena/.venv/bin/python << 'PYEOF'
  from hindsight_client import Hindsight
  c = Hindsight("http://localhost:8888")
  results = c.recall("test-bank", "What programming style do I prefer?")
  print(f"RECALL_RESULTS: {len(results)}")
  assert len(results) > 0, "No results found!"
  print("RECALL_OK")
  PYEOF
Expected: RECALL_RESULTS: >= 1\nRECALL_OK
On failure: Report empty results or connection error
```

### Task 4.3: Test reflect
```
Command: |
  cd /home/nxyme/nx_openmore
  ./athena/.venv/bin/python << 'PYEOF'
  from hindsight_client import Hindsight
  c = Hindsight("http://localhost:8888")
  result = c.reflect("test-bank", "What do I care about in my programming preferences?")
  print(f"REFLECT_RESULT: {result[:200]}")
  print("REFLECT_OK")
  PYEOF
Timeout: 60s
Expected: REFLECT_RESULT: <some text>\nREFLECT_OK
On failure: Report timeout or API error (reflect needs tool-calling support)
```

### Task 4.4: Test real knowledge store
```
Command: |
  cd /home/nxyme/nx_openmore
  ./athena/.venv/bin/python << 'PYEOF'
  from hindsight_client import Hindsight
  c = Hindsight("http://localhost:8888")
  
  facts = [
      "I use Ollama with nomic-embed-text for 768 dimension embeddings",
      "My system runs CachyOS Linux with 30GB RAM",
      "I prefer bleeding edge local-first tools over cloud services",
      "Neo4j crashed 4 times in previous projects, now using Hindsight",
      "I have 8 Ollama models including qwen2.5:14b and granite3.2:8b",
  ]
  
  for fact in facts:
      c.retain("nxyme", fact)
  
  # Test recall
  r = c.recall("nxyme", "What embedding model do I use?")
  print(f"Knowledge recall: {len(r)} results")
  
  r2 = c.recall("nxyme", "What OS do I run?")
  print(f"OS recall: {len(r2)} results")
  
  assert len(r) > 0 and len(r2) > 0, "Knowledge recall failed!"
  print("KNOWLEDGE_STORE_OK")
  PYEOF
Expected: Knowledge recall: >= 1\nOS recall: >= 1\nKNOWLEDGE_STORE_OK
On failure: Report which recall failed
```

---

## WAVE 5: Final Verification (After Wave 4 Passes)

### Task 5.1: Verify MCP tools
```
Command: |
  python3 -c "
  import json
  c = json.load(open('/home/nxyme/nx_openmore/config/opencode.json'))
  assert 'hindsight-memory' in c.get('mcp', {}), 'MCP not configured!'
  mcp = c['mcp']['hindsight-memory']
  assert mcp['enabled'] == True, 'MCP not enabled!'
  assert 'ollama' in str(mcp['environment']), 'Ollama not configured!'
  print('MCP_VERIFIED')
  "
Expected: MCP_VERIFIED
On failure: Report config issue
```

### Task 5.2: Verify server health
```
Command: curl -s http://localhost:8888/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Status: {d.get(\"status\",\"unknown\")}')"
Expected: Status: healthy (or similar)
On failure: Report server not responding
```

### Task 5.3: Count memory banks
```
Command: |
  cd /home/nxyme/nx_openmore
  ./athena/.venv/bin/python << 'PYEOF'
  from hindsight_client import Hindsight
  c = Hindsight("http://localhost:8888")
  banks = c.list_banks()
  print(f"Banks: {len(banks)}")
  for b in banks:
      print(f"  - {b}")
  PYEOF
Expected: Banks: >= 2 (test-bank, nxyme)
On failure: Report no banks found
```

---

## ERROR HANDLING

If ANY task fails:
1. Log the error to `/tmp/hindsight-setup-error.log`
2. Mark task as `failed`
3. Continue with other parallel tasks (don't block)
4. After wave completes, report all failures
5. Retry failed tasks once after checking error

## COMPLETION CRITERIA

ALL of these must be true:
- [ ] `hindsight-all` installed in venv
- [ ] Server running on port 8888
- [ ] Retain stores facts
- [ ] Recall retrieves facts
- [ ] Reflect generates reasoning (or gracefully reports model limitation)
- [ ] MCP configured in opencode.json
- [ ] At least 2 memory banks exist (test-bank, nxyme)

## ROLLBACK

If Hindsight fails to install or run:
1. `./athena/.venv/bin/pip uninstall hindsight-all`
2. Remove MCP entry from opencode.json
3. Kill server: `kill $(cat /tmp/hindsight.pid) 2>/dev/null`
4. Report: "Hindsight failed, falling back to Graphiti plan at .sisyphus/plans/neo4j-graphiti-setup.md"
