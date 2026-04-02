"""RFC 7807 Compliant Error Handler — Global error handling with context

Combines:
- Deprecated errors.py: ErrorCode enum, APIError hierarchy, HTTP status codes
- CATALYST error_handler.py: Traceback capture, context enrichment, error history

New features:
- RFC 7807 Problem Details format
- Circuit breaker integration
- Error severity levels
- Correlation ID support (X-Request-ID)
- Async-safe error history (ring buffer)
"""

import asyncio
import logging
import traceback
import uuid
from collections import deque
from enum import Enum
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ============================================================================
# Enums
# ============================================================================


class ErrorCode(str, Enum):
    """Standardized error codes for API responses"""

    # Authentication errors
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_EXPIRED_TOKEN = "AUTH_EXPIRED_TOKEN"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"

    # Validation errors
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_PARAMETER = "MISSING_PARAMETER"

    # Resource errors
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    RESOURCE_CONFLICT = "RESOURCE_CONFLICT"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Server errors
    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"

    # Circuit breaker
    CIRCUIT_OPEN = "CIRCUIT_OPEN"


class ErrorSeverity(str, Enum):
    """Error severity levels for logging and alerting"""

    CRITICAL = "CRITICAL"  # System-breaking, requires immediate attention
    ERROR = "ERROR"  # Operation failed, needs investigation
    WARNING = "WARNING"  # Degraded functionality, monitor closely
    INFO = "INFO"  # Informational, expected in some flows


# ============================================================================
# Default Messages
# ============================================================================

ERROR_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.AUTH_REQUIRED: "Authentication required. Please provide valid credentials.",
    ErrorCode.AUTH_INVALID_TOKEN: "Invalid authentication token.",
    ErrorCode.AUTH_EXPIRED_TOKEN: "Authentication token has expired.",
    ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS: "Insufficient permissions to perform this action.",
    ErrorCode.VALIDATION_ERROR: "Request validation failed.",
    ErrorCode.INVALID_PARAMETER: "Invalid parameter value.",
    ErrorCode.MISSING_PARAMETER: "Required parameter is missing.",
    ErrorCode.RESOURCE_NOT_FOUND: "The requested resource was not found.",
    ErrorCode.RESOURCE_ALREADY_EXISTS: "Resource already exists.",
    ErrorCode.RESOURCE_CONFLICT: "Resource conflict detected.",
    ErrorCode.RATE_LIMIT_EXCEEDED: "Rate limit exceeded. Please try again later.",
    ErrorCode.INTERNAL_SERVER_ERROR: "An internal server error occurred.",
    ErrorCode.SERVICE_UNAVAILABLE: "Service temporarily unavailable.",
    ErrorCode.EXTERNAL_SERVICE_ERROR: "External service error.",
    ErrorCode.CIRCUIT_OPEN: "Circuit breaker is open. Service temporarily unavailable.",
}

# HTTP status code mapping
ERROR_STATUS_CODES: Dict[ErrorCode, int] = {
    ErrorCode.AUTH_REQUIRED: 401,
    ErrorCode.AUTH_INVALID_TOKEN: 401,
    ErrorCode.AUTH_EXPIRED_TOKEN: 401,
    ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS: 403,
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.INVALID_PARAMETER: 400,
    ErrorCode.MISSING_PARAMETER: 400,
    ErrorCode.RESOURCE_NOT_FOUND: 404,
    ErrorCode.RESOURCE_ALREADY_EXISTS: 409,
    ErrorCode.RESOURCE_CONFLICT: 409,
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.INTERNAL_SERVER_ERROR: 500,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.EXTERNAL_SERVICE_ERROR: 502,
    ErrorCode.CIRCUIT_OPEN: 503,
}

