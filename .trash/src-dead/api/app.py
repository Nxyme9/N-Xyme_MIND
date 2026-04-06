#!/usr/bin/env python3
"""Catalyst API - Main FastAPI application."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))  # Add project root

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers (brain is required, others optional)
from api.brain import router as brain_router

try:
    from api.system import router as system_router

    _has_system = True
except ImportError:
    _has_system = False

try:
    from api.audio import router as audio_router

    _has_audio = True
except ImportError:
    _has_audio = False

# Create app
app = FastAPI(
    title="N-Xyme Catalyst API",
    description="Cognitive API for brain pipeline with tool execution",
    version="1.0.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(brain_router)

if _has_system:
    app.include_router(system_router)

if _has_audio:
    app.include_router(audio_router)


# Health check
@app.get("/health")
async def health():
    return {"status": "healthy", "service": "catalyst-api"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8100)
