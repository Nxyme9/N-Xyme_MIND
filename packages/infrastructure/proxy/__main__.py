#!/usr/bin/env python3
"""
N-Xyme Intelligent Router Proxy
- API Key rotation (5 keys)
- VPN IP rotation (8 SOCKS5 proxies)
- Self-learning rate limiting
- Circuit breaker
"""

import sys
sys.path.insert(0, '/home/nxyme/N-Xyme_CODE/N-Xyme_MIND')

import json
import time
import threading
import logging
from collections import deque
from dataclasses import dataclass, field
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ======================== RATE LIMITER ========================
@dataclass
class RateLimiter:
    """Token bucket rate limiter with adaptive rates."""
    rpm: float = 10.0
    burst: int = 5
    tokens: float = field(default=5.0)
    last_refill: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    
    def allow(self) -> bool:
        with self._lock:
            now = time.time()
            # Refill tokens
            elapsed = now - self.last_refill
            self.tokens = min(self.burst, self.tokens + elapsed * (self.rpm / 60.0))
            self.last_refill = now
            
            if self.tokens >= 1.0:
                self.tokens -= 1.0
                return True
            return False
    
    def wait_time(self) -> float:
        if self.tokens >= 1.0:
            return 0.0
        return (1.0 - self.tokens) / (self.rpm / 60.0)
    
    def record_429(self):
        """Cut rate on rate limit."""
        with self._lock:
            self.rpm = max(1, self.rpm * 0.5)
            self.tokens = 0.0
            logger.warning(f"Rate limit hit, lowering RPM to {self.rpm}")
    
    def record_success(self):
        """Slight increase on success."""
        with self._lock:
            if self.rpm < 50:
                self.rpm = min(50, self.rpm * 1.05)

# ======================== API KEY POOL ========================
@dataclass
class APIKeyState:
    key: str
    key_id: str
    success: int = 0
    errors: int = 0
    last_used: float = 0.0
    
    @property
    def error_rate(self) -> float:
        total = self.success + self.errors
        return self.errors / total if total > 0 else 0.0
    
    @property
    def health(self) -> float:
        return 1.0 - self.error_rate

class APIKeyPool:
    def __init__(self, keys: list):
        self.keys = [APIKeyState(k['key'], k['key_id']) for k in keys]
        self.index = 0
        self._lock = threading.Lock()
    
    def get(self) -> APIKeyState:
        with self._lock:
            key = self.keys[self.index % len(self.keys)]
            self.index += 1
            key.last_used = time.time()
            return key
    
    def record_success(self, key_id: str):
        for k in self.keys:
            if k.key_id == key_id:
                k.success += 1
    
    def record_error(self, key_id: str):
        for k in self.keys:
            if k.key_id == key_id:
                k.errors += 1
    
    def get_healthy(self) -> Optional[APIKeyState]:
        """Get healthiest key."""
        enabled = [k for k in self.keys if k.health > 0.3]
        return max(enabled, key=lambda k: k.health) if enabled else None

# ======================== VPN ROTATOR ========================
VPN_PROXIES = [
    {"ip": "127.0.0.1", "port": 1080, "provider": "local"},
    {"ip": "127.0.0.1", "port": 1081, "provider": "local"},
    {"ip": "127.0.0.1", "port": 1082, "provider": "local"},
    {"ip": "127.0.0.1", "port": 1083, "provider": "local"},
    {"ip": "127.0.0.1", "port": 1084, "provider": "local"},
    {"ip": "127.0.0.1", "port": 1085, "provider": "local"},
    {"ip": "127.0.0.1", "port": 1086, "provider": "local"},
    {"ip": "127.0.0.1", "port": 1087, "provider": "local"},
]

@dataclass
class VPNNode:
    ip: str
    port: int
    provider: str = "local"
    success: int = 0
    errors: int = 0
    
    @property
    def proxy_url(self) -> str:
        return f"socks5://{self.ip}:{self.port}"
    
    @property
    def health(self) -> float:
        total = self.success + self.errors
        return 1.0 - (self.errors / total if total > 0 else 0.0)

class VPNRotator:
    def __init__(self):
        self.nodes = [VPNNode(**p) for p in VPN_PROXIES]
        self.index = 0
        self._lock = threading.Lock()
    
    def get(self) -> VPNNode:
        with self._lock:
            # Try healthy nodes first
            healthy = [n for n in self.nodes if n.health > 0.3]
            if healthy:
                node = healthy[self.index % len(healthy)]
                self.index += 1
                return node
            node = self.nodes[self.index % len(self.nodes)]
            self.index += 1
            return node
    
    def record_success(self, ip: str, port: int):
        for n in self.nodes:
            if n.ip == ip and n.port == port:
                n.success += 1
    
    def record_error(self, ip: str, port: int):
        for n in self.nodes:
            if n.ip == ip and n.port == port:
                n.errors += 1