# Severity mapping by error code
ERROR_SEVERITY: Dict[ErrorCode, ErrorSeverity] = {
    ErrorCode.AUTH_REQUIRED: ErrorSeverity.WARNING,
    ErrorCode.AUTH_INVALID_TOKEN: ErrorSeverity.WARNING,
    ErrorCode.AUTH_EXPIRED_TOKEN: ErrorSeverity.INFO,
    ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS: ErrorSeverity.WARNING,
    ErrorCode.VALIDATION_ERROR: ErrorSeverity.INFO,
    ErrorCode.INVALID_PARAMETER: ErrorSeverity.INFO,
    ErrorCode.MISSING_PARAMETER: ErrorSeverity.INFO,
    ErrorCode.RESOURCE_NOT_FOUND: ErrorSeverity.INFO,
    ErrorCode.RESOURCE_ALREADY_EXISTS: ErrorSeverity.INFO,
    ErrorCode.RESOURCE_CONFLICT: ErrorSeverity.WARNING,
    ErrorCode.RATE_LIMIT_EXCEEDED: ErrorSeverity.WARNING,
    ErrorCode.INTERNAL_SERVER_ERROR: ErrorSeverity.ERROR,
    ErrorCode.SERVICE_UNAVAILABLE: ErrorSeverity.ERROR,
    ErrorCode.EXTERNAL_SERVICE_ERROR: ErrorSeverity.ERROR,
    ErrorCode.CIRCUIT_OPEN: ErrorSeverity.ERROR,
}


# ============================================================================
# Base Error Class (RFC 7807 Problem Details)
# ============================================================================


class APIError(Exception):
    """Base API Error with RFC 7807 Problem Details serialization

    RFC 7807 fields:
    - type: URI reference identifying the problem type
    - title: Short human-readable summary
    - detail: Human-readable explanation specific to this occurrence
    - status: HTTP status code
    - instance: URI reference identifying the specific occurrence

    Extensions:
    - code: Application-specific error code
    - severity: Error severity level
    - correlation_id: Request correlation ID
    - context: Additional error context
    """

    def __init__(
        self,
        error_code: ErrorCode,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        status_code: Optional[int] = None,
        severity: Optional[ErrorSeverity] = None,
        correlation_id: Optional[str] = None,
        instance: Optional[str] = None,
        type_uri: Optional[str] = None,
    ):
        self.error_code = error_code
        self.message = message or ERROR_MESSAGES.get(error_code, "An error occurred")
        self.details = details or {}
        self.status_code = status_code or ERROR_STATUS_CODES.get(error_code, 500)
        self.severity = severity or ERROR_SEVERITY.get(error_code, ErrorSeverity.ERROR)
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.instance = instance
        self.type_uri = type_uri or f"https://api.nxyme.ai/problems/{error_code.value.lower()}"

        super().__init__(self.message)

    def to_problem_detail(self) -> Dict[str, Any]:
        problem = {
            "type": self.type_uri,
            "title": self.error_code.value.replace("_", " ").title(),
            "status": self.status_code,
            "detail": self.message,
            "code": self.error_code.value,
            "severity": self.severity.value,
            "correlation_id": self.correlation_id,
        }

        if self.instance:
            problem["instance"] = self.instance

        if self.details:
            problem["context"] = self.details

        return problem

    def to_dict(self) -> Dict[str, Any]:
        """Legacy format for backward compatibility"""
        return {
            "error": {
                "code": self.error_code.value,
                "message": self.message,
                "details": self.details,
            }
        }

    def get_headers(self) -> Dict[str, str]:
        """Get response headers for this error"""
        headers = {
            "Content-Type": "application/problem+json",
            "X-Request-ID": self.correlation_id,
        }
        return headers


# ============================================================================
# Error Subclasses
# ============================================================================


class NotFoundError(APIError):
    """Resource not found (404)"""

    def __init__(
        self,
        resource: str,
        identifier: Any,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            message=f"{resource} not found: {identifier}",
            details={"resource": resource, "identifier": str(identifier)},
            correlation_id=correlation_id,
        )


class ValidationError(APIError):
    """Validation error (400)"""

    def __init__(
        self,
        field: str,
        message: str,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            error_code=ErrorCode.VALIDATION_ERROR,
            message=f"Validation error: {field}",
            details={"field": field, "message": message},
            correlation_id=correlation_id,
        )


class UnauthorizedError(APIError):
    """Authentication required (401)"""

    def __init__(
        self,
        message: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            error_code=ErrorCode.AUTH_REQUIRED,
            message=message,
            correlation_id=correlation_id,
        )


class ForbiddenError(APIError):
    """Insufficient permissions (403)"""

    def __init__(
        self,
        message: Optional[str] = None,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            error_code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
            message=message,
            correlation_id=correlation_id,
        )


class ConflictError(APIError):
    """Resource conflict (409)"""

    def __init__(
        self,
        message: str,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            error_code=ErrorCode.RESOURCE_CONFLICT,
            message=message,
            correlation_id=correlation_id,
        )


