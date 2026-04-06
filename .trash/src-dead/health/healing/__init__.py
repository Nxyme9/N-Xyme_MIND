"""
Healing — Distributed fault tolerance and self-recovery for N-Xyme MIND.

Modules:
- distributed_circuit_breaker: Resilience4j/Hystrix-style circuit breakers
  with sliding window metrics, state machine, audit trail, and recovery.
"""

from .distributed_circuit_breaker import (
    AuditEntry,
    CallRecord,
    CircuitBreakerConfig,
    CircuitOpenError,
    CircuitState,
    DistributedCircuitBreaker,
    DistributedCircuitBreakerRegistry,
    MaxRetriesExceededError,
    SlidingWindowMetrics,
    StateTransitionReason,
    get_distributed_breaker,
)

__all__ = [
    "AuditEntry",
    "CallRecord",
    "CircuitBreakerConfig",
    "CircuitOpenError",
    "CircuitState",
    "DistributedCircuitBreaker",
    "DistributedCircuitBreakerRegistry",
    "MaxRetriesExceededError",
    "SlidingWindowMetrics",
    "StateTransitionReason",
    "get_distributed_breaker",
]
