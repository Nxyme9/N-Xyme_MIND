# Updating Athena

Athena is designed so **your data and the framework are separate layers**. Updating the framework doesn't touch your personal data.

## If You Forked (Recommended)

```bash
# One-time setup: add the original repo as upstream
git remote add upstream https://github.com/winstonkoh87/Athena-Public.git

# To update:
git fetch upstream
git merge upstream/main
pip install -e .   # Only if pyproject.toml changed
```

## If You Cloned Directly

```bash
git pull origin main
pip install -e .   # Only if pyproject.toml changed
```

## What Gets Updated vs What Doesn't

| Layer | Updated? | Examples |
|:------|:--------:|:--------|
| **Framework** | ✅ Yes | `src/athena/`, `examples/protocols/`, `scripts/`, `docs/` |
| **Your Data** | ❌ No | `.context/memory_bank/`, `.context/memories/`, `.agent/` |
| **Config** | ⚠️ Check | `.env` — compare with `.env.example` for new variables |

> [!IMPORTANT]
> **Privacy**: If you fork, your `.context/` folder (memory bank, session logs, personal profile) will be visible in your fork. **Keep your fork private** if it contains personal data, or add `.context/` to your fork's `.gitignore`.
