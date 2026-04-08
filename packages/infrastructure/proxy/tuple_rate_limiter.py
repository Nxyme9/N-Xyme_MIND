"""
Tuple Rate Limiter - Per (provider, model, vpn_ip, api_key) rate limiting with AIMD and EWMA.

Features:
- Independent rate bucket per unique tuple
- AIMD control: +1 RPM on success, ×0.5 on 429
- EWMA smoothing (alpha=0.3) for error rate
- Sliding window (60s) for rate tracking
"""

import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple


@dataclass
class RateBucket:
    """Rate bucket for a single (provider, model, vpn_ip, api_key) tuple."""
    provider: str
    model: str
    vpn_ip: str
    api_key: str
    
    # Current rate limits
    rpm: float = 10.0  # Starting RPM
    max_rpm: float = 50.0
    min_rpm: float = 1.0
    
    # AIMD parameters
    increase_delta: float = 1.0
    decrease_multiplier: float = 0.5
    
    # EWMA for error rate smoothing
    ewma_alpha: float = 0.3
    error_rate: float = 0.0
    
    # Tracking
    request_times: deque = field(default_factory=deque)
    success_count: int = 0
    error_count: int = 0
    last_429_time: float = 0.0
    cooldown_seconds: float = 5.0
    
    # Tokens for token bucket algorithm
    tokens: float = 10.0
    last_refill: float = field(default_factory=time.time)


class EWMA:
    """Exponential Weighted Moving Average for smoothing."""
    
    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self.value: Optional[float] = None
    
    def update(self, new_value: float) -> float:
        if self.value is None:
            self.value = new_value
        else:
            self.value = self.alpha * new_value + (1 - self.alpha) * self.value
        return self.value
    
    def get(self) -> float:
        return self.value if self.value is not None else 0.0


