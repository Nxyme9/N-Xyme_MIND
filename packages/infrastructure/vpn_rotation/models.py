"""Data models for VPN rotation."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ProviderType(Enum):
    """Types of VPN providers supported."""
    PROTONVPN = "protonvpn"
    WIREPROXY = "wireproxy"
    SOCKS5 = "socks5"
    HTTP_PROXY = "http_proxy"
    CUSTOM = "custom"


class InstanceStatus(Enum):
    """Status of a VPN instance."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    UNHEALTHY = "unhealthy"
    RATE_LIMITED = "rate_limited"


@dataclass
class VPNEndpoint:
    """Represents a single VPN endpoint (IP:port pair)."""
    host: str
    port: int
    provider: str
    provider_type: ProviderType = ProviderType.CUSTOM
    country: str = "unknown"
    city: Optional[str] = None
    
    # Health metrics
    latency_ms: float = 999.0
    healthy: bool = True
    last_check: float = 0
    
    # Rate limiting
    rate_limited_until: float = 0
    quota_remaining: float = 100.0
    
    # Connection tracking
    active_connections: int = 0
    max_connections: int = 100
    
    # Instance reference
    instance_id: Optional[str] = None
    
    @property
    def is_rate_limited(self) -> bool:
        return time.time() < self.rate_limited_until
    
    @property
    def available_capacity(self) -> float:
        """0.0 = exhausted, 1.0 = fully available."""
        if not self.healthy or self.is_rate_limited:
            return 0.0
        conn_ratio = 1.0 - min(1.0, self.active_connections / max(1, self.max_connections))
        latency_score = max(0, 1.0 - (self.latency_ms / 500.0))
        return (conn_ratio * 0.6 + latency_score * 0.4)
    
    @property
    def score(self) -> float:
        """Lower is better for selection."""
        if not self.healthy:
            return 999999.0
        if self.is_rate_limited:
            return 999998.0
        return self.latency_ms
    
    def to_dict(self) -> dict:
        return {
            "host": self.host,
            "port": self.port,
            "provider": self.provider,
            "provider_type": self.provider_type.value,
            "country": self.country,
            "city": self.city,
            "latency_ms": round(self.latency_ms, 1),
            "healthy": self.healthy,
            "is_rate_limited": self.is_rate_limited,
            "available_capacity": round(self.available_capacity, 3),
        }


@dataclass
class RotationOutcome:
    """Outcome of a single routing decision for learning."""
    endpoint: VPNEndpoint
    latency_ms: float
    success: bool
    exit_ip: str = ""
    error_type: str = ""
    timestamp: float = field(default_factory=time.time)
    
    # Request details (for context)
    input_tokens: int = 0
    output_tokens: int = 0
    
    def to_record(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "provider": self.endpoint.provider,
            "host": self.endpoint.host,
            "port": self.endpoint.port,
            "exit_ip": self.exit_ip,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error_type": self.error_type,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


@dataclass
class ProviderConfig:
    """Configuration for a VPN provider."""
    name: str
    provider_type: ProviderType
    
    # Connection settings
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    
    # WireGuard settings (for WireProxy)
    private_key: Optional[str] = None
    public_key: Optional[str] = None
    endpoint: Optional[str] = None
    
    # Provider-specific
    api_key: Optional[str] = None
    config_file: Optional[str] = None
    
    # Limits
    max_instances: int = 8
    rate_limit_rpm: int = 80
    
    # Health check
    health_check_url: Optional[str] = None
    health_check_interval: float = 300.0
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "provider_type": self.provider_type.value,
            "host": self.host,
            "port": self.port,
            "max_instances": self.max_instances,
            "rate_limit_rpm": self.rate_limit_rpm,
        }
