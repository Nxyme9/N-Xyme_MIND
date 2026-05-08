#!/usr/bin/env python3
"""Entry point for brain_mcp package."""

from packages.brain_mcp import mcp

if __name__ == "__main__":
    import sys

    if "--http" in sys.argv:
        port = 8765
        for i, arg in enumerate(sys.argv):
            if arg == "--port" and i + 1 < len(sys.argv):
                port = int(sys.argv[i + 1])
        mcp.run(transport="http", host="0.0.0.0", port=port)
    else:
        mcp.run(transport="stdio")