class RateLimitError(APIError):
    """Rate limit exceeded (429)"""

    def __init__(
        self,
        retry_after: int = 60,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message="Rate limit exceeded. Please try again later.",
            details={"retry_after": retry_after},
            correlation_id=correlation_id,
        )
        self.retry_after = retry_after

    def get_headers(self) -> Dict[str, str]:
        """Get response headers including rate limit headers"""
        headers = super().get_headers()
        headers.update(
            {
                "Retry-After": str(self.retry_after),
                "X-RateLimit-Limit": str(self.retry_after),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(self.retry_after),
            }
        )
        return headers


class CircuitOpenError(APIError):
    """Circuit breaker is open (503)"""

    def __init__(
        self,
        service: str,
        retry_after: int = 30,
        correlation_id: Optional[str] = None,
    ):
        super().__init__(
            error_code=ErrorCode.CIRCUIT_OPEN,
            message=f"Circuit breaker open for {service}. Retry after {retry_after}s.",
            details={"service": service, "retry_after": retry_after},
            correlation_id=correlation_id,
        )
        self.retry_after = retry_after

    def get_headers(self) -> Dict[str, str]:
        """Get response headers including retry-after"""
        headers = super().get_headers()
        headers["Retry-After"] = str(self.retry_after)
        return headers


# ============================================================================
# Error History Entry
# ============================================================================


@dataclass
class ErrorEntry:
    """Single error history entry"""

    error_type: str
    message: str
    severity: str
    code: Optional[str]
    traceback: Optional[str]
    context: Dict[str, Any]
    correlation_id: Optional[str]
    timestamp: float = field(default_factory=lambda: __import__("time").time())


# ============================================================================
# Error Handler (Async-Safe)
# ============================================================================


