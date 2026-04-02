#!/usr/bin/env python3
"""
Multi-Instance OpenCode Manager
Manages multiple OpenCode instances with individual VPN/API rotations
"""
import asyncio
import json
import os
import signal
import socket
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
import hashlib

# Instance states
class InstanceState(Enum):
    CREATING = "creating"
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    ROTATING = "rotating"
    ERROR = "error"
    STOPPED = "stopped"

@dataclass
class OpenCodeInstance:
    """Represents a single OpenCode instance"""
    instance_id: str
    name: str
    port: int
    working_dir: str
    
    # State
    state: InstanceState = InstanceState.CREATING
    pid: int = None
    
    # VPN/Tunnel binding
    vpn_country: str = None
    socks_port: int = None
    tunnel_name: str = None
    
    # API configuration
    model_preference: List[str] = field(default_factory=list)
    api_keys: Dict[str, str] = field(default_factory=dict)
    
    # Statistics
    requests_handled: int = 0
    tokens_generated: int = 0
    errors: int = 0
    uptime_seconds: float = 0
    started_at: datetime = None
    
    # Current task
    current_task: str = None
    current_session: str = None

class InstanceManager:
    """
    Manages multiple OpenCode instances with individual rotations
    """
    
    def __init__(self, base_port: int = 8080, data_dir: str = None):
        self.base_port = base_port
        self.data_dir = data_dir or "/home/nxyme/projects/modelrouter/data/instances"
        self.instances: Dict[str, OpenCodeInstance] = {}
        
        # Callbacks
        self.on_instance_state_change: Optional[Callable] = None
        self.on_task_complete: Optional[Callable] = None
        
        # Thread safety
        self._lock = threading.Lock()
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load configuration
        self._load_config()
        
    def _load_config(self):
        """Load instance configuration"""
        config_path = os.path.join(self.data_dir, "instances.json")
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                data = json.load(f)
                # Restore instances would go here
                
    def _save_config(self):
        """Save instance configuration"""
        config_path = os.path.join(self.data_dir, "instances.json")
        data = {
            "instances": {
                inst_id: {
                    "instance_id": inst.instance_id,
                    "name": inst.name,
                    "port": inst.port,
                    "working_dir": inst.working_dir,
                    "vpn_country": inst.vpn_country,
                    "socks_port": inst.socks_port,
                    "model_preference": inst.model_preference,
                }
                for inst_id, inst in self.instances.items()
            }
        }
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)
    
    def create_instance(
        self,
        name: str = None,
        vpn_country: str = None,
        socks_port: int = None,
        model_preference: List[str] = None,
        working_dir: str = None
    ) -> OpenCodeInstance:
        """Create a new OpenCode instance"""
        with self._lock:
            instance_id = str(uuid.uuid4())[:8]
            name = name or f"instance-{instance_id}"
            
            # Find available port
            port = self._find_available_port()
            
            # Default working directory
            working_dir = working_dir or os.path.join(self.data_dir, instance_id)
            os.makedirs(working_dir, exist_ok=True)
            
            instance = OpenCodeInstance(
                instance_id=instance_id,
                name=name,
                port=port,
                working_dir=working_dir,
                vpn_country=vpn_country,
                socks_port=socks_port,
                model_preference=model_preference or ["mimo-v2-pro-free", "gpt-5-nano"],
                state=InstanceState.CREATING,
                started_at=datetime.now()
            )
            
            self.instances[instance_id] = instance
            self._save_config()
            
            print(f"✅ Created instance: {name} (ID: {instance_id}, Port: {port})")
            return instance
    
    def _find_available_port(self) -> int:
        """Find an available port for new instance"""
        used_ports = {inst.port for inst in self.instances.values()}
        
        for port in range(self.base_port, self.base_port + 100):
            if port not in used_ports:
                try:
                    # Check if port is actually available
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(1)
                    result = sock.connect_ex(('127.0.0.1', port))
                    sock.close()
                    if result != 0:  # Port is free
                        return port
                except:
                    return port
                    
        return self.base_port + len(used_ports)
    
    def start_instance(self, instance_id: str) -> bool:
        """Start an OpenCode instance"""
        with self._lock:
            instance = self.instances.get(instance_id)
            if not instance:
                return False
                
            instance.state = InstanceState.STARTING
            
        try:
            # Build environment with VPN proxy if configured
            env = os.environ.copy()
            if instance.socks_port:
                env['http_proxy'] = f"socks5://127.0.0.1:{instance.socks_port}"
                env['https_proxy'] = f"socks5://127.0.0.1:{instance.socks_port}"
                
            # Create startup script
            startup_script = os.path.join(instance.working_dir, "start.sh")
            with open(startup_script, 'w') as f:
                f.write(f"""#!/bin/bash
cd {instance.working_dir}
# Instance-specific config would go here
opencode --port {instance.port}
""")
            os.chmod(startup_script, 0o755)
            
            # Start the process (simplified - actual opencode startup would differ)
            # For now, we simulate the instance
            proc = subprocess.Popen(
                ["sleep", "infinity"],  # Placeholder
                cwd=instance.working_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            instance.pid = proc.pid
            instance.state = InstanceState.RUNNING
            
            print(f"🚀 Started instance: {instance.name} (PID: {instance.pid})")
            return True
            
        except Exception as e:
            print(f"❌ Failed to start instance {instance_id}: {e}")
            instance.state = InstanceState.ERROR
            instance.errors += 1
            return False
    
    def stop_instance(self, instance_id: str) -> bool:
        """Stop an OpenCode instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            return False
            
        try:
            if instance.pid:
                os.kill(instance.pid, signal.SIGTERM)
                time.sleep(1)
                # Force kill if still running
                try:
                    os.kill(instance.pid, signal.SIGKILL)
                except:
                    pass
                    
            instance.state = InstanceState.STOPPED
            instance.pid = None
            print(f"🛑 Stopped instance: {instance.name}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to stop instance {instance_id}: {e}")
            return False
    
    def rotate_instance_vpn(self, instance_id: str, new_country: str = None) -> bool:
        """Rotate VPN for a specific instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            return False
            
        instance.state = InstanceState.ROTATING
        
        # In real implementation, this would:
        # 1. Connect to new VPN country
        # 2. Get new SOCKS port
        # 3. Update instance config
        # 4. Restart with new proxy
        
        if new_country:
            instance.vpn_country = new_country
            
        instance.state = InstanceState.RUNNING
        print(f"🔄 Rotated VPN for {instance.name} → {new_country or instance.vpn_country}")
        return True
    
    def get_instance_status(self, instance_id: str) -> Dict:
        """Get status of an instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            return {"error": "Instance not found"}
            
        # Update uptime
        if instance.started_at and instance.state == InstanceState.RUNNING:
            instance.uptime_seconds = (datetime.now() - instance.started_at).total_seconds()
            
        return {
            "instance_id": instance.instance_id,
            "name": instance.name,
            "port": instance.port,
            "state": instance.state.value,
            "vpn_country": instance.vpn_country,
            "socks_port": instance.socks_port,
            "pid": instance.pid,
            "requests_handled": instance.requests_handled,
            "tokens_generated": instance.tokens_generated,
            "errors": instance.errors,
            "uptime_seconds": instance.uptime_seconds,
            "current_task": instance.current_task,
            "current_session": instance.current_session
        }
    
    def get_all_status(self) -> Dict:
        """Get status of all instances"""
        return {
            "total_instances": len(self.instances),
            "running": len([i for i in self.instances.values() if i.state == InstanceState.RUNNING]),
            "busy": len([i for i in self.instances.values() if i.state == InstanceState.BUSY]),
            "error": len([i for i in self.instances.values() if i.state == InstanceState.ERROR]),
            "instances": {
                inst_id: self.get_instance_status(inst_id)
                for inst_id in self.instances
            }
        }
    
    def get_best_instance(self, task_type: str = None) -> Optional[OpenCodeInstance]:
        """Get the best available instance for a task"""
        available = [
            inst for inst in self.instances.values()
            if inst.state in [InstanceState.RUNNING, InstanceState.IDLE]
        ]
        
        if not available:
            return None
            
        # Sort by: fewer errors, more uptime, fewer requests
        available.sort(key=lambda x: (x.errors, -x.uptime_seconds, x.requests_handled))
        return available[0]
    
    def delegate_task(self, instance_id: str, task: str, session_id: str = None) -> bool:
        """Delegate a task to an instance"""
        instance = self.instances.get(instance_id)
        if not instance:
            return False
            
        if instance.state not in [InstanceState.RUNNING, InstanceState.IDLE]:
            return False
            
        instance.state = InstanceState.BUSY
        instance.current_task = task
        instance.current_session = session_id or str(uuid.uuid4())[:8]
        instance.requests_handled += 1
        
        print(f"📤 Delegated task to {instance.name}: {task[:50]}...")
        return True
    
    def complete_task(self, instance_id: str, tokens_generated: int = 0):
        """Mark a task as complete"""
        instance = self.instances.get(instance_id)
        if not instance:
            return
            
        instance.tokens_generated += tokens_generated
        instance.state = InstanceState.IDLE
        instance.current_task = None
        
        if self.on_task_complete:
            self.on_task_complete(instance_id, tokens_generated)


# Load balancer for instances
class InstanceLoadBalancer:
    """
    Distributes requests across instances intelligently
    """
    
    def __init__(self, manager: InstanceManager):
        self.manager = manager
        self.round_robin_index = 0
        
    def select_instance(self, requirements: Dict = None) -> Optional[OpenCodeInstance]:
        """Select best instance based on requirements"""
        instances = [
            inst for inst in self.manager.instances.values()
            if inst.state in [InstanceState.RUNNING, InstanceState.IDLE]
        ]
        
        if not instances:
            return None
            
        # If specific VPN country required
        if requirements and requirements.get("vpn_country"):
            vpn_filtered = [
                inst for inst in instances
                if inst.vpn_country == requirements["vpn_country"]
            ]
            if vpn_filtered:
                instances = vpn_filtered
                
        # Round-robin as fallback
        inst = instances[self.round_robin_index % len(instances)]
        self.round_robin_index += 1
        
        return inst


# Singleton instance
_instance_manager = None

def get_instance_manager() -> InstanceManager:
    global _instance_manager
    if _instance_manager is None:
        _instance_manager = InstanceManager()
    return _instance_manager


if __name__ == "__main__":
    print("🧪 Testing Instance Manager...")
    
    manager = get_instance_manager()
    
    # Create instances with different VPN bindings
    inst1 = manager.create_instance(
        name="primary",
        vpn_country="NL",
        socks_port=1080,
        model_preference=["mimo-v2-pro-free"]
    )
    
    inst2 = manager.create_instance(
        name="secondary", 
        vpn_country="JP",
        socks_port=1081,
        model_preference=["gpt-5-nano", "kimi-k2.5-free"]
    )
    
    inst3 = manager.create_instance(
        name="fallback",
        vpn_country="US",
        socks_port=1082,
        model_preference=["claude-sonnet-4"]
    )
    
    print(f"\n📊 Status: {json.dumps(manager.get_all_status(), indent=2, default=str)}")
