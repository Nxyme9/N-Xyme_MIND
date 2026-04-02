#!/usr/bin/env python3
"""
Multi-Tunnel VPN Manager - Bleeding Edge
Manages multiple simultaneous VPN tunnels for federated orchestration
"""
import socket
import threading
import subprocess
import time
import json
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime
import hashlib

# VPN Configuration
VPN_CONNECTIONS = {
    "NL": "ProtonVPN-NL-FREE",
    "NL2": "ProtonVPN-NL-2-FREE",
    "JP": "ProtonVPN-JP-FREE",
    "JP2": "ProtonVPN-JP-2-FREE",
    "CA": "ProtonVPN-CA-FREE",
    "CA2": "ProtonVPN-CA-2-FREE",
    "NO": "ProtonVPN-NO-FREE",
    "NO2": "ProtonVPN-NO-2-FREE",
    "PL": "ProtonVPN-PL-FREE",
    "RO": "ProtonVPN-RO-FREE",
    "RO2": "ProtonVPN-RO-2-FREE",
}

BASE_SOCKS_PORT = 1080
TUNNEL_CONFIG_DIR = "/home/nxyme/projects/modelrouter/configs/tunnels"

@dataclass
class Tunnel:
    name: str
    country: str
    connection_name: str
    socks_port: int
    interface: str = "tun0"  # Will be assigned dynamically
    ip: str = ""
    status: str = "disconnected"  # connecting, connected, disconnected, error
    last_rotation: datetime = field(default_factory=datetime.now)
    request_count: int = 0
    error_count: int = 0

