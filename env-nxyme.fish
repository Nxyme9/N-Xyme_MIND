# Fish shell environment setup for N-Xyme
# Save as: ~/.config/fish/env-nxyme.fish
# Add to ~/.config/fish/config.fish: source ~/N-Xyme_CODE/N-Xyme_MIND/env-nxyme.fish

# Core paths
set -gx NX_MIND_ROOT (dirname (status --current-filename))
set -gx PATH $NX_MIND_ROOT/bin $PATH

# Python venv (disable wrapper to avoid issues)
set -gx VIRTUAL_ENV_DISABLE_PROMPT 1
set -gx VIRTUAL_ENV "$NX_MIND_ROOT/.venv"
set -a fish_user_paths "$VIRTUAL_ENV/bin"

# Python paths
set -gx PYTHONPATH "$NX_MIND_ROOT:$NX_MIND_ROOT/src"

# GGUF llama-server (direct, no Ollama)
set -gx GGUF_HOST "http://localhost:8088"
set -gx GGUF_MODEL "qwen2.5-0.5b-instruct-q4_k_m"

# CUDA (if available)
if test -d /opt/cuda
    set -gx CUDA_PATH /opt/cuda
    set -gx CUDA_DISABLE_PERF_BOOST 1
    set -a fish_user_paths /opt/cuda/bin
end

# Model Router
set -gx MODEL_ROUTER_API_KEY ""

# npm cache
set -gx npm_config_cache "$NX_MIND_ROOT/.cache/npm"

# VPN config
set -gx VPN_ENABLED true
set -gx VPN_BACKENDS_CONFIG "configs/vpn/backends.json"

# Local routing (GGUF direct, no Ollama)
set -gx LOCAL_ROUTING_ENABLED true
set -gx LOCAL_QUALITY_THRESHOLD 0.7
set -gx LOCAL_TIMEOUT_SECONDS 30
set -gx CLOUD_ESCALATION_MODE auto
set -gx ROUTING_METRICS_ENABLED true
set -gx LOCAL_MODEL_POOL "qwen2.5-0.5b-instruct-q4_k_m,qwen2.5-coder-7b-q4_k_m"

# Auto-start N-Xyme Router Proxy
if test -f "$NX_MIND_ROOT/bin/auto-start-proxy.sh"
    bash "$NX_MIND_ROOT/bin/auto-start-proxy.sh"
end
