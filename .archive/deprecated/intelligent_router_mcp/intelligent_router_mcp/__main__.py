#!/usr/bin/env python3
"""Entry point for: python3 -m intelligent_router_mcp"""
import sys
import os
# Add packages directory to path
pkg_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if pkg_dir not in sys.path:
    sys.path.insert(0, pkg_dir)
from . import main

if __name__ == "__main__":
    main()