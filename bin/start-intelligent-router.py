#!/usr/bin/env python3
"""Wrapper to start intelligent-router MCP server with fixed sys.path."""

import sys
import os

# Keep original sys.path but filter out the problematic uv paths
original_path = sys.path.copy()
sys.path = [p for p in sys.path if "cpython-3.12.13" not in p]

# Add our paths - go up from bin/ to project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "packages"))
sys.path.insert(0, os.path.join(project_root, "src", "infrastructure"))
sys.path.insert(0, project_root)

# Verify platform module is correct
import platform

print(f"platform.system(): {platform.system()}")
print(f"platform.python_implementation(): {platform.python_implementation()}")

# Now start the MCP server
from packages.infrastructure.proxy.mcp_server import (
    route_task,
    record_success,
    record_failure,
)
from packages.infrastructure.proxy.mcp_server import (
    get_router_status,
    get_available_models,
    get_routing_history,
)

print("=== Intelligent Router MCP Server ===")
print(f"Python: {sys.version}")
print(f"Using: {sys.executable}")

# Quick test
result = route_task("test", agent_type="test")
print(f"Test route: {result.get('model')}")

# Keep running
import time

while True:
    time.sleep(1)
