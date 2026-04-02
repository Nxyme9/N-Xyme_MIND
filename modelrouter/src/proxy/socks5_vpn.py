#!/usr/bin/env python3
"""Simple SOCKS5 proxy that routes through VPN tun0 interface."""
import socket
import threading
import struct
import signal
import sys

SO_BINDTODEVICE = 25
VPN_INTERFACE = b"tun0"

def handle_client(client):
    try:
        # SOCKS5 handshake
        data = client.recv(262)
        if not data or data[0] != 5:
            client.close()
            return
        # Send no-auth response
        client.sendall(b'\x05\x00')
        
        # Get connection request
        data = client.recv(262)
        if not data or len(data) < 7:
            client.close()
            return
        
        cmd = data[1]
        if cmd != 1:  # Only CONNECT supported
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
        
        # Connect to target through VPN
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        remote.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, VPN_INTERFACE)
        remote.settimeout(10)
        
        try:
            remote.connect((dst_addr, dst_port))
            # Send success response
            bind_addr, bind_port = remote.getsockname()
            client.sendall(b'\x05\x00\x00\x01' + socket.inet_aton(bind_addr) + struct.pack('>H', bind_port))
        except Exception as e:
            client.sendall(b'\x05\x05\x00\x01' + b'\x00' * 6)
            client.close()
            return
        
        # Relay data
        def forward(src, dst):
            try:
                while True:
                    data = src.recv(4096)
                    if not data:
                        break
                    dst.sendall(data)
            except:
                pass
            finally:
                try: src.close()
                except: pass
                try: dst.close()
                except: pass
        
        t1 = threading.Thread(target=forward, args=(client, remote), daemon=True)
        t2 = threading.Thread(target=forward, args=(remote, client), daemon=True)
        t1.start()
        t2.start()
        t1.join()
        
    except Exception as e:
        try: client.close()
        except: pass

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('127.0.0.1', 1080))
    server.listen(50)
    print(f"SOCKS5 proxy listening on 127.0.0.1:1080, routing through tun0")
    sys.stdout.flush()
    
    def signal_handler(sig, frame):
        server.close()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    while True:
        try:
            client, addr = server.accept()
            threading.Thread(target=handle_client, args=(client,), daemon=True).start()
        except:
            break

if __name__ == "__main__":
    main()