class TupleRateLimiter:
    """
    Per-tuple rate limiter with AIMD and EWMA smoothing.
    
    Each unique (provider, model, vpn_ip, api_key) tuple gets its own
    independent rate bucket with AIMD adaptation.
    """
    
    def __init__(
        self,
        default_rpm: float = 10.0,
        max_rpm: float = 50.0,
        min_rpm: float = 1.0,
        window_seconds: int = 60,
        increase_delta: float = 1.0,
        decrease_multiplier: float = 0.5,
        ewma_alpha: float = 0.3,
        cooldown_seconds: float = 5.0,
        increase_interval: int = 10  # Increase every N successes
    ):
        self.default_rpm = default_rpm
        self.max_rpm = max_rpm
        self.min_rpm = min_rpm
        self.window_seconds = window_seconds
        self.increase_delta = increase_delta
        self.decrease_multiplier = decrease_multiplier
        self.ewma_alpha = ewma_alpha
        self.cooldown_seconds = cooldown_seconds
        self.increase_interval = increase_interval
        
        self._buckets: Dict[Tuple[str, str, str, str], RateBucket] = {}
        self._lock = threading.RLock()
    
    def _make_key(self, provider: str, model: str, vpn_ip: str, api_key: str) -> Tuple[str, str, str, str]:
        """Create tuple key from components."""
        return (provider, model, vpn_ip or "", api_key or "")
    
    def _get_bucket(
        self,
        provider: str,
        model: str,
        vpn_ip: str,
        api_key: str,
        create: bool = True
    ) -> Optional[RateBucket]:
        """Get or create rate bucket for tuple."""
        key = self._make_key(provider, model, vpn_ip, api_key)
        
        with self._lock:
            if key not in self._buckets and create:
                self._buckets[key] = RateBucket(
                    provider=provider,
                    model=model,
                    vpn_ip=vpn_ip,
                    api_key=api_key,
                    rpm=self.default_rpm,
                    max_rpm=self.max_rpm,
                    min_rpm=self.min_rpm,
                    increase_delta=self.increase_delta,
                    decrease_multiplier=self.decrease_multiplier,
                    ewma_alpha=self.ewma_alpha,
                    cooldown_seconds=self.cooldown_seconds,
                    tokens=self.default_rpm / 60.0 * 10  # Initial tokens
                )
            return self._buckets.get(key)
    
    def _clean_old_requests(self, bucket: RateBucket):
        """Remove requests outside the sliding window."""
        now = time.time()
        cutoff = now - self.window_seconds
        
        while bucket.request_times and bucket.request_times[0] < cutoff:
            bucket.request_times.popleft()
    
    def _refill_tokens(self, bucket: RateBucket):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - bucket.last_refill
        
        # Add tokens proportional to RPM
        tokens_to_add = elapsed * (bucket.rpm / 60.0)
        bucket.tokens = min(bucket.rpm / 60.0 * 10, bucket.tokens + tokens_to_add)
        bucket.last_refill = now
    
    def acquire(
        self,
        provider: str,
        model: str,
        vpn_ip: str = "",
        api_key: str = ""
    ) -> Tuple[bool, float]:
        """
        Attempt to acquire a request slot.
        
        Returns:
            Tuple of (allowed, retry_after_seconds)
        """
        bucket = self._get_bucket(provider, model, vpn_ip, api_key)
        if bucket is None:
            return True, 0.0  # No bucket = allowed
        
        # Check cooldown
        now = time.time()
        if now - bucket.last_429_time < bucket.cooldown_seconds:
            return False, bucket.cooldown_seconds - (now - bucket.last_429_time)
        
        # Clean old requests and refill tokens
        self._clean_old_requests(bucket)
        self._refill_tokens(bucket)
        
        # Check if within rate limit
        if len(bucket.request_times) < int(bucket.rpm):
            bucket.request_times.append(now)
            bucket.tokens -= 1.0
            return True, 0.0
        
        # Rate limited
        return False, 1.0  # Retry after 1 second
    
    def record_success(
        self,
        provider: str,
        model: str,
        vpn_ip: str = "",
        api_key: str = ""
    ):
        """Record successful request - increase rate via AIMD."""
        bucket = self._get_bucket(provider, model, vpn_ip, api_key)
        if bucket is None:
            return
        
        with self._lock:
            bucket.success_count += 1
            
            # Additive increase every N successes
            if bucket.success_count % self.increase_interval == 0:
                new_rpm = min(bucket.max_rpm, bucket.rpm + bucket.increase_delta)
                bucket.rpm = new_rpm
    
    def record_rate_limit(
        self,
        provider: str,
        model: str,
        vpn_ip: str = "",
        api_key: str = ""
    ):
        """Record 429 response - decrease rate via AIMD."""
        bucket = self._get_bucket(provider, model, vpn_ip, api_key)
        if bucket is None:
            return
        
        with self._lock:
            bucket.error_count += 1
            bucket.last_429_time = time.time()
            
            # Multiplicative decrease
            new_rpm = max(bucket.min_rpm, bucket.rpm * bucket.decrease_multiplier)
            bucket.rpm = new_rpm
            
            # Reset tokens to prevent immediate retry
            bucket.tokens = 0.0
    
    def update_error_rate(
        self,
        provider: str,
        model: str,
        vpn_ip: str = "",
        api_key: str = ""
    ):
        """Update EWMA-smoothed error rate."""
        bucket = self._get_bucket(provider, model, vpn_ip, api_key)
        if bucket is None:
            return
        
        with self._lock:
            total = bucket.success_count + bucket.error_count
            if total > 0:
                raw_error_rate = bucket.error_count / total
                bucket.error_rate = bucket.ewma_alpha * raw_error_rate + \
                    (1 - bucket.ewma_alpha) * bucket.error_rate
    
    def get_stats(
        self,
        provider: str,
        model: str,
        vpn_ip: str = "",
        api_key: str = ""
    ) -> Dict:
        """Get statistics for a tuple."""
        bucket = self._get_bucket(provider, model, vpn_ip, api_key, create=False)
        if bucket is None:
            return {}
        
        with self._lock:
            return {
                "provider": bucket.provider,
                "model": bucket.model,
                "vpn_ip": bucket.vpn_ip,
                "api_key_id": bucket.api_key[:20] + "..." if len(bucket.api_key) > 20 else bucket.api_key,
                "rpm": bucket.rpm,
                "success_count": bucket.success_count,
                "error_count": bucket.error_count,
                "error_rate": bucket.error_rate,
                "requests_in_window": len(bucket.request_times)
            }
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get statistics for all tuples."""
        with self._lock:
            return {
                f"{k[0]}/{k[1]}": self.get_stats(k[0], k[1], k[2], k[3])
                for k in self._buckets.keys()
            }
    
    def set_rpm(
        self,
        provider: str,
        model: str,
        vpn_ip: str,
        api_key: str,
        rpm: float
    ):
        """Manually set RPM for a tuple (used by RateOptimizer)."""
        bucket = self._get_bucket(provider, model, vpn_ip, api_key)
        if bucket:
            with self._lock:
                bucket.rpm = max(self.min_rpm, min(self.max_rpm, rpm))