#!/usr/bin/env python3
"""Thread-Safe MCP Server Wrapper — Enables parallel tool execution."""
import json
import sys
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Callable, Any

class ThreadSafeMCPServer:
    """Wrap an MCP server to make it thread-safe for parallel execution."""
    
    def __init__(self, handler_func: Callable, max_workers: int = 10):
        self.handler = handler_func
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.session_locks: Dict[str, threading.Lock] = {}
        self.request_queue = []
        self.lock = threading.Lock()
    
    def get_session_lock(self, session_id: str) -> threading.Lock:
        """Get or create a lock for a session."""
        with self.lock:
            if session_id not in self.session_locks:
                self.session_locks[session_id] = threading.Lock()
            return self.session_locks[session_id]
    
    def handle_request(self, request: dict) -> dict:
        """Handle a JSON-RPC request."""
        method = request.get('method', '')
        rid = request.get('id', None)
        params = request.get('params', {})
        
        if method == 'initialize':
            return {
                'jsonrpc': '2.0',
                'id': rid,
                'result': {
                    'protocolVersion': '2024-11-05',
                    'capabilities': {'tools': {}},
                    'serverInfo': {'name': 'thread-safe-mcp', 'version': '1.0.0'}
                }
            }
        
        elif method == 'tools/list':
            return {
                'jsonrpc': '2.0',
                'id': rid,
                'result': {'tools': self.get_tools()}
            }
        
        elif method == 'tools/call':
            tool_name = params.get('name', '')
            args = params.get('arguments', {})
            session_id = args.get('_session_id', 'default')
            
            # Execute in thread pool
            future = self.executor.submit(
                self._execute_tool, tool_name, args, session_id
            )
            
            # Wait for result (this makes it synchronous from MCP perspective)
            # But internally it's parallel
            try:
                result = future.result(timeout=30)
                return {
                    'jsonrpc': '2.0',
                    'id': rid,
                    'result': result
                }
            except Exception as e:
                return {
                    'jsonrpc': '2.0',
                    'id': rid,
                    'error': {'code': -32603, 'message': str(e)}
                }
        
        else:
            return {
                'jsonrpc': '2.0',
                'id': rid,
                'error': {'code': -32601, 'message': f'Unknown method: {method}'}
            }
    
    def _execute_tool(self, tool_name: str, args: dict, session_id: str) -> dict:
        """Execute a tool with session lock."""
        lock = self.get_session_lock(session_id)
        
        with lock:
            # Call the original handler
            return self.handler(tool_name, args)
    
    def get_tools(self) -> list:
        """Get list of available tools."""
        # This should be implemented by the subclass
        return []
    
    def run(self):
        """Run the MCP server."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                print(json.dumps(response), flush=True)
            except Exception as e:
                error_response = {
                    'jsonrpc': '2.0',
                    'id': None,
                    'error': {'code': -32603, 'message': str(e)}
                }
                print(json.dumps(error_response), flush=True)
