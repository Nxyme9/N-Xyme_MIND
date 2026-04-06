#!/usr/bin/env python3
"""
Simple SOCKS5 server for testing VPN rotation.
Uses only stdlib. Handles both IPv4 and IPv6.
"""

import socket
import select
import threading
import logging
import struct

logging.basicConfig(level=logging.INFO, format="%(asctime)s SOCKS5 %(message)s")
logger = logging.getLogger(__name__)


def recv_exactly(sock, n):
    """Receive exactly n bytes from socket."""
    data = b""
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data


def handle_client(client_sock, client_addr):
    """Handle a single SOCKS5 client connection."""
    try:
        # Read greeting: VER + NMETHODS
        greeting = recv_exactly(client_sock, 2)
        if not greeting or len(greeting) < 2 or greeting[0] != 5:
            logger.warning(f"Invalid greeting from {client_addr}")
            return

        n_methods = greeting[1]
        methods = recv_exactly(client_sock, n_methods)
        if not methods:
            return

        # Response: VER + METHOD (0 = no auth)
        client_sock.sendall(b"\x05\x00")

        # Read request: VER + CMD + RSV + ATYP
        request = recv_exactly(client_sock, 4)
        if not request or len(request) < 4:
            return

        ver, cmd, rsv, atyp = struct.unpack("!BBBB", request)

        # Read destination address
        if atyp == 1:  # IPv4
            addr_bytes = recv_exactly(client_sock, 4)
            if not addr_bytes:
                return
            dest_addr = socket.inet_ntoa(addr_bytes)
        elif atyp == 3:  # Domain name
            domain_len_byte = recv_exactly(client_sock, 1)
            if not domain_len_byte:
                return
            domain_len = domain_len_byte[0]
            domain_bytes = recv_exactly(client_sock, domain_len)
            if not domain_bytes:
                return
            dest_addr = domain_bytes.decode("utf-8", errors="replace")
        elif atyp == 4:  # IPv6
            addr_bytes = recv_exactly(client_sock, 16)
            if not addr_bytes:
                return
            dest_addr = socket.inet_ntop(socket.AF_INET6, addr_bytes)
        else:
            logger.warning(f"Unknown address type: {atyp}")
            return

        # Read destination port (exactly 2 bytes)
        port_bytes = recv_exactly(client_sock, 2)
        if not port_bytes or len(port_bytes) < 2:
            logger.warning(f"Failed to read port from {client_addr}")
            return

        dest_port = int(struct.unpack("!H", port_bytes)[0])
        logger.info(f"Connecting to {dest_addr}:{dest_port} (atyp={atyp}, port_type={type(dest_port)})")
        logger.debug(f"Connecting to {dest_addr}:{dest_port} (atyp={atyp})")

        if cmd == 2:  # BIND
            client_sock.sendall(b"\x05\x07\x00\x01\x00\x00\x00\x00\x00\x00")
            return

        if cmd == 3:  # UDP ASSOCIATE
            client_sock.sendall(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
            # Keep connection open
            while True:
                if not client_sock.recv(1024):
                    break
            return

        # CONNECT command
        try:
            # Try IPv4 first
            try:
                socket.inet_aton(dest_addr)
                remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                remote.settimeout(10)
                remote.connect((dest_addr, dest_port))
            except socket.error:
                try:
                    # Try IPv6
                    socket.inet_pton(socket.AF_INET6, dest_addr)
                    remote = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                    remote.settimeout(10)
                    remote.connect((dest_addr, dest_port))
                except socket.error:
                    # It's a domain name - resolve to IPv4
                    addr_info = socket.getaddrinfo(
                        dest_addr, dest_port, socket.AF_INET, socket.SOCK_STREAM
                    )
                    if not addr_info:
                        raise ValueError(f"No IPv4 address for {dest_addr}")
                    remote_addr = addr_info[0][4]
                    remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    remote.settimeout(10)
                    remote.connect(remote_addr)

            # Send success response
            local_addr, local_port = remote.getsockname()
            response = struct.pack(
                "!BBBBIH", 5, 0, 0, 1, socket.inet_aton(local_addr), local_port
            )
            client_sock.sendall(response)

            logger.info(f"{client_addr[0]}:{client_addr[1]} -> {dest_addr}:{dest_port}")

            # Relay data
            while True:
                readable, _, _ = select.select([client_sock, remote], [], [], 30)
                if not readable:
                    continue

                for sock in readable:
                    data = sock.recv(4096)
                    if not data:
                        return
                    if sock is client_sock:
                        remote.sendall(data)
                    else:
                        client_sock.sendall(data)

        except Exception as e:
            logger.error(f"Connection failed to {dest_addr}:{dest_port}: {e}")
            client_sock.sendall(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")

    except Exception as e:
        logger.error(f"Handler error: {e}")
    finally:
        try:
            client_sock.close()
        except:
            pass


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Simple SOCKS5 server")
    parser.add_argument("--port", type=int, default=1080)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((args.host, args.port))
    server.listen(128)

    logger.info(f"SOCKS5 server listening on {args.host}:{args.port}")

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
