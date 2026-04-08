"""
VPN Rotator - Rotates through VPN IPs/proxies for request routing.

Features:
- Rotates through VPN IPs
- Tracks health per IP
- Uses existing vpn_manager.py if available

Reads from existing infrastructure if available.
"""

import logging
import random
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class VPNNode:
    """Represents a single VPN node/proxy."""
    
    def __init__(
        self,
        ip: str,
        port: int = 1080,
        protocol: str = "socks5",
        provider: str = "unknown",
        weight: float = 1.0,
        enabled: bool = True
    ):
        self.ip = ip
        self.port = port
        self.protocol = protocol
        self.provider = provider
        self.weight = weight
        self.enabled = enabled
        
        # Runtime state
        self.success_count = 0
        self.error_count = 0
        self.last_used = 0.0
        self.last_error = 0.0
        self.is_healthy = True
    
    @property
    def error_rate(self) -> float:
        total = self.success_count + self.error_count
        if total == 0:
            return 0.0
        return self.error_count / total
    
    @property
    def health_score(self) -> float:
        if not self.enabled:
            return 0.0
        return 1.0 - self.error_rate
    
    @property
    def proxy_url(self) -> str:
        return f"{self.protocol}://{self.ip}:{self.port}"


class VPNRotator:
    """
    Rotates through VPN IPs/proxies with health tracking.
    
    Uses existing packages/infrastructure/network/vpn_manager.py if available,
    otherwise uses configured proxy list.
    """
    
    def __init__(
        self,
        vpn_manager_path: str = "packages/infrastructure/network/vpn_manager.py",
        default_port: int = 1080
    ):
        self.default_port = default_port
        
        # VPN nodes: ip -> VPNNode
        self._nodes: Dict[str, VPNNode] = {}
        
        # Current index for round-robin
        self._round_robin_index: int = 0
        
        self._lock = threading.RLock()
        
        # Try to load from existing vpn_manager
        self._load_from_vpn_manager(vpn_manager_path)
    
    def _load_from_vpn_manager(self, vpn_manager_path: str):
        """Try to load VPN nodes from existing vpn_manager."""
        if not Path(vpn_manager_path).exists():
            logger.warning(f"VPN manager not found: {vpn_manager_path}")
            self._load_default_nodes()
            return
        
        try:
            # Try to import and get available proxies
            import sys
            sys.path.insert(0, str(Path.cwd()))
            
            # Import the module
            from packages.infrastructure.network.vpn_manager import VPNManager
            
            # Get available proxies
            manager = VPNManager()
            proxies = manager.get_all_proxies() if hasattr(manager, 'get_all_proxies') else []
            
            if proxies:
                for proxy in proxies:
                    node = VPNNode(
                        ip=proxy.get("ip", ""),
                        port=proxy.get("port", self.default_port),
                        protocol=proxy.get("protocol", "socks5"),
                        provider=proxy.get("provider", "unknown"),
                        weight=proxy.get("weight", 1.0),
                        enabled=proxy.get("enabled", True)
                    )
                    self._nodes[f"{node.ip}:{node.port}"] = node
                
                logger.info(f"Loaded {len(self._nodes)} VPN nodes from vpn_manager")
                return
                
        except Exception as e:
            logger.warning(f"Failed to load from vpn_manager: {e}")
        
        # Fall back to default nodes
        self._load_default_nodes()
    
    def _load_default_nodes(self):
        """Load default localhost SOCKS5 proxies."""
        # Default SOCKS5 proxies on localhost
        default_proxies = [
            {"ip": "127.0.0.1", "port": 1080, "provider": "local"},
            {"ip": "127.0.0.1", "port": 1081, "provider": "local"},
            {"ip": "127.0.0.1", "port": 1082, "provider": "local"},
            {"ip": "127.0.0.1", "port": 1083, "provider": "local"},
            {"ip": "127.0.0.1", "port": 1084, "provider": "local"},
            {"ip": "127.0.0.1", "port": 1085, "provider": "local"},
            {"ip": "127.0.0.1", "port": 1086, "provider": "local"},
            {"ip": "127.0.0.1", "port": 1087, "provider": "local"},
        ]
        
        for proxy in default_proxies:
            node = VPNNode(
                ip=proxy["ip"],
                port=proxy["port"],
                provider=proxy["provider"],
                enabled=True
            )
            self._nodes[f"{node.ip}:{node.port}"] = node
        
        logger.info(f"Loaded {len(self._nodes)} default VPN nodes")
    
    def get_vpn_ip(self, strategy: str = "health") -> Optional[VPNNode]:
        """
        Get a VPN node using the specified strategy.
        
        Strategies:
        - health: Use node with lowest error rate
        - round_robin: Cycle through nodes
        - weighted: Use node based on weight
        - random: Random selection
        
        Returns:
            VPNNode or None if no enabled nodes
        """
        with self._lock:
            enabled_nodes = [n for n in self._nodes.values() if n.enabled]
            
            if not enabled_nodes:
                return None
            
            if strategy == "health":
                return max(enabled_nodes, key=lambda n: n.health_score)
            elif strategy == "round_robin":
                node = enabled_nodes[self._round_robin_index % len(enabled_nodes)]
                self._round_robin_index = (self._round_robin_index + 1) % len(enabled_nodes)
                return node
            elif strategy == "weighted":
                total_weight = sum(n.weight for n in enabled_nodes)
                r = random.random() * total_weight
                cumulative = 0
                for node in enabled_nodes:
                    cumulative += node.weight
                    if r <= cumulative:
                        return node
                return enabled_nodes[-1]
            elif strategy == "random":
                return random.choice(enabled_nodes)
            else:
                return enabled_nodes[0]
    
    def rotate_on_429(self, ip: str, port: int):
        """
        Mark VPN node as having received 429 and rotate to next.
        
        Called when a VPN node receives a 429 response.
        """
        with self._lock:
            key = f"{ip}:{port}"
            node = self._nodes.get(key)
            
            if node:
                node.error_count += 1
                node.last_error = time.time()
                
                # Check if node should be disabled
                if node.error_rate > 0.5:  # More than 50% errors
                    node.is_healthy = False
                    logger.warning(f"Disabling VPN node {key} due to high error rate")
            
            # Move to next node in round-robin
            enabled_nodes = [n for n in self._nodes.values() if n.enabled]
            if enabled_nodes:
                self._round_robin_index = (self._round_robin_index + 1) % len(enabled_nodes)
    
    def record_success(self, ip: str, port: int):
        """Record successful request for a VPN node."""
        with self._lock:
            key = f"{ip}:{port}"
            node = self._nodes.get(key)
            
            if node:
                node.success_count += 1
                node.last_used = time.time()
    
    def record_error(self, ip: str, port: int):
        """Record error for a VPN node."""
        with self._lock:
            key = f"{ip}:{port}"
            node = self._nodes.get(key)
            
            if node:
                node.error_count += 1
                node.last_error = time.time()
    
    def get_nodes(self) -> List[VPNNode]:
        """Get all VPN nodes."""
        return list(self._nodes.values())
    
    def get_enabled_nodes(self) -> List[VPNNode]:
        """Get enabled VPN nodes."""
        return [n for n in self._nodes.values() if n.enabled]
    
    def get_stats(self) -> Dict:
        """Get statistics for all VPN nodes."""
        enabled_nodes = [n for n in self._nodes.values() if n.enabled]
        return {
            "total_nodes": len(self._nodes),
            "enabled_nodes": len(enabled_nodes),
            "nodes": [
                {
                    "ip": n.ip,
                    "port": n.port,
                    "provider": n.provider,
                    "enabled": n.enabled,
                    "success_count": n.success_count,
                    "error_count": n.error_count,
                    "error_rate": n.error_rate,
                    "health_score": n.health_score
                }
                for n in self._nodes.values()
            ]
        }
    
    def add_node(
        self,
        ip: str,
        port: int,
        protocol: str = "socks5",
        provider: str = "unknown",
        weight: float = 1.0
    ):
        """Add a new VPN node."""
        with self._lock:
            key = f"{ip}:{port}"
            node = VPNNode(
                ip=ip,
                port=port,
                protocol=protocol,
                provider=provider,
                weight=weight,
                enabled=True
            )
            self._nodes[key] = node
            logger.info(f"Added VPN node: {key}")
    
    def enable_node(self, ip: str, port: int):
        """Enable a VPN node."""
        with self._lock:
            key = f"{ip}:{port}"
            node = self._nodes.get(key)
            if node:
                node.enabled = True
                node.is_healthy = True
    
    def disable_node(self, ip: str, port: int):
        """Disable a VPN node."""
        with self._lock:
            key = f"{ip}:{port}"
            node = self._nodes.get(key)
            if node:
                node.enabled = False
                node.is_healthy = False
    
    def get_proxy_dict(self) -> Dict:
        """Get proxy configuration dict for requests library."""
        node = self.get_vpn_ip()
        if node is None:
            return {}
        
        return {
            "http": node.proxy_url,
            "https": node.proxy_url
        }