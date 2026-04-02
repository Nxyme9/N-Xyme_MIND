"""
Security Headers Middleware
Adds HTTP security headers to all responses
"""

import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds security headers to all responses"""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        is_production = os.getenv("NXM_ENV", "development") == "production"
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY" if is_production else "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        if is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: blob:; "
                "font-src 'self' data:; "
                "connect-src 'self' https://api.openai.com https://api.anthropic.com; "
                "frame-ancestors 'none'; "
                "base-uri 'self';"
            )
            response.headers["X-Permitted-Cross-Domain-Policies"] = "none"
            response.headers["Expect-CT"] = "max-age=31536000, enforce"
        else:
            response.headers["Strict-Transport-Security"] = "max-age=86400"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "connect-src 'self' ws: wss: http: https:; "
                "img-src 'self' data: blob:;"
            )
        
        return response


class IPBlocklistMiddleware(BaseHTTPMiddleware):
    """Block specific IP addresses"""
    
    def __init__(self, app):
        super().__init__(app)
        self._blocklist = set(os.getenv("NXM_IP_BLOCKLIST", "").split(","))
        self._blocklist = {ip.strip() for ip in self._blocklist if ip.strip()}
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else None
        
        if client_ip in self._blocklist:
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=403,
                content={"error": "Access denied"}
            )
        
        return await call_next(request)


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Limit request body size"""
    
    def __init__(self, app, max_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size
    
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        
        if content_length and int(content_length) > self.max_size:
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=413,
                content={"error": "Request too large"}
            )
        
        return await call_next(request)
