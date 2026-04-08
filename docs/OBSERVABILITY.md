# Langfuse Observability Setup

This document describes how to set up and configure Langfuse for LLM observability in N-Xyme_MIND.

## Overview

Langfuse provides tracing, metrics, and analytics for LLM applications. It helps you:
- Monitor LLM costs and usage
- Debug traces and latency issues
- Track prompt iterations
- Analyze user interactions

## Prerequisites

- Python 3.9+ (for SDK usage)
- Docker (optional, for self-hosted deployment)

## Installation Options

### Option 1: Langfuse Cloud (Recommended for Quick Start)

1. Sign up at [https://langfuse.com](https://langfuse.com)
2. Create a new project
3. Copy your API keys from the dashboard
4. Add to your `.env` file:

```bash
LANGFUSE_PUBLIC_KEY=pk-...
LANGFUSE_SECRET_KEY=sk-...
LANGFUSE_HOST=https://cloud.langfuse.com
```

### Option 2: Self-Hosted Langfuse

Run Langfuse locally using Docker:

```bash
bash scripts/setup-langfuse.sh --self-host
cd configs/langfuse
docker-compose up -d
```

Langfuse will be available at `http://localhost:3000`

## Setup Script

Use the provided setup script to configure Langfuse:

```bash
# For cloud deployment
bash scripts/setup-langfuse.sh --cloud

# For self-hosted deployment
bash scripts/setup-langfuse.sh --self-host
```

## Environment Variables

Add these to your `.env` file:

| Variable | Description | Required |
|----------|-------------|----------|
| `LANGFUSE_PUBLIC_KEY` | Public key from Langfuse dashboard | Yes |
| `LANGFUSE_SECRET_KEY` | Secret key from Langfuse dashboard | Yes |
| `LANGFUSE_HOST` | Langfuse instance URL | Yes (for self-host) |

Example `.env` entries:

```bash
# Langfuse (LLM Observability)
LANGFUSE_PUBLIC_KEY=pk-YOUR_PUBLIC_KEY_HERE
LANGFUSE_SECRET_KEY=sk-YOUR_SECRET_KEY_HERE
LANGFUSE_HOST=https://cloud.langfuse.com  # or http://localhost:3000 for self-host
```

## Integrating Langfuse

### Basic Integration

```python
from langfuse import Langfuse

# Initialize with environment variables
langfuse = Langfuse()

# Wrap your LLM calls with tracing
def call_llm(prompt, model="gpt-4"):
    with langfuse.trace("llm-call") as trace:
        trace.input = prompt
        trace.output = response
        trace.metadata = {"model": model}
        return response
```

### OpenAI Integration

```python
from langfuse import Langfuse
from openai import OpenAI

langfuse = Langfuse()
client = OpenAI()

def call_openai(prompt):
    with langfuse.trace("openai-call") as trace:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        trace.output = response.choices[0].message.content
        return response
```

### LiteLLM Integration (Unified Interface)

If using LiteLLM for proxy/routing:

```python
from litellm import completion
from langfuse import Langfuse

langfuse = Langfuse()

def call_with_trace(messages):
    response = completion(
        model="gpt-4",
        messages=messages,
        langfuse_tracing=langfuse
    )
    return response
```

## Dashboard

Access your traces at:
- **Cloud**: `https://cloud.langfuse.com`
- **Self-hosted**: `http://localhost:3000`

## Metrics Tracked

| Metric | Description |
|--------|-------------|
| Latency | Time taken for LLM response |
| Token Count | Input/output tokens used |
| Cost | Estimated cost based on model pricing |
| Trace | Full request/response with metadata |

## Troubleshooting

### Langfuse not connecting

1. Verify API keys are correct in `.env`
2. Check network connectivity
3. For self-host: verify Docker container is running

```bash
# Check container status
docker ps | grep langfuse

# View logs
docker logs langfuse-langfuse-1
```

### Missing traces

Ensure your LLM calls are wrapped in `langfuse.trace()` context:

```python
# Correct
with langfuse.trace("my-call"):
    response = client.chat.completions.create(...)

# Incorrect - no trace captured
response = client.chat.completions.create(...)
```

## References

- [Langfuse Documentation](https://langfuse.com/docs)
- [Langfuse Python SDK](https://langfuse.com/docs/sdk/python)
- [Self-hosting Guide](https://langfuse.com/docs/deployment/self-host)
