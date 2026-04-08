"""
Proxy Server - FastAPI server for LLM request proxying with rate limiting.

Features:
- /v1/chat/completions endpoint (OpenAI-compatible)
- TupleRateLimiter before each request
- Routes through optimal (model, vpn_ip, api_key)
- Returns 429 with retry_after if rate limited
- /health endpoint with rate_optimizer stats

Uses only: fastapi, uvicorn, pydantic, requests, sqlite3, threading
"""

import logging
import time
from typing import Any, Dict, Optional

# Lazy imports - these are optional dependencies
FastAPI = None
HTTPException = None
Request = None
BaseModel = None
Field = None
JSONResponse = None
uvicorn = None
_FASTAPI_AVAILABLE = False

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel, Field
    import uvicorn
    _FASTAPI_AVAILABLE = True
except ImportError:
    pass

from packages.infrastructure.proxy.tuple_rate_limiter import TupleRateLimiter
from packages.infrastructure.proxy.rate_optimizer import RateOptimizer
from packages.infrastructure.proxy.api_key_pool import APIKeyPool
from packages.infrastructure.proxy.vpn_rotator import VPNRotator

logger = logging.getLogger(__name__)


# Pydantic models - only defined if pydantic is available
if _FASTAPI_AVAILABLE:
    class Message(BaseModel):
        role: str
        content: str


    class ChatMessage(BaseModel):
        messages: list[Message]
        model: str
        temperature: Optional[float] = 1.0
        max_tokens: Optional[int] = None
        stream: Optional[bool] = False


    class ChatCompletionRequest(BaseModel):
        model: str
        messages: list[Dict[str, str]]
        temperature: Optional[float] = 1.0
        max_tokens: Optional[int] = None
        stream: Optional[bool] = False


    class Usage(BaseModel):
        prompt_tokens: int = 0
        completion_tokens: int = 0
        total_tokens: int = 0


    class ChatCompletionChoice(BaseModel):
        index: int
        message: Message
        finish_reason: str = "stop"


    class ChatCompletionResponse(BaseModel):
        id: str = "chatcmpl-xxx"
        object: str = "chat.completion"
        created: int = 0
        model: str
        choices: list[ChatCompletionChoice]
        usage: Usage = Usage()


