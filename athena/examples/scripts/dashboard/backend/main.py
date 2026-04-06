#!/usr/bin/env python3
"""
Dashboard Backend - FastAPI server with WebSocket support for real-time session updates
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configuration
PROJECT_ROOT = Path("/home/nxyme/N-Xyme_CODE/N-Xyme_MIND")
SESSION_STATE_FILE = PROJECT_ROOT / ".sisyphus" / "session-state.json"
MIND_STATE_FILE = PROJECT_ROOT / ".context" / "mind-state.json"


# ============= Data Models =============

class SessionInfo(BaseModel):
    """Session information model"""
    session_id: str
    last_agent: str
    current_task: str
    last_action: str
    session_started: str
    last_updated: str
    pending_changes: List[str] = []
    completed_changes: List[str] = []
    memory_stats: Dict[str, Any] = {}


class MindState(BaseModel):
    """Mind state model"""
    project: str
    phase: str
    active_tasks: List[str] = []
    context: Dict[str, Any] = {}
    last_updated: str
    session_start: str


class StatusResponse(BaseModel):
    """Status response model"""
    status: str
    timestamp: str
    session: Optional[SessionInfo] = None
    mind: Optional[MindState] = None
    websocket_clients: int


class KillResponse(BaseModel):
    """Response for kill session"""
    success: bool
    message: str
    timestamp: str


# ============= WebSocket Manager =============

class ConnectionManager:
    """Manages WebSocket connections for broadcasting"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Broadcast message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for conn in disconnected:
            self.disconnect(conn)


# ============= Data Reading Functions =============

def read_json_file(file_path: Path) -> Optional[Dict[str, Any]]:
    """Read and parse a JSON file, return None if not found or invalid"""
    try:
        if file_path.exists():
            with open(file_path, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading {file_path}: {e}")
    return None


def get_session_state() -> Optional[SessionInfo]:
    """Read session state from file"""
    data = read_json_file(SESSION_STATE_FILE)
    if data:
        return SessionInfo(
            session_id="current",
            last_agent=data.get("last_agent", "unknown"),
            current_task=data.get("current_task", ""),
            last_action=data.get("last_action", ""),
            session_started=data.get("session_started", ""),
            last_updated=data.get("last_updated", ""),
            pending_changes=data.get("pending_changes", []),
            completed_changes=data.get("completed_changes", []),
            memory_stats=data.get("memory_stats", {})
        )
    return None


def get_mind_state() -> Optional[MindState]:
    """Read mind state from file"""
    data = read_json_file(MIND_STATE_FILE)
    if data:
        return MindState(
            project=data.get("project", ""),
            phase=data.get("phase", ""),
            active_tasks=data.get("active_tasks", []),
            context=data.get("context", {}),
            last_updated=data.get("last_updated", ""),
            session_start=data.get("session_start", "")
        )
    return None


def get_all_sessions() -> List[SessionInfo]:
    """Get list of all sessions"""
    session = get_session_state()
    if session:
        return [session]
    return []


def get_session_by_id(session_id: str) -> Optional[SessionInfo]:
    """Get a specific session by ID"""
    if session_id == "current":
        return get_session_state()
    # For now, only "current" session is supported
    return None


# ============= API Routes =============

app = FastAPI(
    title="Athena Dashboard API",
    description="Real-time session monitoring API with WebSocket support",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter()
manager = ConnectionManager()


@router.get("/sessions", response_model=List[SessionInfo])
async def list_sessions():
    """Get list of all sessions"""
    return get_all_sessions()


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """Get a specific session by ID"""
    session = get_session_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/sessions/{session_id}/kill", response_model=KillResponse)
async def kill_session(session_id: str):
    """Kill a specific session"""
    # For now, this is a placeholder - actual implementation would depend on
    # what "killing" a session means in this context
    if session_id != "current":
        raise HTTPException(status_code=404, detail="Session not found")
    
    return KillResponse(
        success=True,
        message=f"Session {session_id} termination requested",
        timestamp=datetime.utcnow().isoformat()
    )


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """Get current system status"""
    session = get_session_state()
    mind = get_mind_state()
    
    return StatusResponse(
        status="operational",
        timestamp=datetime.utcnow().isoformat(),
        session=session,
        mind=mind,
        websocket_clients=len(manager.active_connections)
    )


# ============= WebSocket Endpoint =============

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time session updates"""
    await manager.connect(websocket)
    
    # Send initial state
    session = get_session_state()
    mind = get_mind_state()
    await websocket.send_json({
        "type": "init",
        "data": {
            "session": session.model_dump() if session else None,
            "mind": mind.model_dump() if mind else None,
            "timestamp": datetime.utcnow().isoformat()
        }
    })
    
    # Notify about new connection
    await manager.broadcast({
        "type": "client_connected",
        "data": {
            "client_count": len(manager.active_connections),
            "timestamp": datetime.utcnow().isoformat()
        }
    })
    
    try:
        # Keep connection alive and listen for messages
        while True:
            # Wait for any message from client
            data = await websocket.receive_text()
            
            # Handle client messages
            try:
                message = json.loads(data)
                msg_type = message.get("type", "")
                
                if msg_type == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.utcnow().isoformat()})
                elif msg_type == "request_refresh":
                    # Send current state
                    session = get_session_state()
                    mind = get_mind_state()
                    await websocket.send_json({
                        "type": "refresh",
                        "data": {
                            "session": session.model_dump() if session else None,
                            "mind": mind.model_dump() if mind else None,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    })
            except json.JSONDecodeError:
                pass
                
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)
        # Notify about disconnect
        await manager.broadcast({
            "type": "client_disconnected",
            "data": {
                "client_count": len(manager.active_connections),
                "timestamp": datetime.utcnow().isoformat()
            }
        })


# ============= Background Task for State Changes =============

async def check_state_changes():
    """Background task to check for state changes and broadcast updates"""
    last_session_update = None
    last_mind_update = None
    
    while True:
        try:
            # Check session state
            session_data = read_json_file(SESSION_STATE_FILE)
            if session_data:
                current_update = session_data.get("last_updated")
                if current_update != last_session_update and last_session_update is not None:
                    # State changed, broadcast
                    session = get_session_state()
                    await manager.broadcast({
                        "type": "session_updated",
                        "data": {
                            "session": session.model_dump() if session else None,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    })
                last_session_update = current_update
            
            # Check mind state
            mind_data = read_json_file(MIND_STATE_FILE)
            if mind_data:
                current_mind_update = mind_data.get("last_updated")
                if current_mind_update != last_mind_update and last_mind_update is not None:
                    # State changed, broadcast
                    mind = get_mind_state()
                    await manager.broadcast({
                        "type": "mind_updated",
                        "data": {
                            "mind": mind.model_dump() if mind else None,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    })
                last_mind_update = current_mind_update
                
        except Exception as e:
            print(f"Error in state check: {e}")
        
        await asyncio.sleep(2)  # Check every 2 seconds


@app.on_event("startup")
async def startup_event():
    """Start background task on app startup"""
    asyncio.create_task(check_state_changes())


# Include router
app.include_router(router)


# ============= Main =============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)