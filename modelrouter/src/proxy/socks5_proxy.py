#!/usr/bin/env python3
"""
SOCKS5 Proxy that routes traffic through VPN interface (tun0)
For OpenCode-only VPN routing while keeping PC direct.
"""

import socket
import select
import threading
import struct
import sys
import os

# SOCKS5 constants
SOCKS_VERSION = 5
SOCKS_CMD_CONNECT = 1
SOCKS_ATYP_IPV4 = 1
SOCKS_ATYP_DOMAIN = 3

class SOCKS5Proxy:
    def __init__(self, bind_host='127.0.0.1', bind_port=1080, bind_interface=None):
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.bind_interface = bind_interface  # e.g., 'tun0'
        self.server_socket = None
        
    def start(self):
        """Start the SOCKS5 proxy server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.bind_host, self.bind_port))
            self.server_socket.listen(100)
            print(f"SOCKS5 proxy listening on {self.bind_host}:{self.bind_port}")
            if self.bind_interface:
                print(f"Outgoing traffic bound to interface: {self.bind_interface}")
            
            while True:
                client_socket, client_addr = self.server_socket.accept()
                print(f"Connection from {client_addr}")
                thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                thread.daemon = True
                thread.start()
                
        except KeyboardInterrupt:
            print("\nShutting down proxy...")
        finally:
            if self.server_socket:
                self.server_socket.close()
    
    def handle_client(self, client_socket):
        """Handle a SOCKS5 client connection"""
        try:
            # SOCKS5 greeting
            version = client_socket.recv(1)
            if not version or version[0] != SOCKS_VERSION:
                client_socket.close()
                return
            
            # Number of authentication methods
            n_methods = client_socket.recv(1)[0]
            methods = client_socket.recv(n_methods)
            
            # Reply: no authentication required
            client_socket.sendall(struct.pack('BB', SOCKS_VERSION, 0))
            
            # SOCKS5 request
            version = client_socket.recv(1)[0]
            if version != SOCKS_VERSION:
                client_socket.close()
                return
            
            cmd = client_socket.recv(1)[0]
            rsv = client_socket.recv(1)[0]  # Reserved
            
            if cmd != SOCKS_CMD_CONNECT:
                # Only support CONNECT
                self.send_reply(client_socket, 7)  # Command not supported
                client_socket.close()
                return
            
            # Read destination address
            atyp = client_socket.recv(1)[0]
            
            if atyp == SOCKS_ATYP_IPV4:
                addr = client_socket.recv(4)
                dst_addr = socket.inet_ntoa(addr)
            elif atyp == SOCKS_ATYP_DOMAIN:
                domain_len = client_socket.recv(1)[0]
                dst_addr = client_socket.recv(domain_len).decode('utf-8')
            else:
                self.send_reply(client_socket, 8)  # Address type not supported
                client_socket.close()
                return
            
            # Read destination port
            dst_port = struct.unpack('!H', client_socket.recv(2))[0]
            
            print(f"Connect to {dst_addr}:{dst_port}")
            
            # Connect to destination through VPN interface
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Bind to VPN interface if specified
            if self.bind_interface:
                # Get interface IP
                try:
                    import fcntl
                    import struct as struct2
                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    interface_ip = fcntl.ioctl(
                        s.fileno(),
                        0x8915,  # SIOCGIFADDR
                        struct2.pack('256s', self.bind_interface[:15].encode('utf-8'))
                    )[20:24]
                    interface_ip = socket.inet_ntoa(interface_ip)
                    remote_socket.bind((interface_ip, 0))
                    print(f"Bound to interface {self.bind_interface} ({interface_ip})")
                except Exception as e:
                    print(f"Warning: Could not bind to interface {self.bind_interface}: {e}")
                    print("Falling back to default routing")
            
            try:
                remote_socket.connect((dst_addr, dst_port))
                self.send_reply(client_socket, 0)  # Success
            except Exception as e:
                print(f"Connection failed: {e}")
                self.send_reply(client_socket, 5)  # Connection refused
                client_socket.close()
                return
            
            # Relay data between client and remote
            self.relay_data(client_socket, remote_socket)
            
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            client_socket.close()
    
    def send_reply(self, client_socket, status):
        """Send SOCKS5 reply"""
        reply = struct.pack('BBBBIH', SOCKS_VERSION, status, 0, 1, 0, 0)
        client_socket.sendall(reply)
    
    def relay_data(self, client_socket, remote_socket):
        """Relay data between client and remote"""
        try:
            while True:
                readable, _, _ = select.select([client_socket, remote_socket], [], [], 1)
                
                if not readable:
                    continue
                
                for sock in readable:
                    other = remote_socket if sock is client_socket else client_socket
                    
                    try:
                        data = sock.recv(4096)
                        if not data:
                            return
                        other.sendall(data)
                    except:
                        return
                        
        finally:
            remote_socket.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='SOCKS5 Proxy for VPN routing')
    parser.add_argument('--host', default='127.0.0.1', help='Bind host (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=1080, help='Bind port (default: 1080)')
    parser.add_argument('--interface', default='tun0', help='Outgoing interface (default: tun0)')
    
    args = parser.parse_args()
    
    proxy = SOCKS5Proxy(
        bind_host=args.host,
        bind_port=args.port,
        bind_interface=args.interface
    )
    
    proxy.start()


if __name__ == '__main__':
    main()
