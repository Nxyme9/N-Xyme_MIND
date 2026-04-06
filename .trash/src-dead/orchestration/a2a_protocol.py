"""A2A Protocol - Google A2A protocol implementation."""

import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class A2AMessage:
    """A2A protocol message."""
    
    def __init__(self, message_type: str, content: Dict[str, Any], session_id: Optional[str] = None):
        self.id = str(uuid.uuid4())
        self.type = message_type
        self.content = content
        self.session_id = session_id or str(uuid.uuid4())
        self.timestamp = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'A2AMessage':
        msg = cls(
            message_type=data.get("type", "unknown"),
            content=data.get("content", {}),
            session_id=data.get("session_id"),
        )
        msg.id = data.get("id", msg.id)
        msg.timestamp = data.get("timestamp", msg.timestamp)
        return msg


class A2AProtocol:
    """Google A2A protocol implementation."""
    
    def __init__(self):
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.messages: List[A2AMessage] = []
    
    def create_session(self, session_id: Optional[str] = None) -> str:
        """Create a new session."""
        sid = session_id or str(uuid.uuid4())
        self.sessions[sid] = {
            "id": sid,
            "created_at": time.time(),
            "messages": [],
            "status": "active",
        }
        logger.info(f"✅ Created session: {sid}")
        return sid
    
    def send_message(self, session_id: str, message_type: str, content: Dict[str, Any]) -> A2AMessage:
        """Send a message to a session."""
        session = self.sessions.get(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")
        
        message = A2AMessage(message_type, content, session_id)
        self.messages.append(message)
        session["messages"].append(message.id)
        
        return message
    
    def get_session_messages(self, session_id: str) -> List[A2AMessage]:
        """Get all messages in a session."""
        session = self.sessions.get(session_id)
        if not session:
            return []
        
        return [m for m in self.messages if m.session_id == session_id]
    
    def close_session(self, session_id: str) -> bool:
        """Close a session."""
        session = self.sessions.get(session_id)
        if not session:
            return False
        
        session["status"] = "closed"
        logger.info(f"✅ Closed session: {session_id}")
        return True
    
    def get_status(self) -> Dict[str, Any]:
        """Get protocol status."""
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len([s for s in self.sessions.values() if s["status"] == "active"]),
            "total_messages": len(self.messages),
        }


# Global protocol instance
_protocol = None


def get_a2a_protocol() -> A2AProtocol:
    """Get or create the global A2A protocol instance."""
    global _protocol
    if _protocol is None:
        _protocol = A2AProtocol()
    return _protocol
