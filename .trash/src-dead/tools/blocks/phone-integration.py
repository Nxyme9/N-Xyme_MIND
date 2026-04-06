"""
Phone App Integration — Start all Jarvis remote control services.

Launches:
1. FastAPI API server (PWA dashboard + REST API)
2. Telegram bot (quick commands)
3. Voice WebSocket server (voice streaming)

Usage:
    python scripts/phone-integration.py              # Start all services
    python scripts/phone-integration.py --api-only   # API server only
    python scripts/phone-integration.py --telegram   # Telegram bot only
    python scripts/phone-integration.py --voice      # Voice WebSocket only
    python scripts/phone-integration.py --qr         # Show QR code for phone pairing

Environment Variables:
    JARVIS_API_HOST      API server host (default: 0.0.0.0)
    JARVIS_API_PORT      API server port (default: 8088)
    TELEGRAM_BOT_TOKEN   Telegram bot token from BotFather
    JARVIS_VOICE_PORT    Voice WebSocket port (default: 5005)
    JARVIS_VOICE_SSL     Enable SSL for voice (default: false)
"""

import argparse
import asyncio
import logging
import os
import signal
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import centralized configuration
try:
    from jarvis.config.graphiti_config import JARVIS_API_URL
except ImportError:
    JARVIS_API_URL = os.getenv("JARVIS_API_URL", "http://localhost:8088")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("phone-integration")

# ── Configuration ──────────────────────────────────────────────────────────

DEFAULT_API_HOST = "127.0.0.1"
DEFAULT_API_PORT = 8088
DEFAULT_VOICE_PORT = 5005


def get_local_ip() -> str:
    """Get the local IP address of this machine."""
    try:
        # Connect to external address to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


def get_api_key() -> Optional[str]:
    """Load API key from config file."""
    api_key_file = PROJECT_ROOT / "configs" / "jarvis" / "api_key.json"
    if api_key_file.exists():
        try:
            import json as json_mod

            data = json_mod.loads(api_key_file.read_text(encoding="utf-8"))
            return data.get("api_key")
        except (ValueError, OSError, KeyError):
            pass
    return None


def generate_qr_code(url: str) -> str:
    """Generate ASCII QR code for phone pairing."""
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_L

        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_L,
            box_size=1,
            border=1,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Try to use make_ascii if available, otherwise fallback to string representation
        if hasattr(qr, "make_ascii"):
            return qr.make_ascii()  # type: ignore[attr-defined]
        else:
            # Fallback: create a simple ASCII representation
            return f"[Install qrcode[pil] for ASCII QR code]\nURL: {url}"
    except ImportError:
        return f"[QR code requires: pip install qrcode]\nURL: {url}"


# ── Service Starters ──────────────────────────────────────────────────────


class ServiceManager:
    """Manages all phone integration services."""

    def __init__(self):
        self.api_server: Any = None
        self.telegram_bot: Any = None
        self.voice_server: Any = None
        self._running = False
        self._threads = []

    def start_api_server(
        self,
        host: str = DEFAULT_API_HOST,
        port: int = DEFAULT_API_PORT,
    ) -> None:
        """Start the FastAPI API server."""
        try:
            from jarvis.api.server import JarvisAPIServer

            self.api_server = JarvisAPIServer(host=host, port=port)
            self.api_server.start(daemon=True)
            logger.info(f"API Server: Started on http://{host}:{port}")
        except Exception as e:
            logger.error(f"API Server: Failed to start: {e}")
            raise

    def start_telegram_bot(
        self,
        token: Optional[str] = None,
        jarvis_url: str = JARVIS_API_URL,
    ) -> None:
        """Start the Telegram bot."""
        try:
            from jarvis.api.telegram_bot import JarvisTelegramBot

            self.telegram_bot = JarvisTelegramBot(token=token, jarvis_url=jarvis_url)

            def run_bot():
                try:
                    self.telegram_bot.run()  # type: ignore[union-attr]
                except Exception as e:
                    logger.error(f"Telegram Bot: Error: {e}")

            thread = threading.Thread(target=run_bot, daemon=True, name="telegram-bot")
            thread.start()
            self._threads.append(thread)
            logger.info("Telegram Bot: Started polling")
        except ValueError as e:
            logger.warning(f"Telegram Bot: Skipped (no token): {e}")
        except Exception as e:
            logger.error(f"Telegram Bot: Failed to start: {e}")

    def start_voice_server(
        self,
        host: str = "localhost",
        port: int = DEFAULT_VOICE_PORT,
        enable_ssl: bool = False,
    ) -> None:
        """Start the voice WebSocket server."""
        try:
            from jarvis.api.voice_ws import create_voice_server

            self.voice_server = create_voice_server(
                host=host,
                port=port,
                enable_ssl=enable_ssl,
            )

            def run_voice():
                try:
                    self.voice_server.run()  # type: ignore[union-attr]
                except Exception as e:
                    logger.error(f"Voice Server: Error: {e}")

            thread = threading.Thread(target=run_voice, daemon=True, name="voice-server")
            thread.start()
            self._threads.append(thread)
            logger.info(f"Voice Server: Started on ws://{host}:{port}/voice")
        except Exception as e:
            logger.error(f"Voice Server: Failed to start: {e}")

    def stop_all(self) -> None:
        """Stop all services."""
        self._running = False
        logger.info("Stopping all services...")

        if self.api_server:
            try:
                asyncio.run(self.api_server.stop())  # type: ignore[union-attr]
            except Exception as e:
                logger.debug(f"API server stop error: {e}")

        if self.voice_server:
            try:
                # Voice server doesn't have a clean stop method
                pass
            except Exception as e:
                logger.debug(f"Voice server stop error: {e}")

        logger.info("All services stopped")


