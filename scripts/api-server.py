#!/usr/bin/env python3
"""Launch Catalyst API Server"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from api.app import app
import uvicorn

if __name__ == "__main__":
    print("Starting Catalyst API on http://localhost:8100")
    print("Docs: http://localhost:8100/docs")
    uvicorn.run(app, host="0.0.0.0", port=8100)
