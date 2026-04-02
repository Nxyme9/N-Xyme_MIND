# Troubleshooting

## MCP Connection Failed

**Symptom**: MCP shows "disconnected" in OpenCode TUI

**Fix**:
```bash
# Check if binary exists
which mcp-server-sequential-thinking

# Test MCP directly
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0.0"}}}' | mcp-server-sequential-thinking
```

## Python Venv Broken

**Symptom**: `import athena` fails

**Fix**:
```bash
rm -rf venvs/athena
uv venv venvs/athena --python python3
uv pip install -e "athena[all]" --python venvs/athena/bin/python
```

## Ollama Not Running

**Symptom**: athena/hindsight MCPs fail

**Fix**:
```bash
ollama serve &
sleep 3
curl http://localhost:11434/api/tags
```

## Config Invalid

**Symptom**: OpenCode won't start

**Fix**:
```bash
python3 -m json.tool opencode.json
# Fix JSON errors, then:
cp opencode.json .opencode/opencode.json
```

## Hardcoded Paths

**Symptom**: Files reference /home/nxyme/nx_openmore

**Fix**:
```bash
grep -rn "/home/nxyme/nx_openmore" . --include="*.py" | head -10
sed -i 's|/home/nxyme/nx_openmore|.|g' <file>
```