# ======================== LOAD CONFIG ========================
with open('/home/nxyme/N-Xyme_CODE/N-Xyme_MIND/configs/api-keys/keys.json') as f:
    config = json.load(f)

KEYS = config.get('openrouter', [])
api_pool = APIKeyPool(KEYS)
vpn_rotator = VPNRotator()
rate_limiter = RateLimiter(rpm=10.0, burst=5)

# Qwen-specific limiter (conservative)
qwen_limiter = RateLimiter(rpm=3, burst=1)

# ======================== FASTAPI APP ========================
app = FastAPI(title="N-Xyme Intelligent Router")

class ChatRequest(BaseModel):
    model: str
    messages: list[dict]
    temperature: float = 1.0
    max_tokens: int = None
    stream: bool = False

@app.get("/health")
def health():
    """Health check with stats."""
    healthy_keys = [k for k in api_pool.keys if k.health > 0.3]
    healthy_vpns = [n for n in vpn_rotator.nodes if n.health > 0.3]
    
    return {
        "status": "healthy",
        "api_keys": {
            "total": len(api_pool.keys),
            "healthy": len(healthy_keys),
            "current_index": api_pool.index % len(api_pool.keys),
        },
        "vpn_nodes": {
            "total": len(vpn_rotator.nodes),
            "healthy": len(healthy_vpns),
        },
        "rate_limiter": {
            "rpm": rate_limiter.rpm,
            "tokens": rate_limiter.tokens,
        },
        "qwen_limiter": {
            "rpm": qwen_limiter.rpm,
            "tokens": qwen_limiter.tokens,
        }
    }

@app.post("/v1/chat/completions")
async def chat_completions(request: ChatRequest, req: Request):
    """OpenAI-compatible chat completions with full rotation."""
    
    # Check if Qwen model
    is_qwen = "qwen" in request.model.lower()
    limiter = qwen_limiter if is_qwen else rate_limiter
    
    # Wait for rate limit
    if not limiter.allow():
        wait = limiter.wait_time()
        raise HTTPException(
            status_code=429,
            detail={"error": "rate_limit", "retry_after": wait}
        )
    
    # Get API key
    key = api_pool.get_healthy() or api_pool.get()
    if not key:
        raise HTTPException(status_code=500, detail="No API keys")
    
    # Get VPN
    vpn = vpn_rotator.get()
    
    # Build request - extract proper model ID for OpenRouter
    model_id = request.model
    # Strip any provider prefix and convert to openrouter format
    if model_id.startswith("openrouter/"):
        model_id = model_id[11:]  # Remove "openrouter/"
    elif "/" in model_id:
        # Some other provider format - use as is
        pass
    elif ":" in model_id:
        # Handle model:variant format (e.g., qwen3.6-plus:free -> qwen/qwen3.6-plus:free)
        # Keep the dots in the model name, use colon for variant
        parts = model_id.split(":")
        model_name = parts[0]  # qwen3.6-plus (keep dots)
        variant = parts[1] if len(parts) > 1 else "free"
        # Use preview model if available, otherwise use coder
        if "3.6" in model_name:
            model_id = f"qwen/qwen3.6-plus-preview:{variant}"
        else:
            model_id = f"qwen/{model_name}:{variant}"
    else:
        # Just model name - add qwen as default provider
        model_id = f"qwen/{model_id}"
    
    headers = {
        "Authorization": f"Bearer {key.key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://opencode.ai",
        "X-Title": "N-Xyme"
    }
    
    body = {
        "model": model_id,
        "messages": request.messages,
        "temperature": request.temperature,
        "stream": request.stream
    }
    if request.max_tokens:
        body["max_tokens"] = request.max_tokens
    
    # Use SOCKS5 proxy for IP rotation
    proxies = {"http": vpn.proxy_url, "https": vpn.proxy_url}
    
    try:
        resp = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=body,
            proxies=proxies,
            timeout=90
        )
        
        if resp.status_code == 429:
            limiter.record_429()
            api_pool.record_error(key.key_id)
            vpn_rotator.record_error(vpn.ip, vpn.port)
            raise HTTPException(
                status_code=429,
                detail={"error": "rate_limit", "message": "Upstream rate limited"}
            )
        
        if resp.status_code != 200:
            api_pool.record_error(key.key_id)
            vpn_rotator.record_error(vpn.ip, vpn.port)
            return JSONResponse(content=resp.json(), status_code=resp.status_code)
        
        # Record success
        api_pool.record_success(key.key_id)
        vpn_rotator.record_success(vpn.ip, vpn.port)
        limiter.record_success()
        
        return resp.json()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Request failed: {e}")
        api_pool.record_error(key.key_id)
        vpn_rotator.record_error(vpn.ip, vpn.port)
        raise HTTPException(status_code=502, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8080)