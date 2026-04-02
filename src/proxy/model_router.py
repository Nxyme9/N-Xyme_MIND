#!/usr/bin/env python3
"""
Model Router Proxy - Unified API for multi-provider LLM routing
"""
import os
import asyncio
import logging
import time
import json
import sqlite3
from typing import List, Optional, Dict, Any
from enum import Enum
from dataclasses import dataclass, field

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import httpx
import uvicorn

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Model Router Proxy", version="1.0.0")

DATA_DIR = os.path.expanduser("~/N-Xyme_MIND/data/proxy")
os.makedirs(DATA_DIR, exist_ok=True)
DB_PATH = os.path.join(DATA_DIR, "usage.db")


def init_db():
    """Initialize SQLite database for usage tracking"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            provider TEXT,
            model TEXT,
            task_type TEXT,
            tokens_used INTEGER,
            latency_ms INTEGER,
            success INTEGER,
            rate_limit_hit INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS provider_stats (
            provider TEXT PRIMARY KEY,
            requests INTEGER DEFAULT 0,
            tokens INTEGER DEFAULT 0,
            rate_limits INTEGER DEFAULT 0,
            last_used REAL
        )
    """)
    conn.commit()
    conn.close()


init_db()


class TaskType(Enum):
    CODING = "coding"
    REASONING = "reasoning"
    FAST = "fast"
    HEAVY = "heavy"
    VISION = "vision"
    GENERAL = "general"


@dataclass
class ProviderStats:
    provider: str
    requests: int = 0
    tokens: int = 0
    rate_limits: int = 0
    last_used: float = 0


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    top_p: Optional[float] = 1.0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]


PROVIDERS = {
    "opencode": {
        "base_url": "https://opencode.ai/api/chat",
        "models": ["opencode/mimo-v2-pro-free", "opencode/minimax-m2.5-free"],
        "requires_key": True,
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1/chat/completions",
        "models": ["openrouter/*", "qwen/qwen3-coder:free", "deepseek/deepseek-r1:free"],
        "requires_key": True,
    },
    "ollama": {
        "base_url": "http://localhost:11434/api/chat",
        "models": ["qwen2.5-coder:7b", "qwen3:8b", "llama3.2:3b"],
        "requires_key": False,
    },
}


TASK_ROUTING = {
    "coding": ["ollama", "opencode"],
    "fast": ["ollama", "opencode"],
    "reasoning": ["openrouter", "opencode"],
    "heavy": ["openrouter", "opencode"],
    "vision": ["opencode"],
    "general": ["opencode", "ollama", "openrouter"],
}


def detect_task_type(model: str, messages: List[ChatMessage]) -> TaskType:
    """Detect task type from model and messages"""
    model_lower = model.lower()
    content = " ".join(m.content.lower() for m in messages)
    
    if any(kw in model_lower for kw in ["coder", "code", "programming"]):
        return TaskType.CODING
    if any(kw in model_lower for kw in ["reason", "think", "r1"]):
        return TaskType.REASONING
    if any(kw in model_lower for kw in ["vision", "omni", "multimodal"]):
        return TaskType.VISION
    if any(kw in model_lower for kw in ["large", "14b", "32b"]):
        return TaskType.HEAVY
    
    if any(kw in content for kw in ["debug", "fix", "implement", "function", "class"]):
        return TaskType.CODING
    if any(kw in content for kw in ["explain", "why", "how does", "reason"]):
        return TaskType.REASONING
    
    return TaskType.GENERAL


def route_provider(task_type: TaskType) -> str:
    """Get provider order for task type"""
    providers = TASK_ROUTING.get(task_type.value, TASK_ROUTING["general"])
    return providers[0]


