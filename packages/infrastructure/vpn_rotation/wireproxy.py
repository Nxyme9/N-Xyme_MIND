"""WireProxy instance manager - dynamic spawning without hard limits."""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from .models import InstanceStatus, VPNEndpoint

logger = logging.getLogger("vpn_rotation.wireproxy")


# Default paths (configurable via environment)
WIREPROXY_BIN = os.environ.get("WIREPROXY_BIN", f"{os.path.expanduser('~')}/go/bin/wireproxy")
CONFIG_DIR = Path(os.environ.get("WIREPROXY_CONFIG_DIR", f"{os.path.expanduser('~')}/.config/wireproxy"))
SERVICE_DIR = Path(os.environ.get("WIREPROXY_SERVICE_DIR", f"{os.path.expanduser('~')}/.config/systemd/user"))


@dataclass
class WireProxyInstance:
    """Represents a single WireProxy instance."""
    instance_id: str
    port: int
    country: str
    status: InstanceStatus = InstanceStatus.STOPPED
    pid: Optional[int] = None
    config_file: Optional[Path] = None
    
    # Metrics
    created_at: float = 0
    last_startAttempt: float = 0
    restart_count: int = 0
    
    @property
    def is_running(self) -> bool:
        return self.status == InstanceStatus.RUNNING
    
    @property
    def endpoint(self) -> VPNEndpoint:
        return VPNEndpoint(
            host="127.0.0.1",
            port=self.port,
            provider="wireproxy",
            provider_type="wireproxy",
            country=self.country,
            instance_id=self.instance_id,
        )


