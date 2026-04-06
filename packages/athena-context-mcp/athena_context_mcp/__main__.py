"""
athena-context-mcp entry point.
"""

from athena_context_mcp import mcp
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Athena Context MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--port", type=int, default=8766, help="SSE port")
    args = parser.parse_args()
    
    if args.sse:
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")