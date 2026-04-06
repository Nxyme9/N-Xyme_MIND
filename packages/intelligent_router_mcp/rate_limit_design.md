# Rate Limit Anticipation & Management System Design

## Overview

This document describes a comprehensive rate limit management system for the Intelligent Router MCP. The system provides proactive rate limit detection, automatic retry with backoff, circuit breaker patterns, and request queuing.

## Architecture Components

### 1. RateLimitPredictor

**Purpose**: Detect approaching rate limits BEFORE hitting them using sliding window analytics.

**Location**: `packages/intelligent_router_mcp/__init__.py`

```python
class RateLimitPredictor:
    """Predicts rate limit exhaustion using sliding window analysis."""
    
    def __init__(
        self,
        warning_threshold: float = 0.80,  # Warn at 80% usage
        critical_threshold: float = 0.95,  # Critical at 95%
        window_seconds: int = 60,          # 1-minute sliding window
    ):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.window_seconds = window_seconds
        self._request_timestamps: Dict[str, List[float]] = {}  # session_id -> timestamps
        self._token_counts: Dict[str, List[int]] = {}          # session_id -> token counts
        self._lock = threading.Lock()
    
    def record_request(self, session_id: str, tokens: int = 0) -> None:
        """Record request for sliding window calculation."""
        now = time.time()
        with self._lock:
            if session_id not in self._request_timestamps:
                self._request_timestamps[session_id] = []
                self._token_counts[session_id] = []
            
            # Add current request
            self._request_timestamps[session_id].append(now)
            self._token_counts[session_id].append(tokens)
            
            # Prune old entries outside window
            cutoff = now - self.window_seconds
            self._request_timestamps[session_id] = [
                ts for ts in self._request_timestamps[session_id] if ts > cutoff
            ]
            self._token_counts[session_id] = self._token_counts[session_id][
                -len(self._request_timestamps[session_id]):
            ]
    
    def get_status(self, session_id: str, rpm_limit: int, tpm_limit: int) -> dict:
        """Get current rate limit status with prediction."""
        with self._lock:
            timestamps = self._request_timestamps.get(session_id, [])
            tokens = self._token_counts.get(session_id, [])
            
            current_rpm = len(timestamps)
            current_tpm = sum(tokens)
            
            rpm_ratio = current_rpm / rpm_limit if rpm_limit > 0 else 0
            tpm_ratio = current_tpm / tpm_limit if tpm_limit > 0 else 0
            
            # Predict time to exhaustion
            if current_rpm > 0:
                time_to_rpm_limit = self._estimate_time_to_limit(
                    current_rpm, rpm_limit, self.window_seconds
                )
            else:
                time_to_rpm_limit = float('inf')
            
            if current_tpm > 0:
                time_to_tpm_limit = self._estimate_time_to_limit(
                    current_tpm, tpm_limit, self.window_seconds
                )
            else:
                time_to_tpm_limit = float('inf')
            
            return {
                "session_id": session_id,
                "current_rpm": current_rpm,
                "rpm_limit": rpm_limit,
                "rpm_usage_pct": round(rpm_ratio * 100, 1),
                "current_tpm": current_tpm,
                "tpm_limit": tpm_limit,
                "tpm_usage_pct": round(tpm_ratio * 100, 1),
                "warning_level": self._get_warning_level(rpm_ratio, tpm_ratio),
                "time_to_rpm_limit_sec": round(time_to_rpm_limit, 1) if time_to_rpm_limit < float('inf') else None,
                "time_to_tpm_limit_sec": round(time_to_tpm_limit, 1) if time_to_tpm_limit < float('inf') else None,
                "should_throttle": rpm_ratio >= self.warning_threshold or tpm_ratio >= self.warning_threshold,
                "should_reject": rpm_ratio >= 1.0 or tpm_ratio >= 1.0,
            }
    
    def _estimate_time_to_limit(self, current: int, limit: int, window: int) -> float:
        """Estimate seconds until limit is reached."""
        if current == 0:
            return float('inf')
        rate_per_second = current / window
        remaining = limit - current
        if rate_per_second <= 0:
            return float('inf')
        return remaining / rate_per_second
    
    def _get_warning_level(self, rpm_ratio: float, tpm_ratio: float) -> str:
        """Determine warning level based on usage ratios."""
        max_ratio = max(rpm_ratio, tpm_ratio)
        if max_ratio >= self.critical_threshold:
            return "critical"
        elif max_ratio >= self.warning_threshold:
            return "warning"
        else:
            return "normal"
```