class WireProxyManager:
    """Manages WireProxy instances with dynamic spawning.
    
    Key features:
    - No hard limit on instances (spawn on demand)
    - Automatic restart on failure
    - Port allocation management
    - systemd integration optional
    """
    
    def __init__(
        self,
        base_port: int = 1080,
        max_instances: int = 32,
        config_dir: Path = CONFIG_DIR,
        binary_path: str = WIREPROXY_BIN,
    ):
        self.base_port = base_port
        self.max_instances = max_instances
        self.config_dir = config_dir
        self.binary_path = binary_path
        
        self._instances: dict[str, WireProxyInstance] = {}
        self._used_ports: set[int] = set()
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    @property
    def instances(self) -> List[WireProxyInstance]:
        """List all instances."""
        return list(self._instances.values())
    
    @property
    def running_count(self) -> int:
        """Count of running instances."""
        return sum(1 for i in self._instances.values() if i.is_running)
    
    def _allocate_port(self) -> Optional[int]:
        """Allocate an available port."""
        for port in range(self.base_port, self.base_port + self.max_instances):
            if port not in self._used_ports:
                self._used_ports.add(port)
                return port
        return None
    
    def _release_port(self, port: int) -> None:
        """Release a port back to the pool."""
        self._used_ports.discard(port)
    
    def _get_country_for_port(self, port: int) -> str:
        """Map port to country code (for display)."""
        idx = (port - self.base_port) % 8
        countries = ["nl", "us", "de", "ca", "jp", "ro", "no", "se"]
        return countries[idx] if idx < len(countries) else "unknown"
    
    async def spawn_instance(
        self,
        instance_id: Optional[str] = None,
        config: Optional[dict] = None,
    ) -> Optional[WireProxyInstance]:
        """Spawn a new WireProxy instance.
        
        Args:
            instance_id: Optional custom ID (generated if not provided).
            config: Optional WireProxy config dict.
            
        Returns:
            New instance, or None if max reached.
        """
        port = self._allocate_port()
        if port is None:
            logger.warning(f"Max instances ({self.max_instances}) reached")
            return None
        
        if instance_id is None:
            instance_id = f"wireproxy-{port}"
        
        # Check if already exists
        if instance_id in self._instances:
            existing = self._instances[instance_id]
            if existing.is_running:
                return existing
            # Restart stopped instance
            return await self.start_instance(instance_id)
        
        country = self._get_country_for_port(port)
        instance = WireProxyInstance(
            instance_id=instance_id,
            port=port,
            country=country,
            status=InstanceStatus.STARTING,
            created_at=time.time(),
        )
        
        # Generate config file
        config_file = self.config_dir / f"proxy-{port}.conf"
        instance.config_file = config_file
        
        if config is None:
            # Default minimal config (user needs to add credentials)
            config = {
                "SocksPort": str(port),
                "SocksAddress": "127.0.0.1",
                "Socks5": True,
            }
        
        # Write config
        config_content = self._generate_config(config)
        config_file.write_text(config_content)
        
        self._instances[instance_id] = instance
        return await self.start_instance(instance_id)
    
    def _generate_config(self, config: dict) -> str:
        """Generate WireProxy config file content."""
        lines = ["[Interface]"]
        if "PrivateKey" in config:
            lines.append(f"PrivateKey = {config['PrivateKey']}")
        if "Address" in config:
            lines.append(f"Address = {config['Address']}")
        
        lines.append("\n[Peer]")
        if "PublicKey" in config:
            lines.append(f"PublicKey = {config['PublicKey']}")
        if "Endpoint" in config:
            lines.append(f"Endpoint = {config['Endpoint']}")
        if "AllowedIPs" in config:
            lines.append(f"AllowedIPs = {config['AllowedIPs']}")
        else:
            lines.append("AllowedIPs = 0.0.0.0/0")
        
        lines.append("\n[Socks5]")
        lines.append(f"Bind = 127.0.0.1:{config.get('SocksPort', 1080)}")
        
        return "\n".join(lines)
    
    async def start_instance(self, instance_id: str) -> Optional[WireProxyInstance]:
        """Start a specific instance."""
        instance = self._instances.get(instance_id)
        if not instance:
            return None
        
        if instance.is_running:
            return instance
        
        instance.status = InstanceStatus.STARTING
        instance.last_startAttempt = time.time()
        
        # Check binary exists
        if not Path(self.binary_path).exists():
            logger.error(f"WireProxy binary not found: {self.binary_path}")
            instance.status = InstanceStatus.UNHEALTHY
            return None
        
        try:
            # Start WireProxy process
            proc = subprocess.Popen(
                [self.binary_path, "-c", str(instance.config_file)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            instance.pid = proc.pid
            
            # Wait for startup
            await asyncio.sleep(2)
            
            # Check if still running
            if proc.poll() is not None:
                instance.status = InstanceStatus.UNHEALTHY
                logger.error(f"WireProxy instance {instance_id} died on startup")
                return None
            
            instance.status = InstanceStatus.RUNNING
            logger.info(f"Started WireProxy instance {instance_id} on port {instance.port}")
            return instance
            
        except Exception as e:
            logger.error(f"Failed to start instance {instance_id}: {e}")
            instance.status = InstanceStatus.UNHEALTHY
            return None
    
    async def stop_instance(self, instance_id: str) -> bool:
        """Stop a specific instance."""
        instance = self._instances.get(instance_id)
        if not instance:
            return False
        
        if instance.pid:
            try:
                os.kill(instance.pid, 15)  # SIGTERM
                await asyncio.sleep(1)
                # Force kill if still running
                try:
                    os.kill(instance.pid, 9)
                except ProcessLookupError:
                    pass
            except ProcessLookupError:
                pass
        
        instance.status = InstanceStatus.STOPPED
        instance.pid = None
        self._release_port(instance.port)
        
        logger.info(f"Stopped WireProxy instance {instance_id}")
        return True
    
    async def restart_instance(self, instance_id: str) -> Optional[WireProxyInstance]:
        """Restart an instance."""
        await self.stop_instance(instance_id)
        return await self.start_instance(instance_id)
    
    async def remove_instance(self, instance_id: str) -> bool:
        """Remove (stop + delete) an instance."""
        await self.stop_instance(instance_id)
        instance = self._instances.pop(instance_id, None)
        if instance and instance.config_file:
            try:
                instance.config_file.unlink()
            except FileNotFoundError:
                pass
        return True
    
    async def scale_to(self, count: int) -> List[WireProxyInstance]:
        """Scale to specified number of running instances.
        
        Creates or removes instances as needed.
        """
        current = self.running_count
        
        if current < count:
            # Spawn more
            needed = count - current
            logger.info(f"Scaling up: {needed} new instances")
            for _ in range(needed):
                await self.spawn_instance()
        
        elif current > count:
            # Remove excess (oldest first)
            excess = current - count
            logger.info(f"Scaling down: {excess} instances")
            running = [i for i in self.instances if i.is_running]
            running.sort(key=lambda x: x.created_at)
            for inst in running[:excess]:
                await self.remove_instance(inst.instance_id)
        
        return [i for i in self.instances if i.is_running]
    
    async def get_endpoints(self) -> List[VPNEndpoint]:
        """Get endpoints from all running instances."""
        return [i.endpoint for i in self.instances if i.is_running]
    
    async def health_check(self) -> dict:
        """Check health of all instances."""
        results = {}
        for inst in self.instances:
            if inst.is_running and inst.pid:
                try:
                    os.kill(inst.pid, 0)  # Check if process exists
                    results[inst.instance_id] = "healthy"
                except ProcessLookupError:
                    inst.status = InstanceStatus.UNHEALTHY
                    results[inst.instance_id] = "dead"
            else:
                results[inst.instance_id] = inst.status.value
        return results
    
    async def start_monitoring(self, interval: float = 30.0) -> None:
        """Start background monitoring task."""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
    
    async def stop_monitoring(self) -> None:
        """Stop background monitoring."""
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
    
    async def _monitor_loop(self, interval: float) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                health = await self.health_check()
                for inst_id, status in health.items():
                    if status == "dead":
                        logger.warning(f"Instance {inst_id} died, restarting...")
                        inst = self._instances.get(inst_id)
                        if inst:
                            inst.restart_count += 1
                            await self.restart_instance(inst_id)
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
            
            await asyncio.sleep(interval)
    
    async def stop_all(self) -> None:
        """Stop all instances."""
        await self.stop_monitoring()
        for inst in list(self._instances.keys()):
            await self.stop_instance(inst)
    
    def get_stats(self) -> dict:
        """Get manager statistics."""
        return {
            "total_instances": len(self._instances),
            "running": self.running_count,
            "stopped": sum(1 for i in self._instances.values() if i.status == InstanceStatus.STOPPED),
            "unhealthy": sum(1 for i in self._instances.values() if i.status == InstanceStatus.UNHEALTHY),
            "max_instances": self.max_instances,
            "ports_in_use": len(self._used_ports),
        }


# Default singleton (lazy initialization)
_wireproxy_manager: Optional[WireProxyManager] = None


def get_wireproxy_manager() -> WireProxyManager:
    """Get or create the default WireProxyManager instance."""
    global _wireproxy_manager
    if _wireproxy_manager is None:
        _wireproxy_manager = WireProxyManager()
    return _wireproxy_manager
