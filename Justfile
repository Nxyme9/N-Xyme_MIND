# nx-agents command runner
# ──────────────────────────────────────────

# Build all workspace members in release mode
build:
    cargo build --release --workspace

# Build all in debug mode (faster iteration)
build-debug:
    cargo build --workspace

# Build only the MCP server
build-mcp:
    cargo build --release -p nx_agents

# Run all tests
test:
    cargo test --workspace

# Run tests with output
test-verbose:
    cargo test --workspace -- --nocapture

# Format check (no changes)
fmt:
    cargo fmt --all --check

# Auto-fix formatting
fmt-fix:
    cargo fmt --all

# Lint check (deny warnings)
lint:
    cargo clippy --workspace -- -D warnings

# Lint with all pedantic warnings
lint-pedantic:
    cargo clippy --workspace -- -W clippy::pedantic

# Security audit
audit:
    cargo audit

# Run all quality gates (format → lint → test → audit)
quality-gates: fmt lint test audit

# Fix common issues (format + clippy auto-fix)
fix:
    cargo fix --workspace --allow-dirty
    cargo fmt --all

# Clean all build artifacts
clean:
    cargo clean

# Copy release binaries to bins/
bins:
    mkdir -p bins
    cp target/release/nx_agents bins/
    cp target/release/jailbreak-cli bins/
    @echo "Binaries copied to bins/"

# Install the MCP server binary
install: build
    cp target/release/nx_agents bins/
    @echo "nx_agents installed to bins/"

# Watch mode (requires cargo-watch)
dev:
    cargo watch -x 'build --workspace'

# Show available targets
default:
    @just --list

# Launch opencode with agent-specific toolset
opencode *args:
    @if [ -z "{{ args }}" ]; then \
        bins/nx; \
    else \
        bins/nx {{ args }}; \
    fi

# ──────────────────────────────────────────
# TokenGuard — Token quota monitor
# ──────────────────────────────────────────

# One-shot token quota check
token-check:
    python3 services/token-guard/src/token_guard.py --check

# Show token quota status
token-status:
    python3 services/token-guard/src/token_guard.py --status

# Run TokenGuard as daemon
token-daemon interval="30":
    python3 services/token-guard/src/token_guard.py --daemon --interval {{ interval }}

# Reset daily token counters
token-reset:
    python3 services/token-guard/src/token_guard.py --reset

# Manually trigger IP rotation
token-rotate:
    python3 services/token-guard/src/token_guard.py --rotate

# Start all services including TokenGuard
start-services:
    bash scripts/start-services.sh

# ──────────────────────────────────────────
# LSP Auto-Diagnose — LSP server health monitor
# ──────────────────────────────────────────

# Show LSP server status (table format)
lsp-status:
    python3 plugins/lsp-auto-diagnose/diagnose.py status

# Run full LSP diagnosis (JSON output)
lsp-diagnose:
    python3 plugins/lsp-auto-diagnose/diagnose.py check

# Start LSP health monitor as background daemon
lsp-monitor:
    python3 plugins/lsp-auto-diagnose/diagnose.py daemon

# ──────────────────────────────────────────
# Session Digest — Session log summarizer
# ──────────────────────────────────────────

# Generate digests for all sessions
digest:
    python3 plugins/session-digest/generator.py

# Generate digest for the latest session only
digest-latest:
    python3 plugins/session-digest/generator.py --latest

# ──────────────────────────────────────────
# Session Finder — List/search session history
# ──────────────────────────────────────────

# List recent sessions
session:
    scripts/find-session.sh

# Search sessions by keyword: just session-find "agent"
session-find query:
    scripts/find-session.sh "{{query}}"

# Get session content: just session-content <id>
session-content id:
    scripts/find-session.sh --content "{{id}}"