**Integration with TokenTunnel**:
- TokenTunnel calls `RateLimitPredictor.record_request()` on each request
- Before executing request, check `RateLimitPredictor.get_status()` for throttling decision

---

### 2. RetryManager

**Purpose**: Automatic retry with exponential backoff + jitter.

```python
class RetryManager:
    """Manages retry logic with exponential backoff and jitter."""
    
    def __init__(
        self,
        max_retries: int = 3,
        base_delay_ms: int = 500,
        max_delay_ms: int = 10000,
        jitter_factor: float = 0.2,  # ±20% jitter
        retry_on_errors: List[str] = None,
    ):
        self.max_retries = max_retries
        self.base_delay_ms = base_delay_ms
        self.max_delay_ms = max_delay_ms
        self.jitter_factor = jitter_factor
        self.retry_on_errors = retry_on_errors or [
            "rate_limit",
            "timeout",
            "connection_error",
            "temporary_failure",
            "429",
            "503",
            "504",
        ]
        self._retry_counts: Dict[str, int] = {}  # request_id -> retry count
        self._lock = threading.Lock()
    
    def should_retry(
        self,
        request_id: str,
        error_type: str,
        attempt: int,
    ) -> bool:
        """Determine if request should be retried."""
        if attempt >= self.max_retries:
            return False
        
        error_lower = error_type.lower()
        return any(err in error_lower for err in self.retry_on_errors)
    
    def get_delay_ms(self, attempt: int, error_type: str = "") -> int:
        """Calculate delay with exponential backoff + jitter."""
        # Exponential: base_delay * 2^attempt
        delay = self.base_delay_ms * (2 ** attempt)
        
        # Cap at max_delay
        delay = min(delay, self.max_delay_ms)
        
        # Add jitter
        import random
        jitter = delay * self.jitter_factor * (2 * random.random() - 1)
        delay = int(delay + jitter)
        
        # Adjust for specific error types
        if "rate_limit" in error_type.lower() or "429" in error_type:
            # Longer delay for rate limits
            delay = int(delay * 1.5)
        
        return max(0, delay)
    
    def execute_with_retry(
        self,
        func: Callable,
        request_id: str,
        error_handler: Callable[[Exception], str] = None,
    ) -> Tuple[Any, str, dict]:
        """
        Execute function with retry logic.
        
        Returns: (result, status, metadata)
        - status: "success", "retry_exhausted", "non_retryable_error"
        - metadata: {"attempts": N, "last_error": str, "total_delay_ms": int}
        """
        metadata = {"attempts": 0, "last_error": None, "total_delay_ms": 0}
        
        for attempt in range(self.max_retries + 1):
            metadata["attempts"] = attempt + 1
            
            try:
                result = func()
                if attempt > 0:
                    return result, "success_after_retry", metadata
                return result, "success", metadata
            
            except Exception as e:
                metadata["last_error"] = str(e)
                error_type = error_handler(e) if error_handler else self._classify_error(e)
                
                if not self.should_retry(request_id, error_type, attempt):
                    return None, "non_retryable_error", metadata
                
                # Calculate and apply delay
                delay_ms = self.get_delay_ms(attempt, error_type)
                metadata["total_delay_ms"] += delay_ms
                time.sleep(delay_ms / 1000)
        
        return None, "retry_exhausted", metadata
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error type from exception."""
        error_str = str(error).lower()
        if "429" in error_str or "rate limit" in error_str:
            return "rate_limit"
        elif "timeout" in error_str:
            return "timeout"
        elif "connection" in error_str:
            return "connection_error"
        elif "503" in error_str or "504" in error_str:
            return "temporary_failure"
        return "unknown"
```

