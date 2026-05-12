# Local LLM Layer

## Overview

The Local LLM Layer provides high-performance local GGUF inference. It implements a custom inference engine (frankenstein_engine) that outperforms Ollama by 14x with real tool calling capability. Supports single port 8080 for all requests, true parallel execution, and GPU acceleration.

## Public API

```python
from packages.local_llm import LocalLLM, execute_with_tools

# Direct LLM access
llm = LocalLLM()
result = llm.complete("Hello, how are you?")

# Tool calling execution
result = execute_with_tools(prompt="What is the weather?", tools=[...])
```

## Architecture

### Core Modules

| Module | Purpose | Key Classes | Key Functions |
|--------|---------|-------------|---------------|
| brain.py | Core brain wrapper | Brain | complete(), chat(), embed(), get_status() |
| wrapper.py | Tool execution wrapper | execute_with_tools() | - |
| ollama_client.py | Ollama API client | OllamaClient | chat(), complete(), embed() |
| llama_server.py | Llama.cpp server | LlamaServer | start(), stop(), predict() |
| gguf_mcp_server.py | MCP server for GGUF | GGUFMCPServer | handle_request() |
| mcp_tool_loader.py | Tool loading | MCPToolLoader | load_tools() |
| rosetta_executor.py | Tool translation | RosettaExecutor | translate() |
| model_router.py | Model selection | ModelRouter | route() |
| caching.py | Response caching | Cache | get(), set() |
| monitoring.py | Performance monitoring | Monitor | record(), stats() |

### Integration Modules

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| integration.py | General integration | - |
| rosetta_integration.py | Rosetta integration | - |
| direct_pipeline.py | Direct inference pipeline | - |

### Benchmark Modules

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| gguf_benchmark.py | GGUF benchmarks | - |
| benchmark_rosetta.py | Rosetta benchmarks | - |

### Utility Modules

| Module | Purpose | Key Classes |
|--------|---------|-------------|
| rag_injector.py | RAG context injection | - |
| rosetta_preloader.py | Rosetta model preloader | - |
| kv_cache_persistence.py | KV cache persistence | - |
| tool_validator.py | Tool validation | - |
| error_recovery.py | Error handling | - |

## Components

### Brain (brain.py)

- **Purpose**: Unified API for local GGUF inference
- **Key Methods**:
  - `complete()`: Text completion
  - `chat()`: Chat completion with message history
  - `embed()`: Generate embeddings
  - `get_status()`: Get brain status
- **Features**:
  - Model pool management (lazy load, auto-unload)
  - VRAM management (1GB headroom)
  - Tool calling support

### Model Configuration

- **Model Aliases**:
  - `7b`, `default`, `qwen`: DEFAULT_MODEL
  - `0.5b`, `fast`, `rosetta`: ROSETTA_MODEL
  - `embed`, `embedding`, `nomic`: EMBED_MODEL
- **Default Settings**:
  - DEFAULT_N_CTX: 4096
  - LARGE_N_CTX: 131072
  - DEFAULT_N_GPU_LAYERS: -1 (all to GPU)
  - DEFAULT_TIMEOUT_SECS: 60
  - UNLOAD_TIMEOUT_SECS: 60

### Ollama Client

- **Purpose**: Direct Ollama API client with tool calling support
- **Key Methods**:
  - `chat()`: Chat completion
  - `complete()`: Text completion
  - `embed()`: Generate embeddings
- **Supports**: Tool calling during streaming

### GGUF MCP Server

- **Purpose**: MCP server for GGUF inference
- **Features**:
  - Single port 8080
  - Tool calling support
  - Continuous batching

### Rosetta Executor

- **Purpose**: Translate between tool formats
- **Used for**: Tool calling with GGUF models

### Model Router

- **Purpose**: Select optimal model for task
- **Factors**: Task type, latency requirements, VRAM availability

## Performance

| Model | Tokens/sec | GPU Util | Power |
|-------|------------|----------|-------|
| 0.5b (Qwen) | 1,341+ | 96% | 346W |
| 7b (Qwen) | 471 | 96% | ~400W |

### Benchmark Results

- **14x faster** than Ollama
- **6.4x lower** latency
- True parallel: 8-16 concurrent slots with continuous batching

## Relationships

- **Depends on**: frankenstein_engine (custom inference)
- **Used by**: orchestration (agent inference), intelligence (routing), MCP servers

## Notes

- Uses llama.cpp with bleeding-edge optimization flags
- Supports flash attention, KV cache quantization
- GPU optimization: -ngl 99, --flash-attn on, -ctk q4_0 -ctv q4_0
- Start with: `bash start_llama_server.sh`
- Manage with: `./gguf_manager.sh start/stop/switch`