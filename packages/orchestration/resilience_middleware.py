"""Resilience Middleware - Retry, circuit breaker, fallback chains."""

import logging
import time
from typing import Any, Callable, List, Optional

logger = logging.getLogger(__name__)


class RetryPolicy:
    """Retry policy with exponential backoff."""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 30.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with retry logic."""
        last_error = None
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                if attempt < self.max_retries:
                    delay = min(self.base_delay * (2 ** attempt), self.max_delay)
                    logger.warning(f"⚠️ Attempt {attempt + 1} failed: {e}, retrying in {delay:.1f}s")
                    time.sleep(delay)
                else:
                    logger.error(f"❌ All {self.max_retries + 1} attempts failed: {e}")
        raise last_error


class CircuitBreaker:
    """Circuit breaker pattern implementation."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker logic."""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info("🔄 Circuit breaker: HALF_OPEN")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info("✅ Circuit breaker: CLOSED")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.warning(f"⚠️ Circuit breaker: OPEN (failures: {self.failure_count})")
            raise e


class FallbackChain:
    """Fallback chain execution."""
    
    def __init__(self):
        self.fallbacks: List[Callable] = []
    
    def add_fallback(self, func: Callable):
        """Add a fallback function."""
        self.fallbacks.append(func)
    
    def execute(self, primary_func: Callable, *args, **kwargs) -> Any:
        """Execute primary function with fallback chain."""
        # Try primary
        try:
            return primary_func(*args, **kwargs)
        except Exception as e:
            logger.warning(f"⚠️ Primary failed: {e}, trying fallbacks")
        
        # Try fallbacks
        for i, fallback in enumerate(self.fallbacks):
            try:
                return fallback(*args, **kwargs)
            except Exception as e:
                logger.warning(f"⚠️ Fallback {i + 1} failed: {e}")
        
        raise Exception("All fallbacks failed")


class ResilienceMiddleware:
    """Combined resilience middleware."""
    
    def __init__(self, retry_policy: Optional[RetryPolicy] = None, 
                 circuit_breaker: Optional[CircuitBreaker] = None):
        self.retry_policy = retry_policy or RetryPolicy()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.fallback_chain = FallbackChain()
    
    def execute(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with full resilience stack."""
        return self.retry_policy.execute(
            lambda: self.circuit_breaker.execute(func, *args, **kwargs)
        )
    
    def add_fallback(self, func: Callable):
        """Add a fallback function."""
        self.fallback_chain.add_fallback(func)