---

### 3. CircuitBreaker

**Purpose**: Protect proxies from cascading failures by temporarily banning unhealthy proxies.

```python
class CircuitBreaker:
    """Circuit breaker pattern for proxy health management."""
    
    class State:
        CLOSED = "closed"      # Normal operation
        OPEN = "open"          # Failing, reject requests
        HALF_OPEN = "half_open"  # Testing recovery
    
    def __init__(
        self,
        failure_threshold: int = 5,    # Open after N failures
        success_threshold: int = 2,    # Close after N successes
        timeout_seconds: float = 30.0,  # Auto-transition to half-open
        ban_duration_seconds: float = 60.0,  # How long to ban
    ):
        self.failure_threshold = failure_threshold
        self.success_threshold = success_threshold
        self.timeout_seconds = timeout_seconds
        self.ban_duration_seconds = ban_duration_seconds
        
        # Per-proxy state
        self._proxy_states: Dict[str, dict] = {}  # proxy_key -> state dict
        self._lock = threading.Lock()
    
    def _get_proxy_state(self, proxy_key: str) -> dict:
        """Get or create state for proxy."""
        if proxy_key not in self._proxy_states:
            self._proxy_states[proxy_key] = {
                "state": self.State.CLOSED,
                "failure_count": 0,
                "success_count": 0,
                "last_failure_time": 0.0,
                "opened_at": 0.0,
                "banned_until": 0.0,
            }
        return self._proxy_states[proxy_key]
    
    def record_success(self, proxy_key: str) -> bool:
        """
        Record success for proxy.
        Returns True if proxy state changed to allow requests.
        """
        with self._lock:
            state = self._get_proxy_state(proxy_key)
            
            if state["state"] == self.State.HALF_OPEN:
                state["success_count"] += 1
                if state["success_count"] >= self.success_threshold:
                    # Recovered - close circuit
                    state["state"] = self.State.CLOSED
                    state["failure_count"] = 0
                    state["success_count"] = 0
                    state["banned_until"] = 0.0
                    return True
            elif state["state"] == self.State.CLOSED:
                # Reset failure count on success
                state["failure_count"] = 0
            
            return state["state"] != self.State.OPEN
    
    def record_failure(self, proxy_key: str) -> bool:
        """
        Record failure for proxy.
        Returns True if proxy should be banned.
        """
        with self._lock:
            state = self._get_proxy_state(proxy_key)
            now = time.time()
            
            state["failure_count"] += 1
            state["last_failure_time"] = now
            
            if state["state"] == self.State.CLOSED:
                if state["failure_count"] >= self.failure_threshold:
                    # Open circuit - ban proxy
                    state["state"] = self.State.OPEN
                    state["opened_at"] = now
                    state["banned_until"] = now + self.ban_duration_seconds
                    return True
            elif state["state"] == self.State.HALF_OPEN:
                # Failed during recovery - reopen
                state["state"] = self.State.OPEN
                state["opened_at"] = now
                state["banned_until"] = now + self.ban_duration_seconds
                return True
            
            return False
    
    def can_request(self, proxy_key: str) -> Tuple[bool, str]:
        """
        Check if proxy can accept requests.
        Returns (allowed, reason).
        """
        with self._lock:
            state = self._get_proxy_state(proxy_key)
            now = time.time()
            
            # Check explicit ban
            if state["banned_until"] > now:
                return False, f"banned_until_{state['banned_until']}"
            
            # Check timeout - transition to half-open
            if state["state"] == self.State.OPEN:
                if now - state["opened_at"] >= self.timeout_seconds:
                    state["state"] = self.State.HALF_OPEN
                    state["success_count"] = 0
                    return True, "half_open_recovery"
            
            if state["state"] == self.State.OPEN:
                return False, "circuit_open"
            
            return True, "ok"
    
    def get_status(self, proxy_key: str = None) -> dict:
        """Get circuit breaker status."""
        with self._lock:
            if proxy_key:
                state = self._get_proxy_state(proxy_key)
                return {
                    "proxy": proxy_key,
                    "state": state["state"],
                    "failure_count": state["failure_count"],
                    "success_count": state["success_count"],
                    "banned_until": state["banned_until"],
                }
            
            return {
                proxy: {
                    "state": s["state"],
                    "failures": s["failure_count"],
                    "banned_until": s["banned_until"],
                }
                for proxy, s in self._proxy_states.items()
            }
    
    def reset(self, proxy_key: str = None) -> None:
        """Reset circuit breaker for proxy or all."""
        with self._lock:
            if proxy_key and proxy_key in self._proxy_states:
                self._proxy_states[proxy_key] = {
                    "state": self.State.CLOSED,
                    "failure_count": 0,
                    "success_count": 0,
                    "last_failure_time": 0.0,
                    "opened_at": 0.0,
                    "banned_until": 0.0,
                }
            elif not proxy_key:
                self._proxy_states.clear()
```

