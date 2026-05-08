"""
nx-mind-mcp entry point.
"""

from nx_mind_mcp import mcp
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="N-Xyme MIND MCP Server")
    parser.add_argument("--sse", action="store_true", help="Use SSE transport")
    parser.add_argument("--port", type=int, default=8767, help="SSE port")
    args = parser.parse_args()
    
    if args.sse:
        mcp.run(transport="sse", port=args.port)
    else:
        mcp.run(transport="stdio")
