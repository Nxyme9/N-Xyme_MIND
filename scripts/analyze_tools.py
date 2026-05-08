#!/usr/bin/env python3
"""Analyze all MCP tools in the N-Xyme system."""
import re
from pathlib import Path
from collections import defaultdict

tools = defaultdict(dict)

# Scan packages for @mcp.tool decorators
packages_dir = Path("packages")
for mcp_file in packages_dir.rglob("mcp_server.py"):
    package = mcp_file.parent.name
    try:
        content = mcp_file.read_text()
        lines = content.split('\n')
        
        for i, line in enumerate(lines):
            if '@mcp.tool' in line:
                for j in range(i+1, min(i+20, len(lines))):
                    if 'def ' in lines[j]:
                        match = re.search(r'def (\w+)\((.*?)\):', lines[j])
                        if match:
                            func_name = match.group(1)
                            params_str = match.group(2)
                            params = []
                            for p in params_str.split(','):
                                p = p.strip()
                                if p and '=' in p:
                                    param_name = p.split('=')[0].strip()
                                    param_name = re.sub(r':.*', '', param_name)
                                    if param_name and param_name != 'self':
                                        params.append(param_name)
                            
                            if package not in tools:
                                tools[package] = {}
                            tools[package][func_name] = {'params': params}
                        break
                    else:
                        break

# Print unique tool names
all_tools = set()
for pkg, pkg_tools in tools.items():
    for t in pkg_tools.keys():
        all_tools.add(t)

print(f"=== FOUND {len(all_tools)} UNIQUE TOOLS IN {len(tools)} PACKAGES ===\n")

print("=== TOOLS BY PACKAGE ===")
for pkg, pkg_tools in sorted(tools.items(), key=lambda x: -len(x[1])):
    print(f"\n{pkg} ({len(pkg_tools)} tools):")
    for t, info in list(pkg_tools.items())[:8]:
        print(f"  - {t}({', '.join(info['params'][:4])})")
    if len(pkg_tools) > 8:
        print(f"  ... and {len(pkg_tools)-8} more")

print("\n=== ALL TOOL NAMES ===")
for t in sorted(all_tools):
    print(f"  {t}")