**Integration with VPNIPPool**:
- CircuitBreaker coordinates with VPNIPPool to track proxy health
- When CircuitBreaker bans a proxy, VPNIPPool marks it unavailable
- After cooldown, CircuitBreaker allows half-open testing

---

### 4. RequestQueue

**Purpose**: Hold requests during cooldown periods and auto-dispatch when ready.

```python
class RequestQueue:
    """Queue requests for rate-limited resources with auto-dispatch."""
    
    def __init__(
        self,
        max_queue_size: int = 100,
        max_wait_seconds: float = 60.0,
        dispatch_interval_ms: int = 100,  # Check queue every 100ms
    ):
        self.max_queue_size = max_queue_size
        self.max_wait_seconds = max_wait_seconds
        self.dispatch_interval_ms = dispatch_interval_ms
        
        self._queues: Dict[str, List[dict]] = {}  # resource_key -> request queue
        self._lock = threading.Lock()
        self._dispatch_thread: Optional[threading.Thread] = None
        self._running = False
        self._dispatch_callback: Optional[Callable] = None
    
    def set_dispatch_callback(self, callback: Callable[[dict], Any]) -> None:
        """Set callback to execute queued requests."""
        self._dispatch_callback = callback
    
    def enqueue(
        self,
        resource_key: str,
        request: dict,
        priority: int = 0,
    ) -> Tuple[bool, str]:
        """
        Add request to queue.
        Returns (success, message).
        """
        with self._lock:
            if resource_key not in self._queues:
                self._queues[resource_key] = []
            
            if len(self._queues[resource_key]) >= self.max_queue_size:
                return False, "queue_full"
            
            # Add with timestamp for timeout tracking
            self._queues[resource_key].append({
                **request,
                "enqueued_at": time.time(),
                "priority": priority,
            })
            
            # Sort by priority (higher first), then by enqueued_at
            self._queues[resource_key].sort(
                key=lambda x: (-x["priority"], x["enqueued_at"])
            )
            
            return True, "enqueued"
    
    def get_queue_status(self, resource_key: str = None) -> dict:
        """Get queue status."""
        with self._lock:
            if resource_key:
                queue = self._queues.get(resource_key, [])
                return {
                    "resource": resource_key,
                    "size": len(queue),
                    "max_size": self.max_queue_size,
                    "oldest_request_age_sec": (
                        time.time() - queue[0]["enqueued_at"] if queue else 0
                    ),
                }
            
            return {
                resource: len(q)
                for resource, q in self._queues.items()
            }
    
    def start_dispatcher(self) -> None:
        """Start background dispatcher."""
        if self._running:
            return
        
        self._running = True
        self._dispatch_thread = threading.Thread(
            target=self._dispatch_loop,
            daemon=True,
        )
        self._dispatch_thread.start()
    
    def stop_dispatcher(self) -> None:
        """Stop background dispatcher."""
        self._running = False
        if self._dispatch_thread:
            self._dispatch_thread.join(timeout=2.0)
    
    def _dispatch_loop(self) -> None:
        """Background loop to dispatch queued requests."""
        while self._running:
            self._dispatch_ready_requests()
            time.sleep(self.dispatch_interval_ms / 1000)
    
    def _dispatch_ready_requests(self) -> None:
        """Check and dispatch ready requests."""
        with self._lock:
            for resource_key, queue in list(self._queues.items()):
                if not queue:
                    continue
                
                # Peek at first request
                request = queue[0]
                
                # Check if ready (rate limit may have lifted)
                ready, reason = self._check_ready(resource_key, request)
                
                if ready:
                    # Remove from queue and dispatch
                    queue.pop(0)
                    if self._dispatch_callback:
                        try:
                            self._dispatch_callback(request)
                        except Exception as e:
                            # Log error but continue
                            pass
    
    def _check_ready(self, resource_key: str, request: dict) -> Tuple[bool, str]:
        """
        Check if request is ready to dispatch.
        Override this to implement custom readiness logic.
        """
        # Default: always ready after brief delay
        age = time.time() - request["enqueued_at"]
        if age > self.max_wait_seconds:
            return False, "timeout"
        
        # Call external check if provided
        # This would integrate with RateLimitPredictor
        return True, "ready"


class ThrottledRequestExecutor:
    """Executes requests with throttling based on rate limit prediction."""
    
    def __init__(
        self,
        rate_predictor: RateLimitPredictor,
        request_queue: RequestQueue,
        token_tunnel: TokenTunnel,
    ):
        self.predictor = rate_predictor
        self.queue = request_queue
        self.token_tunnel = token_tunnel
    
    def execute(
        self,
        session_id: str,
        tokens_needed: int,
        executor: Callable,
    ) -> Any:
        """Execute request with throttling."""
        # Check rate limit status
        status = self.predictor.get_status(
            session_id,
            self.token_tunnel.rpm_limit,
            self.token_tunnel.tpm_limit,
        )
        
        if status["should_reject"]:
            # Rate limit hit - queue request
            self.queue.enqueue(
                f"session_{session_id}",
                {"session_id": session_id, "tokens": tokens_needed},
                priority=1,
            )
            raise RateLimitExceededError("Rate limit reached, request queued")
        
        if status["should_throttle"]:
            # Approaching limit - throttle by adding delay
            time.sleep(0.1)  # Brief throttle
        
        # Execute
        result = executor()
        
        # Record for prediction
        self.predictor.record_request(session_id, tokens_needed)
        self.token_tunnel.record_request(session_id, tokens_needed)
        
        return result
```

