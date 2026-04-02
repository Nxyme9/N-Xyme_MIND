#!/usr/bin/env python3
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from tui.app import CatalystDashboard

if __name__ == "__main__":
    print("Starting Catalyst Dashboard...")
    print("Make sure API is running: python scripts/api-server.py")
    CatalystDashboard().run()
