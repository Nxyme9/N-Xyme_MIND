import asyncio
import json
from typing import Dict, Any, List, Callable, Optional
from dataclasses import dataclass
import aiohttp

# Import centralized Graphiti configuration
import os

try:
    from jarvis.config.graphiti_config import GRAPHITI_URL
except ImportError:
    GRAPHITI_URL = os.getenv("GRAPHITI_URL", "http://localhost:8001")


@dataclass
class Message:
    """Message for agent communication."""

    sender: str
    receiver: str
    content: Dict[str, Any]
    message_id: str
    timestamp: float


class Communicator:
    """Handle agent communication via direct messaging, blackboard, and pub/sub."""

    def __init__(self, blackboard_url: str = GRAPHITI_URL):
        self.blackboard_url = blackboard_url
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.message_log = []

    async def send_direct(self, sender: str, receiver: str, content: Dict[str, Any]) -> bool:
        """Send a direct message to another agent."""
        import uuid
        import time

        message = Message(
            sender=sender,
            receiver=receiver,
            content=content,
            message_id=str(uuid.uuid4()),
            timestamp=time.time(),
        )

        # Store in message log
        self.message_log.append(message)

        # In a real implementation, this would send via HTTP or message queue
        print(f"Direct message from {sender} to {receiver}: {content}")
        return True

    async def post_to_blackboard(self, agent: str, data: Dict[str, Any]) -> bool:
        """Post data to the Graphiti blackboard."""
        import uuid
        import time

        # Format as episode for Graphiti
        episode = {
            "source": "agent_framework",
            "source_description": f"Agent {agent} posting data",
            "content": json.dumps(data),
            "timestamp": time.time(),
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(
                    f"{self.blackboard_url}/v1/episodes", json=episode, timeout=5
                ) as resp:
                    if resp.status == 200:
                        return True
            except Exception as e:
                print(f"Error posting to blackboard: {e}")

        return False

    async def subscribe_to_event(self, event_type: str, callback: Callable):
        """Subscribe to an event type."""
        if event_type not in self.subscriptions:
            self.subscriptions[event_type] = []
        self.subscriptions[event_type].append(callback)

    async def publish_event(self, event_type: str, data: Dict[str, Any]):
        """Publish an event to all subscribers."""
        if event_type in self.subscriptions:
            for callback in self.subscriptions[event_type]:
                await callback(data)

    async def broadcast(self, sender: str, content: Dict[str, Any], exclude: List[str] = None):
        """Broadcast a message to all agents."""
        if exclude is None:
            exclude = []

        # In a real implementation, we'd have a registry of agents
        # For now, we'll just log it
        print(f"Broadcast from {sender}: {content}")

    def get_message_log(self) -> List[Message]:
        """Get all messages logged."""
        return self.message_log

    def clear_log(self):
        """Clear the message log."""
        self.message_log.clear()

    def __repr__(self):
        return f"<Communicator subscriptions={len(self.subscriptions)}>"