---

## Integration Architecture

### System State Machine

```
┌─────────────────────────────────────────────────────────────────┐
│                     REQUEST FLOW                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. ROUTER.select_route()                                       │
│         ↓                                                        │
│  2. RATE_LIMIT_PREDICTOR.get_status()                           │
│         ↓                                                        │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  Status Check:                                         │     │
│  │  - should_reject: Queue request, return error          │     │
│  │  - should_throttle: Add delay, continue                │     │
│  │  - normal: Proceed immediately                         │     │
│  └─────────────────────────────────────────────────────────┘     │
│         ↓                                                        │
│  3. CIRCUIT_BREAKER.can_request(proxy)                          │
│         ↓                                                        │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  Circuit State:                                        │     │
│  │  - CLOSED: Normal operation                            │     │
│  │  - OPEN: Skip proxy, select alternative               │     │
│  │  - HALF_OPEN: Allow test request                      │     │
│  └─────────────────────────────────────────────────────────┘     │
│         ↓                                                        │
│  4. EXECUTE_REQUEST via TokenTunnel                              │
│         ↓                                                        │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │  Result:                                               │     │
│  │  - Success: record_success() → CircuitBreaker.record_success()│
│  │  - Rate Limited: RetryManager.with_retry() → circuit.record_failure()│
│  │  - Other Error: RetryManager.with_retry() or fail      │     │
│  └─────────────────────────────────────────────────────────┘     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Class Relationships

```
┌──────────────────────────────────────────────────────────────────┐
│                        INTEGRATION DIAGRAM                       │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│   ┌─────────────┐    ┌──────────────────┐    ┌─────────────┐   │
│   │   Router    │───▶│ RateLimitPredictor│◀───│ TokenTunnel │   │
│   └─────────────┘    └──────────────────┘    └─────────────┘   │
│         │                     │                      │            │
│         ▼                     ▼                      ▼            │
│   ┌─────────────┐    ┌──────────────────┐    ┌─────────────┐   │
│   │ VPNIPPool   │◀───│  CircuitBreaker  │───▶│  RetryManager│   │
│   └─────────────┘    └──────────────────┘    └─────────────┘   │
│         │                     │                      │            │
│         ▼                     ▼                      ▼            │
│   ┌─────────────┐    ┌──────────────────┐    ┌─────────────┐   │
│   │   VPNIP     │    │    RequestQueue  │    │  Learning   │   │
│   └─────────────┘    └──────────────────┘    │   Engine    │   │
│                                               └─────────────┘   │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Integration Points

