"""CLI entry point for core-mcp server."""

import asyncio
import sys

from fastmcp.utilities.logging import configure_logging

from core_mcp import mcp


async def run_stdio():
    """Run in stdio mode."""
    await mcp.run_async()


async def run_sse(host: str = "localhost", port: int = 8000):
    """Run in SSE mode."""
    from fastmcp.server import SseServer

    server = SseServer(mcp)
    await server.run(host=host, port=port)


def main():
    """Main entry point."""
    import logging
    configure_logging("INFO", logger=logging.getLogger("core_mcp"))

    mode = sys.argv[1] if len(sys.argv) > 1 else "stdio"

    if mode == "sse":
        host = sys.argv[2] if len(sys.argv) > 2 else "localhost"
        port = int(sys.argv[3] if len(sys.argv) > 3 else "8000")
        asyncio.run(run_sse(host, port))
    else:
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
