#!/usr/bin/env python3
"""
The Catalyst - CLI Entry Point

Command-line interface for The Catalyst orchestration engine.
"""

import asyncio
import sys
from pathlib import Path

# Add the package to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "core-infrastructure"))

from src.catalyst import main

if __name__ == "__main__":
    asyncio.run(main())
