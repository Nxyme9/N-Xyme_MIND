"""
OpenAI-Compatible Proxy Server — Routes OpenCode requests through intelligent router.

This server acts as an OpenAI-compatible API endpoint. OpenCode sends requests here,
and the router intelligently selects the optimal model, provider, API key, and VPN IP.
"""

import json
import time
import uuid
import os
import asyncio
import httpx
from typing import Dict, List, Optional

from . import (
    intelligent_router,
    health_monitor,
    dashboard,
    stall_detector,
    key_notifier,
    dead_letter_queue,
    request_validator,
    lru_semantic_cache,
    feedback_loop,
    vpn_ip_pool,
    api_key_pool,
    cost_tracker,
    learning_engine,
    agent_preferences,
    metrics,
    alerts,
)

# Provider configurations
PROVIDERS = {
    "opencode": {
        "base_url": "https://api.opencode.ai/v1",
        "api_key": os.getenv("OPENCODE_API_KEY", ""),
        "models": ["qwen3.6-plus-free", "minimax-m2.5-free"],
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "models": ["qwen/qwen3.6-plus:free", "deepseek/deepseek-r1:free"],
    },
    "google": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "api_key": os.getenv("GOOGLE_API_KEY", ""),
        "models": ["gemini-2.5-flash"],
    },
}

# Model to provider mapping
MODEL_PROVIDER_MAP = {
    "qwen3.6-plus-free": "opencode",
    "qwen3.6-plus:free": "openrouter",
    "minimax-m2.5-free": "opencode",
    "deepseek-r1:free": "openrouter",
    "gemini-2.5-flash": "google",
}


async def call_provider(model: str, messages: List[dict], provider: str = None) -> dict:
    """Call the actual provider API."""
    if not provider:
        provider = MODEL_PROVIDER_MAP.get(model, "opencode")

    config = PROVIDERS.get(provider)
    if not config or not config["api_key"]:
        raise Exception(f"Provider {provider} not configured or missing API key")

    # Map model name for provider
    provider_model = model
    if provider == "openrouter" and "/" not in model:
        provider_model = f"qwen/{model}:free" if "qwen" in model.lower() else model

    url = f"{config['base_url']}/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "http://localhost"
        headers["X-Title"] = "N-Xyme Router"

    payload = {
        "model": provider_model,
        "messages": messages,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()


async def chat_completions(request: dict) -> dict:
    """Handle chat completions request through intelligent router."""
    request_id = str(uuid.uuid4())[:8]
    messages = request.get("messages", [])
    model = request.get("model", "qwen3.6-plus-free")

    # Extract prompt from messages
    prompt = " ".join(
        [m.get("content", "") for m in messages if m.get("role") == "user"]
    )

    # Validate request
    valid, error = request_validator.validate(prompt)
    if not valid:
        return {"error": {"message": error, "type": "invalid_request_error"}}

    # Check cache
    cached = lru_semantic_cache.get(prompt)
    if cached:
        return {
            "id": f"chatcmpl-{request_id}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": cached},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }

    # Route through intelligent router
    route = intelligent_router.select_route(prompt, agent_type="opencode")
    stall_detector.start_request(f"opencode:{request_id}")

    try:
        # Call provider
        start = time.time()
        result = await call_provider(route["model"], messages, route["provider"])
        latency_ms = (time.time() - start) * 1000

        # Record success
        intelligent_router.record_success(route, len(prompt), 100, latency_ms)
        stall_detector.complete_request(f"opencode:{request_id}", True)

        # Cache response
        if "choices" in result and result["choices"]:
            response_text = result["choices"][0]["message"]["content"]
            lru_semantic_cache.put(prompt, response_text)

        return result

    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        intelligent_router.record_failure(route, str(e)[:100], latency_ms)
        stall_detector.complete_request(f"opencode:{request_id}", False)

        # Try fallback
        dead_letter_queue.add(prompt, "", "opencode", str(e)[:100], model)
        return {"error": {"message": str(e)[:200], "type": "api_error"}}


# FastAPI app
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="N-Xyme Intelligent Router")


@app.post("/v1/chat/completions")
async def chat_completions_endpoint(request: Request):
    body = await request.json()
    result = await chat_completions(body)
    if "error" in result:
        return JSONResponse(status_code=502, content=result)
    return JSONResponse(content=result)


@app.get("/v1/models")
async def list_models():
    """List available models."""
    models = []
    for provider, config in PROVIDERS.items():
        if config["api_key"]:
            for model in config["models"]:
                models.append({"id": model, "object": "model", "owned_by": provider})
    return {"data": models, "object": "list"}


@app.get("/health")
async def health():
    """Health check endpoint with full system status."""
    health_status = health_monitor.get_status()
    dashboard.update_provider_health(health_status)
    vpn_status = vpn_ip_pool.get_pool_status()
    dashboard.update_vpn_status(vpn_status)
    return {
        "status": "healthy",
        "providers": health_status,
        "vpn_pool": vpn_status,
        "api_keys": {
            p: api_key_pool.get_pool_status(p) for p in api_key_pool.get_all_providers()
        },
        "dashboard": dashboard.get_status(),
        "stalled_providers": stall_detector.get_stalled_providers(),
        "key_alerts": key_notifier.get_alerts(),
        "learning": learning_engine.get_stats(),
        "dead_letters": dead_letter_queue.get_stats(),
    }


@app.get("/dashboard")
async def get_dashboard():
    """Full dashboard data."""
    return dashboard.get_status()


@app.post("/v1/feedback")
async def submit_feedback(request: Request):
    """Submit quality feedback for a routed request."""
    body = await request.json()
    feedback_loop.submit(
        request_id=body.get("request_id", "unknown"),
        model=body.get("model", "unknown"),
        provider=body.get("provider", "unknown"),
        rating=body.get("rating", 3),
        comment=body.get("comment", ""),
        was_helpful=body.get("was_helpful", True),
        response_time_ms=body.get("response_time_ms", 0.0),
    )
    return {"status": "recorded"}


@app.get("/v1/feedback/rankings")
async def get_feedback_rankings():
    """Get model rankings based on user feedback."""
    return {"rankings": feedback_loop.get_model_rankings()}


if __name__ == "__main__":
    import uvicorn

    print("Starting N-Xyme Intelligent Router Proxy on port 8080...")
    uvicorn.run(app, host="127.0.0.1", port=8080)
