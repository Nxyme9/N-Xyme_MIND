#!/usr/bin/env python3
"""
Master Orchestration Controller
Federated system: Multi-tunnel VPN + Multi-instance OpenCode + Token Aggregation
"""
import asyncio
import json
import os
import socket
import subprocess
import threading
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import signal
import sys

# Import our modules
from multi_tunnel import MultiTunnelManager, get_tunnel_manager
from token_aggregator import TokenAggregator, FederatedContextBuilder, get_aggregator
from instance_manager import InstanceManager, InstanceLoadBalancer, get_instance_manager

class OrchestrationMode(Enum):
    SINGLE = "single"           # Single instance, single tunnel
    FEDERATED = "federated"    # Multiple instances, multiple tunnels
    PARALLEL = "parallel"      # Multiple instances, token aggregation

@dataclass
class OrchestrationSession:
    """Main orchestration session"""
    session_id: str
    mode: OrchestrationMode
    created_at: datetime = field(default_factory=datetime.now)
    
    # Components
    tunnel_manager: MultiTunnelManager = None
    instance_manager: InstanceManager = None
    aggregator: TokenAggregator = None
    context_builder: FederatedContextBuilder = None
    
    # Status
    status: str = "initializing"  # initializing, running, paused, complete
    total_tokens: int = 0
    active_instances: int = 0
    
