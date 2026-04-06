# Fish shell environment for N-Xyme_MIND
# Source this file: source ./env.fish

# Get script directory
set -gx NX_MIND_ROOT (dirname (status --current-filename))

# Python venv - check both locations
if test -d "$NX_MIND_ROOT/venv"
    set -gx VIRTUAL_ENV "$NX_MIND_ROOT/venv"
else if test -d "$NX_MIND_ROOT/.venv"
    set -gx VIRTUAL_ENV "$NX_MIND_ROOT/.venv"
else if test -d "$NX_MIND_ROOT/venvs/athena"
    set -gx VIRTUAL_ENV "$NX_MIND_ROOT/venvs/athena"
end

# Add venv to PATH
set -gx PATH "$VIRTUAL_ENV/bin" $PATH

# PYTHONPATH
set -gx PYTHONPATH "$NX_MIND_ROOT/src:$NX_MIND_ROOT/athena/src:$NX_MIND_ROOT"

# Ollama
set -gx OLLAMA_MODELS "$NX_MIND_ROOT/.ollama/models"

# npm cache
set -gx npm_config_cache "$NX_MIND_ROOT/.cache/npm"

# Load .env if exists
if test -f "$NX_MIND_ROOT/.env"
    # Fish doesn't have bash's source - use set -a pattern
    while read -l line
        if test (string match -r '^[A-Za-z_][A-Za-z0-9_]*=' "$line")
            set -gx $line
        end
    end < "$NX_MIND_ROOT/.env"
end
