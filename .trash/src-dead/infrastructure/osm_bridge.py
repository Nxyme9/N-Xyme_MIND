"""OSC Bridge — Open Sound Control protocol"""

import logging, socket
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)


class OSCBridge:
    def __init__(self, host: str = "127.0.0.1", port: int = 9000):
        self.host = host
        self.port = port
        self._handlers: Dict[str, Callable] = {}
        self._socket = None

    def register(self, address: str, handler: Callable):
        self._handlers[address] = handler

    def send(self, address: str, *args):
        try:
            import pythonosc
            from pythonosc import udp_client

            client = udp_client.SimpleUDPClient(self.host, self.port)
            client.send_message(address, list(args))
        except ImportError:
            logger.warning("pythonosc not installed")

    def start_server(self, listen_port: int = 9001):
        try:
            from pythonosc import dispatcher, osc_server
            import threading

            disp = dispatcher.Dispatcher()
            for addr, handler in self._handlers.items():
                disp.map(addr, handler)
            server = osc_server.ThreadingOSCUDPServer(("127.0.0.1", listen_port), disp)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            logger.info(f"OSC: Server started on port {listen_port}")
        except ImportError:
            logger.warning("pythonosc not installed")
