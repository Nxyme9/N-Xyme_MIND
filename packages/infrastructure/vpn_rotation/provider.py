"""Provider registry with plugin abstraction for VPN providers."""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type

from .models import ProviderConfig, ProviderType, VPNEndpoint


logger = logging.getLogger("vpn_rotation.provider")


class VPNProvider(ABC):
    """Abstract base class for VPN providers.
    
    Implement this to add support for new VPN services.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""
        pass
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        """Type of provider."""
        pass
    
    @abstractmethod
    async def list_endpoints(self) -> List[VPNEndpoint]:
        """List available endpoints from this provider.
        
        Returns:
            List of VPNEndpoint objects.
        """
        pass
    
    @abstractmethod
    async def check_health(self, endpoint: VPNEndpoint) -> bool:
        """Check if an endpoint is healthy.
        
        Args:
            endpoint: The endpoint to check.
            
        Returns:
            True if healthy, False otherwise.
        """
        pass
    
    async def connect(self, endpoint: VPNEndpoint) -> bool:
        """Connect to an endpoint (optional implementation).
        
        Default: always return True (endpoint is ready to use).
        """
        return True
    
    async def disconnect(self, endpoint: VPNEndpoint) -> None:
        """Disconnect from an endpoint (optional implementation)."""
        pass
    
    def configure(self, config: ProviderConfig) -> None:
        """Apply configuration to this provider."""
        pass


class ProtonVPNProvider(VPNProvider):
    """ProtonVPN provider implementation (WireGuard)."""
    
    def __init__(self):
        self._config: Optional[ProviderConfig] = None
        self._cached_endpoints: List[VPNEndpoint] = []
        self._cache_time: float = 0
        self._cache_ttl: float = 300.0  # 5 minutes
    
    @property
    def name(self) -> str:
        return "protonvpn"
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.PROTONVPN
    
    def configure(self, config: ProviderConfig) -> None:
        self._config = config
        self._cached_endpoints = []  # Invalidate cache on config change
    
    async def list_endpoints(self) -> List[VPNEndpoint]:
        """List available ProtonVPN endpoints.
        
        Uses WireGuard free servers.
        """
        import time
        
        # Return cached if fresh
        if self._cached_endpoints and (time.time() - self._cache_time) < self._cache_ttl:
            return self._cached_endpoints
        
        # Free server list (static for protonvpn free tier)
        servers = [
            {"host": "nl-free-101.protonvpn.net", "port": 51820, "country": "NL", "city": "Amsterdam"},
            {"host": "us-free-101.protonvpn.net", "port": 51820, "country": "US", "city": "New York"},
            {"host": "de-free-101.protonvpn.net", "port": 51820, "country": "DE", "city": "Berlin"},
            {"host": "ca-free-101.protonvpn.net", "port": 51820, "country": "CA", "city": "Toronto"},
            {"host": "jp-free-101.protonvpn.net", "port": 51820, "country": "JP", "city": "Tokyo"},
            {"host": "ro-free-101.protonvpn.net", "port": 51820, "country": "RO", "city": "Bucharest"},
            {"host": "no-free-101.protonvpn.net", "port": 51820, "country": "NO", "city": "Oslo"},
            {"host": "se-free-101.protonvpn.net", "port": 51820, "country": "SE", "city": "Stockholm"},
        ]
        
        endpoints = []
        for srv in servers:
            ep = VPNEndpoint(
                host=srv["host"],
                port=srv["port"],
                provider=self.name,
                provider_type=self.provider_type,
                country=srv["country"],
                city=srv["city"],
            )
            endpoints.append(ep)
        
        self._cached_endpoints = endpoints
        self._cache_time = time.time()
        return endpoints
    
    async def check_health(self, endpoint: VPNEndpoint) -> bool:
        """Check WireGuard endpoint health via UDP handshake."""
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(3.0)
            # Try to send handshake initiation
            # Real implementation would do WireGuard handshake
            # For now, just check if host is reachable
            sock.sendto(b"\x04\x00\x00\x00\x00\x00\x00\x00", (endpoint.host, endpoint.port))
            data, _ = sock.recvfrom(128)
            sock.close()
            return len(data) > 0
        except Exception:
            return False


class SOCKS5Provider(VPNProvider):
    """Generic SOCKS5 proxy provider."""
    
    def __init__(self):
        self._config: Optional[ProviderConfig] = None
        self._endpoints: List[VPNEndpoint] = []
    
    @property
    def name(self) -> str:
        return "socks5"
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.SOCKS5
    
    def configure(self, config: ProviderConfig) -> None:
        self._config = config
        if config.host and config.port:
            self._endpoints = [
                VPNEndpoint(
                    host=config.host,
                    port=config.port,
                    provider=self.name,
                    provider_type=self.provider_type,
                )
            ]
    
    async def list_endpoints(self) -> List[VPNEndpoint]:
        return self._endpoints
    
    async def check_health(self, endpoint: VPNEndpoint) -> bool:
        """Check SOCKS5 proxy health via TCP handshake."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(endpoint.host, endpoint.port),
                timeout=5.0
            )
            # SOCKS5 greeting
            writer.write(b"\x05\x01\x00")
            await writer.drain()
            resp = await asyncio.wait_for(reader.readexactly(2), timeout=5.0)
            writer.close()
            await writer.wait_closed()
            return resp == b"\x05\x00"
        except Exception:
            return False