class ErrorHandler:
    """Global error handler with context enrichment and async-safe history

    Features:
    - Error history with ring buffer (max 1000 entries)
    - Async-safe with asyncio.Lock
    - Context enrichment
    - Traceback capture
    - Query by type, severity, code
    - Backward compatible with original ErrorHandler interface
    """

    MAX_HISTORY = 1000

    def __init__(self):
        self._errors: deque[ErrorEntry] = deque(maxlen=self.MAX_HISTORY)
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        """Lazy-initialize the async lock"""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def handle(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle an error (sync version for backward compatibility)"""
        error_type = type(error).__name__
        message = str(error)
        tb = traceback.format_exc() if traceback.format_exc() != "NoneType: None\n" else None

        # Extract metadata if it's an APIError
        code = None
        severity = ErrorSeverity.ERROR.value
        correlation_id = None

        if isinstance(error, APIError):
            code = error.error_code.value
            severity = error.severity.value
            correlation_id = error.correlation_id

        entry = ErrorEntry(
            error_type=error_type,
            message=message,
            severity=severity,
            code=code,
            traceback=tb,
            context=context or {},
            correlation_id=correlation_id,
        )

        self._errors.append(entry)

        # Log based on severity
        log_msg = f"[{severity}] {error_type}: {message}"
        if correlation_id:
            log_msg += f" (correlation_id={correlation_id})"

        if severity == ErrorSeverity.CRITICAL.value:
            logger.critical(log_msg)
        elif severity == ErrorSeverity.ERROR.value:
            logger.error(log_msg)
        elif severity == ErrorSeverity.WARNING.value:
            logger.warning(log_msg)
        else:
            logger.info(log_msg)

        return self._entry_to_dict(entry)

    async def handle_async(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle an error (async-safe version)"""
        async with self._get_lock():
            return self.handle(error, context)

    def _entry_to_dict(self, entry: ErrorEntry) -> Dict[str, Any]:
        """Convert ErrorEntry to dict"""
        result: Dict[str, Any] = {
            "type": entry.error_type,
            "message": entry.message,
            "severity": entry.severity,
            "context": entry.context,
            "timestamp": entry.timestamp,
        }
        if entry.code:
            result["code"] = entry.code
        if entry.traceback:
            result["traceback"] = entry.traceback
        if entry.correlation_id:
            result["correlation_id"] = entry.correlation_id
        return result

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent errors (backward compatible)"""
        entries = list(self._errors)[-limit:]
        return [self._entry_to_dict(e) for e in entries]

    def get_by_type(self, error_type: str) -> List[Dict[str, Any]]:
        """Get errors by type name (backward compatible)"""
        return [self._entry_to_dict(e) for e in self._errors if e.error_type == error_type]

    def get_by_severity(self, severity: ErrorSeverity) -> List[Dict[str, Any]]:
        """Get errors by severity level"""
        return [self._entry_to_dict(e) for e in self._errors if e.severity == severity.value]

    def get_by_code(self, code: ErrorCode) -> List[Dict[str, Any]]:
        """Get errors by error code"""
        return [self._entry_to_dict(e) for e in self._errors if e.code == code.value]

    def get_by_correlation_id(self, correlation_id: str) -> List[Dict[str, Any]]:
        """Get all errors for a correlation ID"""
        return [self._entry_to_dict(e) for e in self._errors if e.correlation_id == correlation_id]

    def clear(self):
        """Clear error history (backward compatible)"""
        self._errors.clear()

    @property
    def count(self) -> int:
        """Get current error count"""
        return len(self._errors)

    def get_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        severity_counts = {}
        code_counts = {}

        for entry in self._errors:
            severity_counts[entry.severity] = severity_counts.get(entry.severity, 0) + 1
            if entry.code:
                code_counts[entry.code] = code_counts.get(entry.code, 0) + 1

        return {
            "total": len(self._errors),
            "by_severity": severity_counts,
            "by_code": code_counts,
        }


# ============================================================================
# HTTP Response Helpers (Framework-Agnostic)
# ============================================================================


def create_problem_response(
    error: APIError,
) -> Dict[str, Any]:
    """Create RFC 7807 Problem Details response

    Returns dict with 'status', 'headers', 'body' for framework integration.
    """
    return {
        "status": error.status_code,
        "headers": error.get_headers(),
        "body": error.to_problem_detail(),
    }


def create_legacy_response(
    error: APIError,
) -> Dict[str, Any]:
    """Create legacy error response format (backward compatible)"""
    return {
        "status": error.status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-Request-ID": error.correlation_id,
        },
        "body": error.to_dict(),
    }


def add_rate_limit_headers(
    response: Any,
    limit: int,
    remaining: int,
    reset: int,
) -> None:
    """Add standard rate limit headers to response (backward compatible)"""
    if hasattr(response, "headers"):
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset)


def create_error_response(
    error_code: ErrorCode,
    message: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    status_code: Optional[int] = None,
    correlation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create standardized error response dict (backward compatible, enhanced)"""
    error = APIError(
        error_code=error_code,
        message=message,
        details=details,
        status_code=status_code,
        correlation_id=correlation_id,
    )
    return {
        "error": error.to_dict()["error"],
        "status_code": error.status_code,
    }


# ============================================================================
# FastAPI Integration (Optional)
# ============================================================================


async def api_error_handler(request, exc: APIError):
    """Global exception handler for FastAPI

    Usage:
        from fastapi import FastAPI
        from fastapi.responses import JSONResponse

        app = FastAPI()

        @app.exception_handler(APIError)
        async def handle_api_error(request, exc):
            return await api_error_handler(request, exc)
    """
    try:
        from fastapi.responses import JSONResponse
    except ImportError:
        raise ImportError(
            "FastAPI is required for api_error_handler. Install with: pip install fastapi"
        )

    logger.warning(
        f"API Error: {exc.error_code.value} - {exc.message}",
        extra={
            "path": str(request.url),
            "method": request.method,
            "error_code": exc.error_code.value,
            "correlation_id": exc.correlation_id,
            "severity": exc.severity.value,
            "details": exc.details,
        },
    )

    response = JSONResponse(
        status_code=exc.status_code,
        content=exc.to_problem_detail(),
    )

    # Set headers
    for key, value in exc.get_headers().items():
        response.headers[key] = value

    return response


# ============================================================================
# Module-Level Singleton
# ============================================================================

# Global error handler instance for convenience
_global_handler: Optional[ErrorHandler] = None


def get_handler() -> ErrorHandler:
    """Get or create global error handler instance"""
    global _global_handler
    if _global_handler is None:
        _global_handler = ErrorHandler()
    return _global_handler


def handle_error(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convenience function to handle error with global handler"""
    return get_handler().handle(error, context)


async def handle_error_async(
    error: Exception,
    context: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Convenience function to handle error async with global handler"""
    return await get_handler().handle_async(error, context)
