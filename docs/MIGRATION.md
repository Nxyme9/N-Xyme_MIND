# Model Configuration Migration Guide

## Overview

This document describes the migration from hardcoded model identifiers to environment variable-based configuration. This enables flexible model switching across the entire N-Xyme MIND workspace without modifying script code.

### What Changed

- **Before**: Model names were hardcoded directly in scripts (e.g., `"llama3.2:3b"`)
- **After**: Models are loaded from environment variables with fallback defaults (e.g., `os.getenv("OLLAMA_MODEL", "llama3.2:3b")`)

### Why This Matters

1. **Single point of change**: Update models in one place (`env.sh`) rather than across 20+ files
2. **Environment-specific configs**: Different models for dev/staging/prod
3. **Easy A/B testing**: Swap models by changing env vars
4. **Security**: No API keys exposed in code

---

## Environment Variables

All model configuration is centralized in `env.sh`. The following 5 environment variables are available:

| Variable | Default | Purpose |
|----------|---------|---------|
| `OLLAMA_MODEL` | `llama3.2:3b` | Local Ollama general-purpose model |
| `DEFAULT_CODING_MODEL` | `qwen2.5-coder:7b` | Code generation tasks |
| `PRIMARY_MODEL` | `opencode/qwen3.6-plus-free` | Primary cloud model |
| `FALLBACK_MODEL` | `opencode/minimax-m2.5-free` | Retry/fallback cloud model |
| `OFFLINE_MODEL` | `ollama/llama3.2:3b` | Disconnected operation |

To override defaults, edit `env.sh` or set variables in `.env`:

```bash
# In .env
OLLAMA_MODEL=llama3.1:8b
DEFAULT_CODING_MODEL=qwen2.5-coder:14b
```

---

## Before/After Examples

### 1. test_max_parallelism.py

**Before (hardcoded):**
```python
model="llama3.2:3b"
```

**After (env var):**
```python
model=os.getenv("OLLAMA_MODEL", "llama3.2:3b")
```

---

### 2. utilization-worker.py

**Before (hardcoded):**
```python
GPU_MODELS = {
    "fast": {
        "name": "llama3.2:3b-instruct-q4_K_M",
    },
    "coding": {"name": "qwen2.5-coder:7b"},
}
```

**After (env var):**
```python
GPU_MODELS = {
    "fast": {
        "name": "llama3.2:3b-instruct-q4_K_M",
    },
    "coding": {"name": os.getenv("DEFAULT_CODING_MODEL", "qwen2.5-coder:7b")},
}
```

---

### 3. optimize-prompts.py

**Before (hardcoded):**
```python
resp = requests.post(
    f"{OLLAMA_URL}/api/generate",
    json={
        "model": "qwen2.5-coder:7b",
    },
)
```

**After (env var):**
```python
resp = requests.post(
    f"{OLLAMA_URL}/api/generate",
    json={
        "model": os.getenv("DEFAULT_CODING_MODEL", "qwen2.5-coder:7b"),
    },
)
```

---

### 4. extract-patterns-v2.py

**Before (hardcoded):**
```python
MODEL = "qwen2.5-coder:7b"
```

**After (env var):**
```python
MODEL = os.getenv("DEFAULT_CODING_MODEL", "qwen2.5-coder:7b")
```

---

### 5. gpu-optimizer.py

**Before (hardcoded):**
```python
MODELS = {
    "coding": {"name": "qwen2.5-coder:7b"},
    "general": {"name": "llama3.1:8b"},
    "heartbeat": {"name": "llama3.2:3b-instruct-q4_K_M"},
}
```

**After (env var):**
```python
MODELS = {
    "coding": {"name": os.getenv("DEFAULT_CODING_MODEL", "qwen2.5-coder:7b")},
    "general": {"name": os.getenv("OLLAMA_MODEL", "llama3.1:8b")},
    "heartbeat": {"name": os.getenv("OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M")},
}
```

---

### 6. trust-switcher.py

**Before (hardcoded):**
```python
MODEL_CAPABILITIES = {
    "llama3.2:3b-instruct-q4_K_M": {...},
    "qwen2.5-coder:7b": {...},
    "deepseek-r1:14b": {...},
}
```

**After (env var):**
```python
MODEL_CAPABILITIES = {
    os.getenv("OLLAMA_MODEL", "llama3.2:3b-instruct-q4_K_M"): {...},
    os.getenv("DEFAULT_CODING_MODEL", "qwen2.5-coder:7b"): {...},
    os.getenv("PRIMARY_MODEL", "deepseek-r1:14b"): {...},
}
```

---

## Migration Steps

### For Your Own Scripts

1. **Identify hardcoded model names** in your script:
   ```bash
   grep -n '"llama3\.' scripts/*.py
   grep -n '"qwen2\.5' scripts/*.py
   ```

