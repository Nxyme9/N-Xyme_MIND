"""
CSRF Protection Middleware
Provides Cross-Site Request Forgery protection for FastAPI
"""

import os
import secrets
from typing import Optional
from datetime import datetime, timedelta
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response, JSONResponse
import logging

logger = logging.getLogger(__name__)


class CSRFConfig:
    """CSRF configuration"""
    cookie_name: str = "nxm_csrf_token"
    cookie_secure: bool = True
    cookie_httponly: bool = True
    cookie_samesite: str = "lax"
    header_name: str = "X-CSRF-Token"
    token_length: int = 32


class CSRFProtection:
    """CSRF token manager"""
    
    def __init__(self, config: Optional[CSRFConfig] = None):
        self.config = config or CSRFConfig()
        self._tokens: dict = {}
        self._enabled = os.getenv("NXM_CSRF_ENABLED", "true").lower() in ("1", "true", "yes")
    
    def is_enabled(self) -> bool:
        return self._enabled
    
    def generate_token(self, session_id: str) -> str:
        """Generate a new CSRF token for a session"""
        token = secrets.token_urlsafe(self.config.token_length)
        self._tokens[token] = {
            "session_id": session_id,
            "created_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(hours=24)
        }
        return token
    
    def validate_token(self, token: str, session_id: str) -> bool:
        """Validate a CSRF token"""
        if not self._enabled:
            return True
        
        if not token or token not in self._tokens:
            return False
        
        token_data = self._tokens[token]
        
        if datetime.utcnow() > token_data["expires_at"]:
            del self._tokens[token]
            return False
        
        if token_data["session_id"] != session_id:
            return False
        
        return True
    
    def rotate_token(self, old_token: str, session_id: str) -> Optional[str]:
        """Rotate a CSRF token (invalidate old, generate new)"""
        if old_token in self._tokens:
            del self._tokens[old_token]
        return self.generate_token(session_id)
    
    def cleanup_expired(self):
        """Remove expired tokens"""
        now = datetime.utcnow()
        expired = [t for t, data in self._tokens.items() if data["expires_at"] <= now]
        for token in expired:
            del self._tokens[token]


_csrf_protection: Optional[CSRFProtection] = None


def get_csrf_protection() -> CSRFProtection:
    """Get the global CSRF protection instance"""
    global _csrf_protection
    if _csrf_protection is None:
        _csrf_protection = CSRFProtection()
    return _csrf_protection


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF middleware for FastAPI"""
    
    def __init__(self, app):
        super().__init__(app)
        self._csrf = get_csrf_protection()
    
    async def dispatch(self, request: Request, call_next):
        if not self._csrf.is_enabled():
            return await call_next(request)
        
        if request.method in ("GET", "HEAD", "OPTIONS"):
            response = await call_next(request)
            
            session_id = request.headers.get("X-Session-ID", "anonymous")
            csrf_token = self._csrf.generate_token(session_id)
            
            response.set_cookie(
                key=self._csrf.config.cookie_name,
                value=csrf_token,
                httponly=self._csrf.config.cookie_httponly,
                secure=self._csrf.config.cookie_secure,
                samesite=self._csrf.config.cookie_samesite,
                max_age=86400
            )
            return response
        
        csrf_token = request.headers.get(self._csrf.config.header_name)
        cookie_token = request.cookies.get(self._csrf.config.cookie_name)
        
        session_id = request.headers.get("X-Session-ID", "anonymous")
        
        token_to_validate = csrf_token or cookie_token
        
        if not self._csrf.validate_token(token_to_validate, session_id):
            return JSONResponse(
                status_code=403,
                content={"error": "CSRF validation failed"}
            )
        
        response = await call_next(request)
        return response
