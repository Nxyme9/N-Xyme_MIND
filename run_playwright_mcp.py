#!/usr/bin/env python3
import os

os.environ["PLAYWRIGHT_CHROMIUM_PATH"] = "/opt/google/chrome"
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/home/nxyme/.cache/ms-playwright"

import sys

sys.path.insert(0, "packages")
import playwright_mcp

playwright_mcp.mcp.run()
