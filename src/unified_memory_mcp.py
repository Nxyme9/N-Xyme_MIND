#!/usr/bin/env python3
"""
Unified Memory MCP Server
Provides memory search over both opencode.db and Graphiti via MCP stdio interface.
"""

import json
import sqlite3
import sys
try:
    import httpx
except ImportError:
    httpx = None
from typing import Dict, Any, List, Optional

OPENCODE_DB = "./data/opencode/opencode.db"
GRAPHITI_URL = "http://localhost:8001/json-rpc"

def log(msg: str):
    """Log to stderr to avoid interfering with stdio MCP communication."""
    print(msg, file=sys.stderr)

def search_opencode(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search opencode.db for messages containing the query."""
    results = []
    try:
        conn = sqlite3.connect(OPENCODE_DB)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.data, m.time_created 
            FROM part p 
            JOIN message m ON p.message_id = m.id 
            WHERE p.data LIKE ? 
            ORDER BY m.time_created DESC 
            LIMIT ?
        """, (f'%{query}%', limit))
        
        for row in cursor.fetchall():
            data_str, timestamp = row
            try:
                content = json.loads(data_str)
                if content.get('type') == 'text':
                    results.append({
                        'source': 'opencode',
                        'text': content.get('text', ''),
                        'timestamp': timestamp,
                        'type': 'episode'  # Match Graphiti's episode structure
                    })
            except (json.JSONDecodeError, KeyError):
                pass
        conn.close()
    except Exception as e:
        log(f"Error searching opencode.db: {e}")
    return results

def search_graphiti(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Search Graphiti for episodes matching the query."""
    results = []
    try:
        resp = httpx.post(GRAPHITI_URL, json={
            "jsonrpc": "2.0",
            "method": "graphiti_search_nodes",
            "params": {"query": query, "limit": limit},
            "id": 1
        }, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            graphiti_results = data.get('result', {}).get('episodes', [])
            for ep in graphiti_results:
                results.append({
                    'source': 'graphiti',
                    'text': ep.get('text', ''),
                    'timestamp': ep.get('created', ''),
                    'type': 'episode'
                })
    except Exception as e:
        log(f"Error searching Graphiti: {e}")
    return results

def handle_initialize(request_id: Any) -> Dict[str, Any]:
    """Handle MCP initialize request."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "unified-memory-mcp",
                "version": "1.0.0"
            }
        }
    }

def handle_tools_list(request_id: Any) -> Dict[str, Any]:
    """Handle MCP tools/list request."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "tools": [
                {
                    "name": "memory_search",
                    "description": "Search memories from both opencode.db and Graphiti",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Text to search for"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of results to return",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                }
            ]
        }
    }

def handle_tools_call(request_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP tools/call request."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})
    
    if tool_name == "memory_search":
        query = arguments.get("query", "")
        limit = arguments.get("limit", 10)
        
        # Search both sources
        opencode_results = search_opencode(query, limit)
        graphiti_results = search_graphiti(query, limit)
        
        # Combine and limit
        combined = opencode_results + graphiti_results
        if len(combined) > limit:
            combined = combined[:limit]
        
        # Format as MCP text content
        text_content = "\n\n".join([
            f"[{r['source']}] {r['text'][:200]}{'...' if len(r['text']) > 200 else ''}"
            for r in combined
        ])
        
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": text_content
                    }
                ]
            }
        }
    else:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32601,
                "message": f"Tool not found: {tool_name}"
            }
        }

def main():
    """Main MCP server loop."""
    log("Starting Unified Memory MCP Server...")
    
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                log(f"Invalid JSON received: {e}")
                continue
            
            method = request.get("method")
            request_id = request.get("id")
            
            if method == "initialize":
                response = handle_initialize(request_id)
            elif method == "tools/list":
                response = handle_tools_list(request_id)
            elif method == "tools/call":
                response = handle_tools_call(request_id, request.get("params", {}))
            elif method == "notifications/initialized":
                # Notification, no response needed
                continue
            else:
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: {method}"
                    }
                }
            
            # Send response to stdout
            print(json.dumps(response))
            sys.stdout.flush()
            
        except BrokenPipeError:
            break
        except Exception as e:
            log(f"Error in MCP loop: {e}")
            # Try to send error response if we have an ID
            if 'request_id' in locals() and request_id is not None:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {e}"
                    }
                }
                print(json.dumps(error_response))
                sys.stdout.flush()

if __name__ == "__main__":
    main()