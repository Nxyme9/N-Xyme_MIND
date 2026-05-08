# Contributing to N-Xyme MIND

## Welcome

N-Xyme MIND is a personal AI coding workspace. We welcome contributions from developers who want to learn, build, and improve AI orchestration systems.

## Quick Start

```bash
git clone https://github.com/yourusername/N-Xyme_MIND.git
cd N-Xyme_MIND
source env.sh
bash n-xyme-mind.sh
```

## Development Setup

### Prerequisites
- Python 3.10+
- CUDA-capable GPU (for local LLM)
- 16GB+ RAM

### Environment
1. Copy `.env.example` to `.env` and configure
2. Run `bash bootstrap.sh` for fresh setup
3. Verify with `bash bin/health-l0-blink.sh`

## Making Changes

### 1. Fork and Branch
```bash
git checkout -b feature/your-feature
```

### 2. Code Standards
- Python: Follow PEP 8, use type hints
- Use `lsp_diagnostics` before committing
- Run quality gates: `bash bin/quality-gates/gate-1-typecheck.sh`

### 3. Testing
```bash
# Run tests
pytest

# Health checks
bash bin/health-l1-pulse.sh
```

### 4. Commit Messages
- Use clear, descriptive messages
- Reference issues: "Fixes #123"
- Example: "Add local_llm fallback trigger"

## Pull Request Process

1. **Before submitting:**
   - Run all health checks
   - Ensure typecheck + lint pass
   - Update docs if needed

2. **PR Description:**
   - What does this change?
   - Why is it needed?
   - How was it tested?

3. **Review criteria:**
   - Code quality
   - Tests pass
   - No security issues
   - Documentation updated

## Areas to Contribute

- **Agent orchestration** - Improve agent loops, triggers
- **Local LLM** - Rosetta, GGUF optimization, tool calling
- **Memory systems** - Vector stores, retrieval, cognitive processes
- **Infrastructure** - Proxy, health monitoring, VPN rotation
- **Documentation** - Improve guides, examples

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow

## Getting Help

- Open an issue for bugs/features
- Discussions for questions
- Discord for real-time chat

---

Thank you for contributing!