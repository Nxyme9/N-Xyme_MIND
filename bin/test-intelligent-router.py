#!/usr/bin/env python3
"""Direct import wrapper for intelligent-router MCP - avoids packages/ namespace collision."""

import sys
import os
import importlib.util

# Remove problematic uv paths
sys.path = [p for p in sys.path if "cpython-3.12.13" not in p]

project_root = "/home/nxyme/N-Xyme_CODE/N-Xyme_MIND"
proxy_dir = os.path.join(project_root, "packages", "infrastructure", "proxy")

print("Testing stdlib imports...")
# Verify stdlib works
stdlib_platform = __import__("platform")
print(f"  platform.system(): {stdlib_platform.system()}")
stdlib_uuid = __import__("uuid")
print(f"  uuid imported: OK")
stdlib_logging = __import__("logging")
print(f"  logging imported: OK")

# Load modules directly from file to avoid package namespace issues
print("\nLoading intelligent_router module...")


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# Load each dependency
print("  Loading router_brain...")
router_brain = load_module("router_brain", os.path.join(proxy_dir, "router_brain.py"))

print("  Loading learning_engine...")
learning_engine = load_module(
    "learning_engine", os.path.join(proxy_dir, "learning_engine.py")
)

print("  Loading api_key_pool...")
api_key_pool = load_module("api_key_pool", os.path.join(proxy_dir, "api_key_pool.py"))

print("  Loading vpn_ip_pool...")
vpn_ip_pool = load_module("vpn_ip_pool", os.path.join(proxy_dir, "vpn_ip_pool.py"))

print("  Loading cost_optimizer...")
cost_optimizer = load_module(
    "cost_optimizer", os.path.join(proxy_dir, "cost_optimizer.py")
)

print("  Loading agent_preferences...")
agent_preferences = load_module(
    "agent_preferences", os.path.join(proxy_dir, "agent_preferences.py")
)

print("  Loading dashboard...")
dashboard = load_module("dashboard", os.path.join(proxy_dir, "dashboard.py"))

print("  Loading stall_detector...")
stall_detector = load_module(
    "stall_detector", os.path.join(proxy_dir, "stall_detector.py")
)

print("  Loading key_notifier...")
key_notifier = load_module("key_notifier", os.path.join(proxy_dir, "key_notifier.py"))

print("  Loading intelligent_router...")
intelligent_router = load_module(
    "intelligent_router", os.path.join(proxy_dir, "intelligent_router.py")
)

# Get the instance
ir = intelligent_router.intelligent_router

# Test
print("\nTesting route_task...")
result = ir.select_route("hello world", agent_type="test")
print(f"  model: {result.get('model')}")
print(f"  best_model: {result.get('analysis', {}).get('best_model')}")
print(f"  match: {result.get('model') == result.get('analysis', {}).get('best_model')}")
print(f"  selection_reason: {result.get('selection_reason')}")

print("\n=== SUCCESS ===")