2. **Replace each hardcoded model** with env var pattern:
   ```python
   # Replace: "llama3.2:3b"
   # With:   os.getenv("OLLAMA_MODEL", "llama3.2:3b")
   
   # Replace: "qwen2.5-coder:7b"
   # With:   os.getenv("DEFAULT_CODING_MODEL", "qwen2.5-coder:7b")
   
   # Replace: "deepseek-r1:14b" (or similar reasoning model)
   # With:   os.getenv("PRIMARY_MODEL", "deepseek-r1:14b")
   
   # Replace: "qwen3:8b" (or similar fallback)
   # With:   os.getenv("FALLBACK_MODEL", "qwen3:8b")
   ```

3. **Add import** if not present:
   ```python
   import os
   ```

4. **Test the migration** (see Testing section below)

---

## Testing

### Verify Environment Variables Loaded

```bash
source env.sh
echo $OLLAMA_MODEL        # Should output: llama3.2:3b
echo $DEFAULT_CODING_MODEL  # Should output: qwen2.5-coder:7b
echo $PRIMARY_MODEL       # Should output: opencode/qwen3.6-plus-free
```

### Test Model Config Script

```bash
source env.sh
python3 bin/model_config.py
```

Expected output:
```json
{
  "OLLAMA_MODEL": "llama3.2:3b",
  "DEFAULT_CODING_MODEL": "qwen2.5-coder:7b",
  "PRIMARY_MODEL": "opencode/qwen3.6-plus-free",
  "FALLBACK_MODEL": "opencode/minimax-m2.5-free",
  "OFFLINE_MODEL": "ollama/llama3.2:3b"
}
```

### Run Health Check

```bash
source env.sh
bash bin/health-check.sh
```

Expected: All model configuration checks pass with green checkmarks.

### Quick Smoke Test

```bash
# Test that scripts pick up env vars correctly
source env.sh
python3 -c "
import os
print('OLLAMA_MODEL:', os.getenv('OLLAMA_MODEL', 'NOT_SET'))
print('DEFAULT_CODING_MODEL:', os.getenv('DEFAULT_CODING_MODEL', 'NOT_SET'))
"
```

---

## Rollback

If you need to revert to hardcoded values:

### Option 1: Comment Out env.sh Variables

```bash
# In env.sh, comment the model variables:
# set -gx OLLAMA_MODEL "llama3.2:3b" 2>/dev/null || export OLLAMA_MODEL="llama3.2:3b" 2>/dev/null
```

### Option 2: Revert Script Changes

Each script maintains the **fallback default** in the `os.getenv()` call. Even without env vars set, scripts will work using the hardcoded fallback:

```python
# This always works, even without env.sh
model = os.getenv("OLLAMA_MODEL", "llama3.2:3b")  # Falls back to llama3.2:3b
```

### Option 3: Full Revert

To completely remove env var usage, replace all:
```python
os.getenv("OLLAMA_MODEL", "llama3.2:3b")  →  "llama3.2:3b"
os.getenv("DEFAULT_CODING_MODEL", "qwen2.5-coder:7b")  →  "qwen2.5-coder:7b"
```

---

## Files Modified

| File | Status |
|------|--------|
| `bin/model_config.py` | Created (central config loader) |
| `bin/health-check.sh` | Updated (model config checks) |
| `env.sh` | Updated (5 new env vars) |
| `scripts/test_max_parallelism.py` | Migrated |
| `scripts/utilization-worker.py` | Migrated |
| `scripts/optimize-prompts.py` | Migrated |
| `scripts/extract-patterns-v2.py` | Migrated |
| `scripts/gpu-optimizer.py` | Migrated |
| `scripts/trust-switcher.py` | Migrated |

---

## Pattern Reference

| Model Type | Environment Variable | Fallback Default |
|------------|---------------------|------------------|
| General/Ollama | `OLLAMA_MODEL` | `llama3.2:3b` |
| Coding | `DEFAULT_CODING_MODEL` | `qwen2.5-coder:7b` |
| Primary cloud | `PRIMARY_MODEL` | `opencode/qwen3.6-plus-free` |
| Fallback cloud | `FALLBACK_MODEL` | `opencode/minimax-m2.5-free` |
| Offline | `OFFLINE_MODEL` | `ollama/llama3.2:3b` |

### Quick Reference Snippet

```python
import os

# Add at top of your script
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
DEFAULT_CODING_MODEL = os.getenv("DEFAULT_CODING_MODEL", "qwen2.5-coder:7b")
PRIMARY_MODEL = os.getenv("PRIMARY_MODEL", "opencode/qwen3.6-plus-free")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "opencode/minimax-m2.5-free")
OFFLINE_MODEL = os.getenv("OFFLINE_MODEL", "ollama/llama3.2:3b")
```