# ── Main ──────────────────────────────────────────────────────────────────


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Jarvis Phone App Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/phone-integration.py              Start all services
  python scripts/phone-integration.py --api-only   API server only
  python scripts/phone-integration.py --qr         Show QR code for pairing
  python scripts/phone-integration.py --telegram   Telegram bot only
        """,
    )

    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Start only the API server",
    )
    parser.add_argument(
        "--telegram",
        action="store_true",
        help="Start only the Telegram bot",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Start only the voice WebSocket server",
    )
    parser.add_argument(
        "--qr",
        action="store_true",
        help="Show QR code for phone pairing",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("JARVIS_API_HOST", DEFAULT_API_HOST),
        help=f"API server host (default: {DEFAULT_API_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("JARVIS_API_PORT", DEFAULT_API_PORT)),
        help=f"API server port (default: {DEFAULT_API_PORT})",
    )
    parser.add_argument(
        "--voice-port",
        type=int,
        default=int(os.getenv("JARVIS_VOICE_PORT", DEFAULT_VOICE_PORT)),
        help=f"Voice WebSocket port (default: {DEFAULT_VOICE_PORT})",
    )
    parser.add_argument(
        "--ssl",
        action="store_true",
        default=os.getenv("JARVIS_VOICE_SSL", "false").lower() == "true",
        help="Enable SSL for voice WebSocket",
    )

    args = parser.parse_args()

    # Show QR code and exit
    if args.qr:
        api_key = get_api_key()
        local_ip = get_local_ip()
        url = f"http://{local_ip}:{args.port}"
        if api_key:
            url += f"?key={api_key}"

        print("\n" + "=" * 50)
        print("  Jarvis Phone Pairing")
        print("=" * 50)
        print(f"\n  URL: {url}")
        print(f"  API Key: {api_key or 'Not generated yet'}")
        print("\n  Scan this QR code with your phone:\n")
        print(generate_qr_code(url))
        print("\n  Or open the URL in your phone's browser.")
        print("=" * 50 + "\n")
        return

    # Determine which services to start
    start_all = not (args.api_only or args.telegram or args.voice)

    # Create service manager
    manager = ServiceManager()

    # Handle shutdown signals
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, shutting down...")
        manager.stop_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start services
    print("\n" + "=" * 50)
    print("  Jarvis Phone Integration")
    print("=" * 50 + "\n")

    if start_all or args.api_only:
        manager.start_api_server(host=args.host, port=args.port)

    if start_all or args.telegram:
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        jarvis_url = f"http://localhost:{args.port}"
        manager.start_telegram_bot(token=telegram_token, jarvis_url=jarvis_url)

    if start_all or args.voice:
        manager.start_voice_server(
            host="localhost",
            port=args.voice_port,
            enable_ssl=args.ssl,
        )

    # Show connection info
    local_ip = get_local_ip()
    api_key = get_api_key()

    print("\n" + "-" * 50)
    print("  Connection Info")
    print("-" * 50)
    print(f"  Local IP:   {local_ip}")
    print(f"  API URL:    http://{local_ip}:{args.port}")
    print(f"  API Key:    {api_key or 'Not generated yet'}")
    print(f"  Voice WS:   ws://localhost:{args.voice_port}/voice")
    print("-" * 50)
    print("\n  Open the URL above on your phone to connect.")
    print("  Press Ctrl+C to stop all services.\n")

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        manager.stop_all()


if __name__ == "__main__":
    main()
