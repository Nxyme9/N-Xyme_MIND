#!/usr/bin/env python3
"""
Brain MCP Server - Exposes brain-cli as MCP tools
Implements JSON-RPC 2.0 stdio protocol for OpenCode integration
"""

import sys
import json
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

API_URL = "http://localhost:8100/brain/execute"


def handle_jsonrpc(request: dict) -> dict:
    """Handle JSON-RPC 2.0 request"""
    method = request.get("method", "")
    request_id = request.get("id", 1)

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {"name": "brain-mcp", "version": "1.0.0"},
                "capabilities": {"tools": {}},
            },
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "tools": [
                    {
                        "name": "brain_execute",
                        "description": "Execute brain CLI tool calling - searches files, memory, and runs AI commands",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "message": {
                                    "type": "string",
                                    "description": "Message/prompt to send to brain",
                                },
                                "model": {
                                    "type": "string",
                                    "description": "Model to use (qwen2.5-coder:7b or llama3.2:3b)",
                                    "default": "qwen2.5-coder:7b",
                                },
                            },
                            "required": ["message"],
                        },
                    },
                    {
                        "name": "brain_search_files",
                        "description": "Search for files matching a pattern",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "pattern": {
                                    "type": "string",
                                    "description": "File pattern to search for",
                                }
                            },
                            "required": ["pattern"],
                        },
                    },
                    {
                        "name": "brain_search_memory",
                        "description": "Search memory for relevant content",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "query": {
                                    "type": "string",
                                    "description": "Search query",
                                }
                            },
                            "required": ["query"],
                        },
                    },
                ]
            },
        }

    elif method == "tools/call":
        params = request.get("params", {})
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})

        # Import and call brain functions
        import urllib.request
        import urllib.error

        message = tool_args.get("message", "")
        model = tool_args.get("model", "qwen2.5-coder:7b")

        # For specialized tools, construct the message
        if tool_name == "brain_search_files":
            pattern = tool_args.get("pattern", "")
            message = f"search for files named {pattern}"
            model = "qwen2.5-coder:7b"
        elif tool_name == "brain_search_memory":
            query = tool_args.get("query", "")
            message = f"search memory for {query}"
            model = "qwen2.5-coder:7b"

        # Make API call
        data = json.dumps({"message": message, "model": model}).encode("utf-8")
        req = urllib.request.Request(
            API_URL, data=data, headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))

                # Extract result content
                if "result" in result:
                    content = result["result"]
                else:
                    content = result

                return {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(content, indent=2)}
                        ]
                    },
                }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": -32603, "message": str(e)},
            }

    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main():
    """Main MCP stdio server loop"""
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)
            response = handle_jsonrpc(request)

            print(json.dumps(response), flush=True)

        except json.JSONDecodeError:
            continue
        except KeyboardInterrupt:
            break
        except Exception as e:
            error_response = {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32603, "message": str(e)},
            }
            print(json.dumps(error_response), flush=True)


if __name__ == "__main__":
    main()
