"""Agent Communication Protocol

Provides high-level API for inter-agent communication using the message queue.
Supports direct messaging, broadcast, and request/response patterns.
"""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Callable
from .message_queue import get_message_queue, MessageQueue

logger = logging.getLogger("agent-communication")


class AgentCommunication:
    """High-level API for agent-to-agent communication."""
    
    def __init__(self, message_queue: MessageQueue = None):
        self.mq = message_queue or get_message_queue()
        self._handlers: Dict[str, Callable] = {}
        self._running = False
    
    def register_handler(self, agent_name: str, handler: Callable):
        """Register a message handler for an agent."""
        self._handlers[agent_name] = handler
        logger.info(f"Registered handler for agent: {agent_name}")
    
    async def send_direct(self, from_agent: str, to_agent: str, subject: str, 
                         content: str, priority: int = 0, 
                         metadata: Dict[str, Any] = None) -> str:
        """Send a direct message to an agent."""
        return self.mq.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            subject=subject,
            content=content,
            message_type="direct",
            priority=priority,
            metadata=metadata
        )
    
    async def send_request(self, from_agent: str, to_agent: str, subject: str,
                          content: str, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """Send a request and wait for response."""
        # Send request
        request_id = self.mq.send_message(
            from_agent=from_agent,
            to_agent=to_agent,
            subject=subject,
            content=content,
            message_type="request",
            priority=1
        )
        
        # Wait for response
        start_time = time.time()
        while time.time() - start_time < timeout:
            responses = self.mq.get_messages(to_agent=from_agent, status="pending", limit=10)
            for response in responses:
                if response.get('response_to') == request_id:
                    self.mq.mark_read(response['id'])
                    return response
            
            await asyncio.sleep(0.1)  # Poll every 100ms
        
        logger.warning(f"Request timeout: {request_id}")
        return None
    
    async def send_response(self, from_agent: str, request_id: str, 
                           content: str, subject: str = None) -> str:
        """Send a response to a request."""
        return self.mq.send_response(
            from_agent=from_agent,
            response_to=request_id,
            content=content,
            subject=subject
        )
    
    async def broadcast(self, from_agent: str, subject: str, content: str,
                       exclude_agents: List[str] = None, priority: int = 0) -> List[str]:
        """Broadcast a message to all agents."""
        exclude = exclude_agents or []
        message_ids = []
        
        # Get all registered agents
        all_agents = set(self._handlers.keys())
        target_agents = all_agents - set(exclude)
        
        for agent in target_agents:
            msg_id = self.mq.send_message(
                from_agent=from_agent,
                to_agent=agent,
                subject=subject,
                content=content,
                message_type="broadcast",
                priority=priority
            )
            message_ids.append(msg_id)
        
        logger.info(f"Broadcast from {from_agent} to {len(target_agents)} agents")
        return message_ids
    
    async def process_messages(self, agent_name: str) -> List[Dict[str, Any]]:
        """Process pending messages for an agent."""
        if agent_name not in self._handlers:
            logger.warning(f"No handler registered for agent: {agent_name}")
            return []
        
        handler = self._handlers[agent_name]
        messages = self.mq.get_messages(to_agent=agent_name, status="pending", limit=50)
        processed = []
        
        for message in messages:
            try:
                # Call handler with message
                result = await handler(message)
                
                # Mark as processed
                self.mq.mark_processed(message['id'])
                processed.append({
                    'message_id': message['id'],
                    'status': 'processed',
                    'result': result
                })
                
                # If it was a request, send response
                if message.get('type') == 'request' and result:
                    await self.send_response(
                        from_agent=agent_name,
                        request_id=message['id'],
                        content=str(result),
                        subject=f"Re: {message.get('subject', '')}"
                    )
                
            except Exception as e:
                logger.error(f"Error processing message {message['id']}: {e}")
                processed.append({
                    'message_id': message['id'],
                    'status': 'error',
                    'error': str(e)
                })
        
        return processed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get communication statistics."""
        mq_stats = self.mq.get_stats()
        return {
            'message_queue': mq_stats,
            'registered_agents': len(self._handlers),
            'agents': list(self._handlers.keys())
        }


# Global communication instance
_communication = None

def get_agent_communication() -> AgentCommunication:
    """Get or create the global agent communication system."""
    global _communication
    if _communication is None:
        _communication = AgentCommunication()
    return _communication