class ProxyServer:
    """
    FastAPI proxy server for LLM requests with rate limiting.
    
    Features:
    - OpenAI-compatible /v1/chat/completions endpoint
    - TupleRateLimiter for per-tuple rate limiting
    - RateOptimizer for learning optimal rates
    - APIKeyPool for key rotation
    - VPNRotator for IP rotation
    """
    
    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8000,
        upstream_base_url: str = "https://api.openai.com",
        default_rpm: float = 10.0,
        max_rpm: float = 50.0,
        min_rpm: float = 1.0
    ):
        self.host = host
        self.port = port
        self.upstream_base_url = upstream_base_url
        
        # Initialize components
        self.rate_limiter = TupleRateLimiter(
            default_rpm=default_rpm,
            max_rpm=max_rpm,
            min_rpm=min_rpm
        )
        
        self.rate_optimizer = RateOptimizer(
            db_path="data/proxy/rate_optimizer.db",
            default_rpm=default_rpm,
            max_rpm=max_rpm,
            min_rpm=min_rpm
        )
        
        self.api_key_pool = APIKeyPool(
            config_path="configs/api-keys/keys.json",
            default_strategy="round_robin"
        )
        
        self.vpn_rotator = VPNRotator(
            vpn_manager_path="packages/infrastructure/network/vpn_manager.py"
        )
        
        # Create FastAPI app (only if FastAPI is available)
        if _FASTAPI_AVAILABLE:
            self.app = FastAPI(title="LLM Proxy Server")
            self._setup_routes()
        else:
            self.app = None
    
    def _setup_routes(self):
        """Set up FastAPI routes."""
        if not _FASTAPI_AVAILABLE:
            return
        
        @self.app.get("/health")
        async def health():
            """Health check endpoint with rate optimizer stats."""
            return {
                "status": "healthy",
                "rate_limiter": self.rate_limiter.get_all_stats(),
                "rate_optimizer": self.rate_optimizer.get_total_stats(),
                "api_keys": {
                    provider: self.api_key_pool.get_stats(provider)
                    for provider in self.api_key_pool._keys.keys()
                },
                "vpn_nodes": self.vpn_rotator.get_stats()
            }
        
        @self.app.get("/")
        async def root():
            """Root endpoint."""
            return {
                "message": "LLM Proxy Server",
                "endpoints": ["/v1/chat/completions", "/health"]
            }
        
        @self.app.post("/v1/chat/completions")
        async def chat_completions(request: ChatCompletionRequest, req: Request):
            """OpenAI-compatible chat completions endpoint."""
            return await self._handle_chat_completion(request, req)
    
    async def _handle_chat_completion(
        self,
        request: ChatCompletionRequest,
        http_request: Request
    ) -> JSONResponse:
        """Handle chat completion request with rate limiting."""
        start_time = time.time()
        
        # Extract provider from model name
        # Model format: "provider/model" e.g., "openai/gpt-4", "anthropic/claude-3"
        model = request.model
        if "/" in model:
            provider, model = model.split("/", 1)
        else:
            provider = "openai"
        
        # Get VPN node
        vpn_node = self.vpn_rotator.get_vpn_ip(strategy="health")
        vpn_ip = vpn_node.ip if vpn_node else ""
        vpn_port = vpn_node.port if vpn_node else 0
        
        # Get API key
        api_key_obj = self.api_key_pool.get_key(provider)
        api_key = api_key_obj.key if api_key_obj else ""
        api_key_id = api_key_obj.key_id if api_key_obj else ""
        
        # Get optimized RPM from rate optimizer
        optimal_rpm = self.rate_optimizer.get_optimal_rpm(
            provider, model, vpn_ip, api_key_id
        )
        
        # Set rate limiter RPM
        self.rate_limiter.set_rpm(provider, model, vpn_ip, api_key_id, optimal_rpm)
        
        # Try to acquire rate limit slot
        allowed, retry_after = self.rate_limiter.acquire(
            provider, model, vpn_ip, api_key_id
        )
        
        if not allowed:
            # Rate limited
            logger.warning(
                f"Rate limited: {provider}/{model} (retry after {retry_after:.1f}s)"
            )
            
            # Record rate limit for optimizer
            self.rate_optimizer.record_rate_limit(
                provider, model, vpn_ip, api_key_id
            )
            
            # Rotate VPN on 429
            if vpn_node:
                self.vpn_rotator.rotate_on_429(vpn_node.ip, vpn_node.port)
            
            # Rotate API key on 429
            if api_key_obj:
                self.api_key_pool.rotate_on_429(provider, api_key_obj.key_id)
            
            raise HTTPException(
                status_code=429,
                detail={
                    "error": "rate_limit",
                    "message": "Rate limit exceeded",
                    "retry_after": retry_after
                }
            )
        
        try:
            # Make request to upstream
            response = await self._make_upstream_request(
                provider=provider,
                model=model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                stream=request.stream,
                api_key=api_key,
                proxy=vpn_node.proxy_url if vpn_node else None
            )
            
            # Record success
            self.rate_limiter.record_success(provider, model, vpn_ip, api_key_id)
            self.rate_optimizer.record_success(provider, model, vpn_ip, api_key_id)
            
            if api_key_obj:
                self.api_key_pool.record_success(provider, api_key_obj.key_id)
            
            if vpn_node:
                self.vpn_rotator.record_success(vpn_node.ip, vpn_node.port)
            
            return response
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Upstream request failed: {e}")
            
            # Record error
            if api_key_obj:
                self.api_key_pool.record_error(provider, api_key_obj.key_id)
            
            if vpn_node:
                self.vpn_rotator.record_error(vpn_node.ip, vpn_node.port)
            
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "upstream_error",
                    "message": str(e)
                }
            )
    
    async def _make_upstream_request(
        self,
        provider: str,
        model: str,
        messages: list[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        stream: bool,
        api_key: str,
        proxy: Optional[str] = None
    ) -> JSONResponse:
        """Make request to upstream provider."""
        import requests
        
        # Build headers
        headers = {
            "Content-Type": "application/json"
        }
        
        # Add auth header based on provider
        if provider == "openai" or provider == "opencode":
            headers["Authorization"] = f"Bearer {api_key}"
        elif provider == "anthropic":
            headers["x-api-key"] = api_key
        
        # Build request body
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream
        }
        
        if max_tokens:
            body["max_tokens"] = max_tokens
        
        # Determine endpoint
        if provider == "openai" or provider == "opencode":
            endpoint = f"{self.upstream_base_url}/v1/chat/completions"
        elif provider == "anthropic":
            endpoint = "https://api.anthropic.com/v1/messages"
        else:
            endpoint = f"{self.upstream_base_url}/v1/chat/completions"
        
        # Make request
        proxies = {"http": proxy, "https": proxy} if proxy else None
        
        try:
            response = requests.post(
                endpoint,
                headers=headers,
                json=body,
                proxies=proxies,
                timeout=60
            )
            
            if response.status_code == 429:
                raise HTTPException(
                    status_code=429,
                    detail={"error": "rate_limit", "message": "Upstream rate limited"}
                )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail={
                        "error": "upstream_error",
                        "message": response.text
                    }
                )
            
            # Return response
            data = response.json()
            
            return JSONResponse(
                content=data,
                status_code=200
            )
            
        except requests.RequestException as e:
            raise HTTPException(
                status_code=502,
                detail={"error": "request_failed", "message": str(e)}
            )
    
    def run(self):
        """Run the proxy server."""
        logger.info(f"Starting LLM Proxy Server on {self.host}:{self.port}")
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )


def create_app():
    """Create and configure the proxy server.
    
    Returns the FastAPI app for uvicorn.
    """
    server = ProxyServer(
        host="0.0.0.0",
        port=8000,
        upstream_base_url="https://api.openai.com",
        default_rpm=10.0,
        max_rpm=50.0,
        min_rpm=1.0
    )
    return server.app  # Return the FastAPI app, not the ProxyServer


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    server = create_app()
    server.run()