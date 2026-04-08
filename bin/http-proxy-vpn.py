#!/usr/bin/env python3
"""
HTTP Proxy that binds to ProtonVPN interface (proton0).
This allows all traffic to go through the existing VPN tunnel.
"""

import socket
import threading
import logging
import http.client
import urllib.parse

logging.basicConfig(level=logging.INFO, format="%(asctime)s HTTP-PROXY %(message)s")
logger = logging.getLogger(__name__)

# SO_BINDTODEVICE = 25 on Linux
SO_BINDTODEVICE = 25


def handle_client(client_sock, client_addr):
    """Handle a single HTTP proxy client connection."""
    try:
        # Read the HTTP request
        request = b""
        while b"\r\n\r\n" not in request:
            chunk = client_sock.recv(4096)
            if not chunk:
                return
            request += chunk
        
        request_str = request.decode('utf-8', errors='replace')
        lines = request_str.split('\r\n')
        
        if not lines:
            return
            
        # Parse request line
        parts = lines[0].split()
        if len(parts) < 3:
            return
            
        method, url, version = parts[0], parts[1], parts[2]
        
        logger.info(f"{method} {url} from {client_addr[0]}:{client_addr[1]}")
        
        # Handle CONNECT for HTTPS tunneling
        if method == "CONNECT":
            # Parse host:port from URL
            if ':' in url:
                host, port_str = url.split(':', 1)
                port = int(port_str)
            else:
                host = url
                port = 443
            
            # Create connection bound to proton0
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                remote.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, b'proton0')
            except Exception as e:
                logger.warning(f"Could not bind to proton0: {e}")
            
            try:
                remote.connect((host, port))
                # Send 200 Connection Established
                client_sock.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                logger.info(f"CONNECT tunnel established to {host}:{port}")
            except Exception as e:
                logger.error(f"Failed to connect to {host}:{port}: {e}")
                client_sock.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
                client_sock.close()
                return
            
            # Relay data between client and server
            import select
            try:
                while True:
                    r, _, _ = select.select([client_sock, remote], [], [], 30)
                    if not r:
                        continue
                    for sock in r:
                        data = sock.recv(8192)
                        if not data:
                            break
                        other = remote if sock is client_sock else client_sock
                        other.sendall(data)
            except Exception as e:
                logger.error(f"Relay error: {e}")
            finally:
                client_sock.close()
                remote.close()
            return
        
        # Parse URL for HTTP
        if url.startswith('http://'):
            parsed = urllib.parse.urlparse(url)
            host = parsed.hostname
            port = parsed.port or 80
            path = parsed.path or '/'
            if parsed.query:
                path += '?' + parsed.query
        else:
            # Relative URL - need to find Host header
            host = None
            port = 80
            path = url
            for line in lines[1:]:
                if line.lower().startswith('host:'):
                    host = line.split(':', 1)[1].strip()
                    if ':' in host:
                        host, port_str = host.split(':', 1)
                        port = int(port_str)
                    break
            
            if not host:
                client_sock.sendall(b"HTTP/1.1 400 Bad Request\r\n\r\n")
                return
        
        # Build headers (remove Host, add proxy-specific ones)
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                key, val = line.split(':', 1)
                headers[key.strip().lower()] = val.strip()
        
        # Create connection bound to proton0
        remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            remote.setsockopt(socket.SOL_SOCKET, SO_BINDTODEVICE, b'proton0')
        except Exception as e:
            logger.warning(f"Could not bind to proton0: {e}")
        
        remote.connect((host, port))
        
        # Build and send the request to remote
        remote_request = f"{method} {path} HTTP/1.1\r\n"
        for key, val in headers.items():
            if key != 'host':
                remote_request += f"{key}: {val}\r\n"
        remote_request += f"Host: {host}\r\n"
        remote_request += "Connection: close\r\n"
        remote_request += "\r\n"
        
        # Send headers + body (if POST)
        body_start = request_str.find('\r\n\r\n')
        if body_start > 0:
            body = request_str[body_start + 4:]
            if body:
                remote_request += body
        
        remote.sendall(remote_request.encode('utf-8'))
        
        # Relay response back to client
        while True:
            data = remote.recv(8192)
            if not data:
                break
            client_sock.sendall(data)
            
    except Exception as e:
        logger.error(f"Error handling client {client_addr}: {e}")
    finally:
        try:
            client_sock.close()
        except:
            pass


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="HTTP Proxy via ProtonVPN")
    parser.add_argument("--port", type=int, default=1083)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.host, args.port))
    server.listen(128)
    
    logger.info(f"HTTP proxy listening on {args.host}:{args.port} (via proton0)")
    logger.info("All traffic will route through ProtonVPN tunnel")
    
    try:
        while True:
            client_sock, client_addr = server.accept()
            t = threading.Thread(
                target=handle_client, args=(client_sock, client_addr), daemon=True
            )
            t.start()
    except KeyboardInterrupt:
        logger.info("Shutting down")
    finally:
        server.close()


if __name__ == "__main__":
    main()