def log_request(provider: str, model: str, task_type: TaskType,
                latency_ms: int, success: bool, rate_limit: bool):
    """Log request to database"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO usage_logs 
        (timestamp, provider, model, task_type, latency_ms, success, rate_limit_hit)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (time.time(), provider, model, task_type.value, latency_ms, int(success), int(rate_limit)))
    
    conn.execute("""
        INSERT INTO provider_stats (provider, requests, rate_limits, last_used)
        VALUES (?, 1, ?, ?)
        ON CONFLICT(provider) DO UPDATE SET
            requests = requests + 1,
            rate_limits = rate_limits + ?,
            last_used = ?
    """, (provider, int(rate_limit), time.time(), int(rate_limit), time.time()))
    
    conn.commit()
    conn.close()


async def call_provider(provider: str, model: str, messages: List[ChatMessage],
                        temperature: float, max_tokens: int) -> Dict[str, Any]:
    """Call upstream provider"""
    config = PROVIDERS[provider]
    base_url = config["base_url"]
    
    headers = {"Content-Type": "application/json"}
    
    if provider == "opencode":
        headers["Authorization"] = f"Bearer {os.getenv('OPENCODE_API_KEY', '')}"
    elif provider == "openrouter":
        headers["Authorization"] = f"Bearer {os.getenv('OPENROUTER_API_KEY', '')}"
        headers["HTTP-Referer"] = "https://opencode.ai"
        headers["X-Title"] = "N-Xyme MIND"
    
    if provider == "ollama":
        base_url = f"{base_url}"
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    else:
        payload = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(base_url, json=payload, headers=headers)
        
        if resp.status_code == 429:
            raise HTTPException(status_code=429, detail="Rate limited")
        
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
        
        return resp.json()


def is_rate_limited(resp: Response) -> bool:
    """Check if response indicates rate limiting"""
    return resp.status_code == 429


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest, http_req: Request):
    """Route chat completion request to appropriate provider"""
    
    task_type = detect_task_type(request.model, request.messages)
    provider = route_provider(task_type)
    
    logger.info(f"Task: {task_type.value}, Provider: {provider}, Model: {request.model}")
    
    start_time = time.time()
    rate_limited = False
    
    try:
        result = await call_provider(
            provider, request.model, request.messages,
            request.temperature, request.max_tokens
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        log_request(provider, request.model, task_type, latency_ms, True, False)
        
        return JSONResponse(content=result)
        
    except HTTPException as e:
        if e.status_code == 429:
            rate_limited = True
            logger.warning(f"Rate limited by {provider}, attempting VPN rotation...")
            
            try:
                from ..network.vpn_rotator import VPNRotator
                rotator = VPNRotator()
                rotator.rotate()
                logger.info("VPN rotated, will retry on next request")
            except Exception as ve:
                logger.error(f"VPN rotation failed: {ve}")
            
            latency_ms = int((time.time() - start_time) * 1000)
            log_request(provider, request.model, task_type, latency_ms, False, True)
            
            retry_provider = "openrouter" if provider == "opencode" else "ollama"
            
            try:
                logger.info(f"Retrying with fallback provider: {retry_provider}")
                result = await call_provider(
                    retry_provider, request.model, request.messages,
                    request.temperature, request.max_tokens
                )
                return JSONResponse(content=result)
            except Exception:
                raise HTTPException(status_code=429, detail="All providers rate limited")
        
        raise
    
    except Exception as e:
        logger.error(f"Provider error: {e}")
        latency_ms = int((time.time() - start_time) * 1000)
        log_request(provider, request.model, task_type, latency_ms, False, False)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/v1/models")
async def list_models():
    """List available models"""
    models = []
    for prov, config in PROVIDERS.items():
        for model in config["models"]:
            models.append({"id": model, "provider": prov})
    return {"models": models}


@app.get("/stats")
async def get_stats():
    """Get usage statistics"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    stats = conn.execute("SELECT * FROM provider_stats").fetchall()
    recent = conn.execute("""
        SELECT * FROM usage_logs 
        ORDER BY timestamp DESC LIMIT 20
    """).fetchall()
    
    conn.close()
    
    return {
        "providers": [dict(s) for s in stats],
        "recent_requests": [dict(r) for r in recent]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": time.time()}


@app.post("/vpn/rotate")
async def vpn_rotate():
    """Manually trigger VPN rotation"""
    try:
        from ..network.vpn_rotator import VPNRotator
        rotator = VPNRotator()
        success = rotator.rotate()
        return {"success": success, "message": "VPN rotated" if success else "Rotation failed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/vpn/status")
async def vpn_status():
    """Get VPN status"""
    try:
        from ..network.vpn_rotator import VPNRotator
        rotator = VPNRotator()
        status = rotator.status()
        return {
            "connected": status.connected,
            "country": status.country.name if status.country else None,
            "ip": status.ip_address
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def main():
    """Run the proxy server"""
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")


if __name__ == "__main__":
    main()