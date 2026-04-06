# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-04-04

### Added
- Portable OMO platform - clone to any machine, run bootstrap, it works
- Bootstrap.sh creates all required directories including `.context/memory_bank/` and `.context/memory_graph/`
- MetricsStore with environment-based path resolution (`METRICS_DB_PATH` env var)
- Metrics-memory bridge integration (`src/integrations/metrics_memory_bridge.py`)
- Memory bank files seeded with valid frontmatter and content
- Agent definitions copied to project `oh-my-opencode.json`
- Phase 0 pre-flight checks (mandatory before any work)
- 13-point industry gold standard audit suite

### Fixed
- Replaced all hardcoded `/home/nxyme` paths with `Path(__file__)` + env vars
- Fixed command injection vulnerability in `src/auto_launcher.py` (shell=True → shell=False with validation)
- Fixed path portability in modelrouter/ (uses `$HOME` instead of hardcoded paths)
- Fixed MCP imports - all packages import correctly
- Fixed venv paths in opencode.json to use relative paths
- Fixed AGENTS.md model names (updated to opencode/qwen3.6-plus-free)
- Fixed bootstrap.sh --clear flag for fresh venv creation

### Security
- Command injection fix: validated config["cmd"] before subprocess execution
- Path traversal protection in MetricsStore
- No hardcoded secrets in source code
- Environment variable based configuration for all sensitive values

### Architecture
- Clean separation: MetricsStore (SQLite) → Bridge → Memory Bank files
- Environment-based configuration (no hardcoded paths)
- Memory bank files follow valid frontmatter + markdown pattern
- Bridge provides dual-write to both metrics DB and context files