class SOCKS5Proxy(threading.Thread):
    """SOCKS5 proxy bound to specific VPN interface"""
    
    def __init__(self, port: int, interface: str = "tun0"):
        super().__init__(daemon=True)
        self.port = port
        self.interface = interface
        self.running = False
        self.server = None
        self.SO_BINDTODEVICE = 25
        
    def run(self):
        self.running = True
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server.bind(('127.0.0.1', self.port))
            self.server.listen(50)
            print(f"🌐 SOCKS5 proxy started on 127.0.0.1:{self.port} → {self.interface}")
            
            while self.running:
                try:
                    client, addr = self.server.accept()
                    threading.Thread(target=self.handle_client, args=(client,), daemon=True).start()
                except:
                    break
        except Exception as e:
            print(f"❌ SOCKS5 proxy error on port {self.port}: {e}")
            
    def handle_client(self, client):
        try:
            # SOCKS5 handshake
            data = client.recv(262)
            if not data or data[0] != 5:
                client.close()
                return
            client.sendall(b'\x05\x00')
            
            # Connection request
            data = client.recv(262)
            if not data or len(data) < 7:
                client.close()
                return
                
            cmd = data[1]
            if cmd != 1:
                client.sendall(b'\x05\x07\x00\x01' + b'\x00' * 6)
                client.close()
                return
            
            atyp = data[3]
            if atyp == 1:  # IPv4
                dst_addr = socket.inet_ntoa(data[4:8])
                dst_port = struct.unpack('>H', data[8:10])[0]
            elif atyp == 3:  # Domain
                domain_len = data[4]
                dst_addr = data[5:5+domain_len].decode()
                dst_port = struct.unpack('>H', data[5+domain_len:7+domain_len])[0]
            else:
                client.sendall(b'\x05\x08\x00\x01' + b'\x00' * 6)
                client.close()
                return
            
            # Connect through VPN interface
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                # Bind to specific interface
                if self.interface.startswith("tun"):
                    remote.setsockopt(socket.SOL_SOCKET, self.SO_BINDTODEVICE, self.interface.encode())
            except:
                pass  # Fallback if interface binding fails
            remote.settimeout(30)
            remote.connect((dst_addr, dst_port))
            
            # Success response
            bind_addr, bind_port = remote.getsockname()
            client.sendall(b'\x05\x00\x00\x01' + socket.inet_aton(bind_addr) + struct.pack('>H', bind_port))
            
            # Data relay
            self.relay(client, remote)
            
        except Exception as e:
            try:
                client.sendall(b'\x05\x05\x00\x01' + b'\x00' * 6)
            except:
                pass
        finally:
            try:
                client.close()
            except:
                pass
                
    def relay(self, client, remote):
        def forward(src, dst):
            try:
                while True:
                    data = src.recv(8192)
                    if not data:
                        break
                    dst.sendall(data)
            except:
                pass
            finally:
                try:
                    src.close()
                    dst.close()
                except:
                    pass
        
        t1 = threading.Thread(target=forward, args=(client, remote), daemon=True)
        t2 = threading.Thread(target=forward, args=(remote, client), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        t2.join()
        
    def stop(self):
        self.running = False
        try:
            self.server.close()
        except:
            pass


import struct

class MultiTunnelManager:
    """
    Federated Multi-Tunnel Manager
    Manages multiple VPN tunnels for parallel execution
    """
    
    def __init__(self, num_tunnels: int = 5):
        self.num_tunnels = num_tunnels
        self.tunnels: Dict[str, Tunnel] = {}
        self.proxies: Dict[str, SOCKS5Proxy] = {}
        self.rotation_callbacks: List[Callable] = []
        self._lock = threading.Lock()
        
        # Ensure config directory exists
        os.makedirs(TUNNEL_CONFIG_DIR, exist_ok=True)
        
    def initialize_tunnels(self, countries: List[str] = None):
        """Initialize specified number of tunnels"""
        if countries is None:
            countries = list(VPN_CONNECTIONS.keys())[:self.num_tunnels]
            
        for i, country in enumerate(countries):
            if country not in VPN_CONNECTIONS:
                continue
                
            tunnel_name = f"tunnel_{country}"
            tunnel = Tunnel(
                name=tunnel_name,
                country=country,
                connection_name=VPN_CONNECTIONS[country],
                socks_port=BASE_SOCKS_PORT + i
            )
            self.tunnels[tunnel_name] = tunnel
            print(f"✅ Initialized tunnel: {tunnel_name} → {country} (port {tunnel.socks_port})")
            
    def connect_tunnel(self, tunnel_name: str) -> bool:
        """Connect a specific tunnel"""
        if tunnel_name not in self.tunnels:
            return False
            
        tunnel = self.tunnels[tunnel_name]
        tunnel.status = "connecting"
        
        try:
            # Disconnect any existing
            subprocess.run(["nmcli", "connection", "down", "id", tunnel.connection_name],
                         capture_output=True, timeout=10)
            time.sleep(1)
            
            # Connect new
            result = subprocess.run(["nmcli", "connection", "up", "id", tunnel.connection_name],
                                  capture_output=True, timeout=30)
            
            if result.returncode != 0:
                tunnel.status = "error"
                tunnel.error_count += 1
                return False
                
            time.sleep(5)
            
            # Find the tun interface
            tunnel.interface = self._find_tun_interface()
            tunnel.ip = self._get_vpn_ip(tunnel.interface)
            tunnel.status = "connected"
            tunnel.last_rotation = datetime.now()
            
            # Start SOCKS5 proxy
            self._start_proxy(tunnel)
            
            print(f"✅ Connected: {tunnel_name} | IP: {tunnel.ip} | Port: {tunnel.socks_port}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect {tunnel_name}: {e}")
            tunnel.status = "error"
            tunnel.error_count += 1
            return False
    
    def _find_tun_interface(self) -> str:
        """Find the active tun interface"""
        result = subprocess.run(["ip", "link", "show"],
                              capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'tun' in line:
                return line.split(':')[1].strip()
        return "tun0"  # Fallback
    
    def _get_vpn_ip(self, interface: str) -> str:
        """Get IP address of VPN interface"""
        try:
            result = subprocess.run(
                ["curl", "--interface", interface, "-s", "http://ip-api.com/json"],
                capture_output=True, text=True, timeout=10
            )
            data = json.loads(result.stdout)
            return data.get("query", "unknown")
        except:
            return "unknown"
    
    def _start_proxy(self, tunnel: Tunnel):
        """Start SOCKS5 proxy for tunnel"""
        if tunnel.name in self.proxies:
            self.proxies[tunnel.name].stop()
            
        proxy = SOCKS5Proxy(tunnel.socks_port, tunnel.interface)
        proxy.start()
        self.proxies[tunnel.name] = proxy
    
    def rotate_tunnel(self, tunnel_name: str) -> bool:
        """Rotate a specific tunnel to new IP"""
        with self._lock:
            tunnel = self.tunnels.get(tunnel_name)
            if not tunnel:
                return False
                
            # Stop proxy
            if tunnel.name in self.proxies:
                self.proxies[tunnel.name].stop()
                del self.proxies[tunnel.name]
            
            # Disconnect
            try:
                subprocess.run(["nmcli", "connection", "down", "id", tunnel.connection_name],
                             capture_output=True, timeout=10)
            except:
                pass
                
            time.sleep(2)
            
            # Reconnect
            return self.connect_tunnel(tunnel_name)
    
    def rotate_all(self) -> Dict[str, bool]:
        """Rotate all tunnels"""
        results = {}
        for tunnel_name in self.tunnels:
            results[tunnel_name] = self.rotate_tunnel(tunnel_name)
        return results
    
    def get_status(self) -> Dict:
        """Get status of all tunnels"""
        status = {
            "total_tunnels": len(self.tunnels),
            "connected": 0,
            "tunnels": {}
        }
        
        for name, tunnel in self.tunnels.items():
            status["tunnels"][name] = {
                "country": tunnel.country,
                "ip": tunnel.ip,
                "port": tunnel.socks_port,
                "status": tunnel.status,
                "requests": tunnel.request_count,
                "errors": tunnel.error_count,
                "last_rotation": tunnel.last_rotation.isoformat()
            }
            if tunnel.status == "connected":
                status["connected"] += 1
                
        return status
    
    def get_best_tunnel(self) -> Optional[Tunnel]:
        """Get the best available tunnel (least used, no errors)"""
        best = None
        best_score = float('inf')
        
        for tunnel in self.tunnels.values():
            if tunnel.status != "connected":
                continue
                
            # Score: lower is better
            score = tunnel.request_count + (tunnel.error_count * 10)
            
            if score < best_score:
                best_score = score
                best = tunnel
                
        return best
    
    def record_request(self, tunnel_name: str):
        """Record a request through tunnel"""
        if tunnel_name in self.tunnels:
            self.tunnels[tunnel_name].request_count += 1
    
    def record_error(self, tunnel_name: str):
        """Record an error on tunnel"""
        if tunnel_name in self.tunnels:
            self.tunnels[tunnel_name].error_count += 1


# Singleton instance
_tunnel_manager = None

def get_tunnel_manager(num_tunnels: int = 5) -> MultiTunnelManager:
    global _tunnel_manager
    if _tunnel_manager is None:
        _tunnel_manager = MultiTunnelManager(num_tunnels)
    return _tunnel_manager


if __name__ == "__main__":
    print("🚀 Starting Multi-Tunnel Manager...")
    manager = get_tunnel_manager(5)
    
    # Initialize with first 5 countries
    countries = ["NL", "NL2", "JP", "CA", "NO"]
    manager.initialize_tunnels(countries)
    
    # Connect all
    for tunnel_name in manager.tunnels:
        manager.connect_tunnel(tunnel_name)
        time.sleep(3)
    
    print("\n📊 Status:")
    print(json.dumps(manager.get_status(), indent=2))
