"""
context-store entry point.
"""

from packages.context_store import mcp
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="N-Xyme Context MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--port", type=int, default=8766, help="SSE port")
    args = parser.parse_args()

    if args.sse:
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")