| Component | Integrates With | Method |
|-----------|-----------------|--------|
| RateLimitPredictor | TokenTunnel | `record_request()`, `get_status()` |
| CircuitBreaker | VPNIPPool | `can_request()`, `record_success/failure()` |
| RetryManager | Router, CircuitBreaker | `execute_with_retry()` |
| RequestQueue | RateLimitPredictor | `enqueue()`, dispatch callback |

---

## Configuration

```python
# Rate limit system configuration
RATE_LIMIT_CONFIG = {
    # Prediction thresholds
    "warning_threshold": 0.80,      # Start throttling at 80%
    "critical_threshold": 0.95,    # Critical at 95%
    "window_seconds": 60,          # Sliding window size
    
    # Retry configuration
    "max_retries": 3,
    "base_delay_ms": 500,
    "max_delay_ms": 10000,
    "jitter_factor": 0.2,
    
    # Circuit breaker
    "failure_threshold": 5,        # Open after 5 failures
    "success_threshold": 2,        # Close after 2 successes
    "circuit_timeout_seconds": 30, # Test recovery after 30s
    "ban_duration_seconds": 60,    # Ban for 60s
    
    # Request queue
    "max_queue_size": 100,
    "max_wait_seconds": 60,
    "dispatch_interval_ms": 100,
}
```

---

## Implementation Checklist

1. **RateLimitPredictor** - ✅ Designed
   - Sliding window tracking
   - Usage percentage calculation
   - Time-to-limit prediction
   - Warning level determination

2. **RetryManager** - ✅ Designed
   - Exponential backoff + jitter
   - Configurable max retries
   - Error classification
   - Non-retryable error handling

3. **CircuitBreaker** - ✅ Designed
   - State machine (CLOSED/OPEN/HALF_OPEN)
   - Auto-recovery after timeout
   - Banned proxy tracking
   - Integration with VPNIPPool

4. **RequestQueue** - ✅ Designed
   - Priority queuing
   - Auto-dispatch on rate limit lift
   - Timeout handling
   - Background dispatcher

5. **Integration** - TODO
   - Wire RateLimitPredictor to TokenTunnel
   - Wire CircuitBreaker to VPNIPPool
   - Wire RetryManager to Router
   - Wire RequestQueue to main flow

---

## Files Modified

- `packages/intelligent_router_mcp/__init__.py` - Add new classes
- No new files required - all in single module per existing pattern