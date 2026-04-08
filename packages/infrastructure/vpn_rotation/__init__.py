"""
Unified VPN/IP Rotation Module

ARCHITECTURE OVERVIEW:
======================
This module consolidates multiple VPN/IP rotation sources:
- rotator.py (HTTP CONNECT proxy with SOCKS5 backends)
- socks5-server.py (Basic SOCKS5 implementation)
- wireproxy-manager.sh (WireProxy instance management)
- Provider plugins (ProtonVPN, custom)
- Learning engine (Q-Learning routing + SQLite outcomes)

KEY COMPONENTS:
==============
1. VPNRotationManager - Main orchestration class
2. ProviderRegistry - Plugin-based provider abstraction
3. WireProxyManager - Dynamic WireProxy instance spawning
4. HealthMonitor - Exit IP detection + health checks
5. QLearningRouter - Self-learning routing with weighted selection

USAGE:
======
    from packages.infrastructure.vpn_rotation import vpn_rotation_manager
    
    # Get a rotating endpoint
    endpoint = vpn_rotation_manager.get_endpoint()
    print(f"Using: {endpoint.host}:{endpoint.port}")
    
    # Record outcome for learning
    vpn_rotation_manager.record_outcome(
        endpoint=endpoint,
        latency_ms=150.0,
        success=True,
        ip="185.x.x.x"
    )
"""

from .manager import VPNRotationManager
from .provider import ProviderRegistry, VPNProvider, ProviderConfig
from .wireproxy import WireProxyManager, WireProxyInstance
from .health import HealthMonitor, IPDetector
from .router import QLearningRouter, RoutingDecision
from .models import VPNEndpoint, RotationOutcome

# Default singleton instance
vpn_rotation_manager = VPNRotationManager()

__all__ = [
    "VPNRotationManager",
    "ProviderRegistry",
    "VPNProvider",
    "ProviderConfig",
    "WireProxyManager",
    "WireProxyInstance",
    "HealthMonitor",
    "IPDetector",
    "QLearningRouter",
    "RoutingDecision",
    "VPNEndpoint",
    "RotationOutcome",
    "vpn_rotation_manager",
]