class MasterController:
    """
    Master Orchestration Controller
    Coordinates all components for maximum throughput
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or self._default_config()
        self.session: OrchestrationSession = None
        
        # Components
        self.tunnel_manager: Optional[MultiTunnelManager] = None
        self.instance_manager: Optional[InstanceManager] = None
        self.aggregator: Optional[TokenAggregator] = None
        self.context_builder: Optional[FederatedContextBuilder] = None
        self.load_balancer: Optional[InstanceLoadBalancer] = None
        
        # State
        self._running = False
        self._health_check_thread = None
        
        # Statistics
        self.stats = {
            "sessions_completed": 0,
            "total_tokens_generated": 0,
            "total_requests": 0,
            "vpn_rotations": 0,
            "instance_rotations": 0,
            "errors": 0
        }
        
    def _default_config(self) -> Dict:
        """Default configuration"""
        return {
            "num_tunnels": 5,
            "num_instances": 3,
            "tunnel_countries": ["NL", "NL2", "JP", "CA", "NO"],
            "base_socks_port": 1080,
            "base_instance_port": 8080,
            "health_check_interval": 60,
            "auto_rotate_on_error": True,
            "max_retries": 3,
            "token_buffer_size": 128000
        }
    
    def initialize(self, mode: OrchestrationMode = OrchestrationMode.FEDERATED) -> bool:
        """Initialize the orchestration system"""
        print(f"🚀 Initializing Master Controller in {mode.value} mode...")
        
        session_id = str(uuid.uuid4())[:8]
        self.session = OrchestrationSession(
            session_id=session_id,
            mode=mode
        )
        
        try:
            # Initialize tunnel manager
            print("📡 Setting up multi-tunnel VPN...")
            self.tunnel_manager = get_tunnel_manager(self.config["num_tunnels"])
            self.tunnel_manager.initialize_tunnels(self.config["tunnel_countries"])
            
            # Connect tunnels
            for tunnel_name in self.tunnel_manager.tunnels:
                self.tunnel_manager.connect_tunnel(tunnel_name)
                time.sleep(2)  # Stagger connections
                
            # Initialize instance manager
            print("💻 Setting up OpenCode instances...")
            self.instance_manager = get_instance_manager()
            self.instance_manager.base_port = self.config["base_instance_port"]
            
            # Create instances with tunnel bindings
            countries = self.config["tunnel_countries"]
            ports = range(self.config["base_socks_port"], 
                         self.config["base_socks_port"] + self.config["num_instances"])
            
            for i in range(self.config["num_instances"]):
                country = countries[i % len(countries)]
                socks_port = ports[i]
                
                inst = self.instance_manager.create_instance(
                    name=f"orch-{i+1}",
                    vpn_country=country,
                    socks_port=socks_port,
                    model_preference=self._get_model_preference(i)
                )
                
                # Start instance
                self.instance_manager.start_instance(inst.instance_id)
                time.sleep(1)
            
            # Initialize token aggregator
            print("🔗 Setting up token aggregator...")
            self.aggregator = get_aggregator(session_id)
            self.context_builder = FederatedContextBuilder()
            
            # Register all instances as sources
            for inst_id, inst in self.instance_manager.instances.items():
                self.aggregator.add_source(
                    inst_id,
                    f"http://localhost:{inst.port}"
                )
                self.context_builder.register_source(
                    inst_id,
                    priority=1.0 - (i * 0.1),  # First instance = highest priority
                    metadata={"vpn": inst.vpn_country, "port": inst.port}
                )
            
            # Initialize load balancer
            self.load_balancer = InstanceLoadBalancer(self.instance_manager)
            
            # Start background services
            self._start_health_checks()
            
            self.session.status = "running"
            print(f"✅ Master Controller initialized! Session: {session_id}")
            return True
            
        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            self.stats["errors"] += 1
            return False
    
    def _get_model_preference(self, instance_index: int) -> List[str]:
        """Get model preference for instance"""
        preferences = [
            ["mimo-v2-pro-free", "gpt-5-nano", "kimi-k2.5-free"],
            ["gpt-5-nano", "mimo-v2-pro-free", "claude-sonnet-4"],
            ["kimi-k2.5-free", "gpt-5-nano", "mimo-v2-omni-free"]
        ]
        return preferences[instance_index % len(preferences)]
    
    def _start_health_checks(self):
        """Start background health monitoring"""
        self._running = True
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True
        )
        self._health_check_thread.start()
        print("❤️ Health checks started")
    
    def _health_check_loop(self):
        """Background health check loop"""
        while self._running:
            try:
                self._perform_health_check()
            except Exception as e:
                print(f"⚠️ Health check error: {e}")
            time.sleep(self.config["health_check_interval"])
    
    def _perform_health_check(self):
        """Perform health check on all components"""
        # Check tunnels
        if self.tunnel_manager:
            status = self.tunnel_manager.get_status()
            if status["connected"] < status["total_tunnels"]:
                print(f"⚠️ Some tunnels disconnected: {status['connected']}/{status['total_tunnels']}")
                
        # Check instances
        if self.instance_manager:
            inst_status = self.instance_manager.get_all_status()
            if inst_status["error"] > 0:
                print(f"⚠️ {inst_status['error']} instances in error state")
    
    def execute_task(self, task: str, requirements: Dict = None) -> Dict:
        """Execute a task using the best available instance"""
        if not self.session or self.session.status != "running":
            return {"error": "Orchestrator not initialized"}
            
        requirements = requirements or {}
        
        # Select best instance
        instance = self.load_balancer.select_instance(requirements)
        
        if not instance:
            return {"error": "No available instances"}
        
        # Delegate to instance
        session_id = str(uuid.uuid4())[:8]
        self.instance_manager.delegate_task(instance.instance_id, task, session_id)
        
        # Record in context builder
        self.context_builder.add_content(
            instance.instance_id,
            f"Task: {task}",
            metadata={"session": session_id, "timestamp": datetime.now().isoformat()}
        )
        
        self.stats["total_requests"] += 1
        
        return {
            "status": "delegated",
            "instance": instance.name,
            "instance_id": instance.instance_id,
            "session_id": session_id,
            "vpn_country": instance.vpn_country,
            "socks_port": instance.socks_port
        }
    
    def aggregate_output(self, source_id: str, content: str, tokens: int):
        """Aggregate output from an instance"""
        from token_aggregator import TokenChunk
        
        chunk = TokenChunk(
            chunk_id=str(uuid.uuid4()),
            source_id=source_id,
            content=content,
            token_count=tokens
        )
        
        self.aggregator.receive_chunk(chunk)
        self.context_builder.add_content(source_id, content)
        
        self.stats["total_tokens_generated"] += tokens
    
    def rotate_all(self) -> Dict:
        """Rotate all tunnels and instances"""
        results = {
            "tunnels": {},
            "instances": {}
        }
        
        # Rotate tunnels
        if self.tunnel_manager:
            results["tunnels"] = self.tunnel_manager.rotate_all()
            self.stats["vpn_rotations"] += 1
        
        # Rotate instances
        if self.instance_manager:
            for inst_id in self.instance_manager.instances:
                new_country = self._get_next_country()
                results["instances"][inst_id] = self.instance_manager.rotate_instance_vpn(
                    inst_id, new_country
                )
            self.stats["instance_rotations"] += 1
        
        return results
    
    def _get_next_country(self) -> str:
        """Get next country for rotation"""
        countries = self.config["tunnel_countries"]
        return countries[self.stats["vpn_rotations"] % len(countries)]
    
    def get_status(self) -> Dict:
        """Get full system status"""
        status = {
            "session_id": self.session.session_id if self.session else None,
            "mode": self.session.mode.value if self.session else None,
            "status": self.session.status if self.session else "not_initialized",
            "statistics": self.stats
        }
        
        if self.tunnel_manager:
            status["tunnels"] = self.tunnel_manager.get_status()
            
        if self.instance_manager:
            status["instances"] = self.instance_manager.get_all_status()
            
        if self.aggregator:
            status["aggregator"] = self.aggregator.get_status()
            
        return status
    
    def get_unified_context(self, max_tokens: int = None) -> str:
        """Get unified context from all sources"""
        if self.context_builder:
            return self.context_builder.build_unified_context(max_tokens)
        return ""
    
    def shutdown(self):
        """Shutdown the orchestration system"""
        print("🛑 Shutting down Master Controller...")
        self._running = False
        
        if self.instance_manager:
            for inst_id in list(self.instance_manager.instances.keys()):
                self.instance_manager.stop_instance(inst_id)
                
        if self.tunnel_manager:
            for tunnel_name in list(self.tunnel_manager.tunnels.keys()):
                # Would disconnect tunnels here
                pass
                
        if self.aggregator:
            self.aggregator.stop_aggregation()
            
        self.session.status = "complete"
        print("✅ Shutdown complete")


# Quick command handlers
def handle_status(controller: MasterController):
    """Handle status command"""
    print(json.dumps(controller.get_status(), indent=2, default=str))

def handle_rotate(controller: MasterController):
    """Handle rotation command"""
    results = controller.rotate_all()
    print(json.dumps(results, indent=2, default=str))

def handle_execute(controller: MasterController, task: str):
    """Handle execute command"""
    result = controller.execute_task(task)
    print(json.dumps(result, indent=2, default=str))

def handle_context(controller: MasterController):
    """Handle context command"""
    context = controller.get_unified_context()
    print(f"Context ({len(context)} chars):")
    print(context[:500] + "..." if len(context) > 500 else context)


# CLI Interface
def main():
    """Main CLI entry point"""
    controller = MasterController()
    
    if len(sys.argv) < 2:
        print("""
🎛️  Master Orchestration Controller

Usage:
  python master_controller.py init [mode]    - Initialize (single|federated|parallel)
  python master_controller.py status          - Show system status
  python master_controller.py rotate         - Rotate all tunnels/instances
  python master_controller.py exec <task>    - Execute a task
  python master_controller.py context        - Get unified context
  python master_controller.py shutdown        - Shutdown system
        """)
        return
        
    command = sys.argv[1]
    
    if command == "init":
        mode = OrchestrationMode.FEDERATED
        if len(sys.argv) > 2:
            mode = OrchestrationMode(sys.argv[2])
        controller.initialize(mode)
        handle_status(controller)
        
    elif command == "status":
        handle_status(controller)
        
    elif command == "rotate":
        handle_rotate(controller)
        
    elif command == "exec":
        if len(sys.argv) < 3:
            print("Usage: python master_controller.py exec <task>")
            return
        task = " ".join(sys.argv[2:])
        handle_execute(controller, task)
        
    elif command == "context":
        handle_context(controller)
        
    elif command == "shutdown":
        controller.shutdown()
        
    else:
        print(f"Unknown command: {command}")


if __name__ == "__main__":
    main()
