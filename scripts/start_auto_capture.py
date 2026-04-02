#!/usr/bin/env python
"""Simple startup script for Auto-Capture Service without uvicorn reload."""

import sys
import os

# Add the auto-capture src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "packages", "auto-capture"))

# Disable watchfiles reload
os.environ["UVICORN_RELOAD"] = "false"

# Import and run
from src.main import app
import uvicorn

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=5003, reload=False, log_level="info")