class WireProxyProvider(VPNProvider):
    """WireProxy (WireGuard-to-SOCKS5) provider."""
    
    def __init__(self):
        self._config: Optional[ProviderConfig] = None
        self._base_port: int = 1080
    
    @property
    def name(self) -> str:
        return "wireproxy"
    
    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.WIREPROXY
    
    def configure(self, config: ProviderConfig) -> None:
        self._config = config
        self._base_port = config.port or 1080
    
    async def list_endpoints(self) -> List[VPNEndpoint]:
        """List WireProxy instances (ports 1080-1087)."""
        # Dynamic: instances spawned by WireProxyManager
        # This just returns the port range as endpoints
        max_instances = self._config.max_instances if self._config else 8
        endpoints = []
        for i in range(max_instances):
            ep = VPNEndpoint(
                host="127.0.0.1",
                port=self._base_port + i,
                provider=self.name,
                provider_type=self.provider_type,
                instance_id=f"wireproxy-{i}",
            )
            endpoints.append(ep)
        return endpoints
    
    async def check_health(self, endpoint: VPNEndpoint) -> bool:
        """Check WireProxy SOCKS5 health."""
        return await SOCKS5Provider().check_health(endpoint)


class ProviderRegistry:
    """Registry for VPN providers with plugin support.
    
    Manages provider lifecycle and endpoint discovery.
    """
    
    _providers: Dict[str, VPNProvider] = {}
    _provider_classes: Dict[str, Type[VPNProvider]] = {
        "protonvpn": ProtonVPNProvider,
        "socks5": SOCKS5Provider,
        "wireproxy": WireProxyProvider,
    }
    
    @classmethod
    def register_provider(cls, name: str, provider_class: Type[VPNProvider]) -> None:
        """Register a new provider type.
        
        Args:
            name: Provider identifier.
            provider_class: Class implementing VPNProvider.
        """
        cls._provider_classes[name] = provider_class
        logger.info(f"Registered provider: {name}")
    
    @classmethod
    def add_provider(cls, name: str, config: ProviderConfig) -> VPNProvider:
        """Add and configure a provider.
        
        Args:
            name: Provider identifier.
            config: Provider configuration.
            
        Returns:
            Configured provider instance.
        """
        if name in cls._providers:
            cls._providers[name].configure(config)
            return cls._providers[name]
        
        if name not in cls._provider_classes:
            raise ValueError(f"Unknown provider: {name}")
        
        provider = cls._provider_classes[name]()
        provider.configure(config)
        cls._providers[name] = provider
        logger.info(f"Added provider: {name}")
        return provider
    
    @classmethod
    def get_provider(cls, name: str) -> Optional[VPNProvider]:
        """Get a provider by name."""
        return cls._providers.get(name)
    
    @classmethod
    def list_providers(cls) -> List[str]:
        """List all registered provider names."""
        return list(cls._providers.keys())
    
    @classmethod
    async def list_all_endpoints(cls) -> List[VPNEndpoint]:
        """List all endpoints from all providers."""
        endpoints = []
        for provider in cls._providers.values():
            try:
                eps = await provider.list_endpoints()
                endpoints.extend(eps)
            except Exception as e:
                logger.warning(f"Failed to list endpoints from {provider.name}: {e}")
        return endpoints
    
    @classmethod
    async def check_all_health(cls) -> Dict[str, bool]:
        """Check health of all endpoints from all providers."""
        results = {}
        endpoints = await cls.list_all_endpoints()
        for ep in endpoints:
            key = f"{ep.host}:{ep.port}"
            # Placeholder - actual health check done by HealthMonitor
            results[key] = ep.healthy
        return results
    
    @classmethod
    def clear(cls) -> None:
        """Clear all registered providers."""
        cls._providers.clear()
