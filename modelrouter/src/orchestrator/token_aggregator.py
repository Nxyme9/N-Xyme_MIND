#!/usr/bin/env python3
"""
Token Aggregation Engine - Federated Context Tunneling
Aggregates outputs from multiple OpenCode instances into unified context
"""
import asyncio
import json
import queue
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from enum import Enum
import hashlib

class MessageType(Enum):
    CHUNK = "chunk"           # Token chunk
    CONTEXT = "context"       # Context update
    COMPLETE = "complete"     # Task complete
    ERROR = "error"           # Error occurred
    HEARTBEAT = "heartbeat"   # Keepalive
    SYNC = "sync"             # State sync

@dataclass
class TokenChunk:
    """A chunk of tokens from a source"""
    chunk_id: str
    source_id: str
    content: str
    token_count: int
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 0  # Higher = more important
    metadata: Dict = field(default_factory=dict)

@dataclass
class AggregationSession:
    """A session for aggregating tokens from multiple sources"""
    session_id: str
    sources: List[str] = field(default_factory=list)
    chunks: List[TokenChunk] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    status: str = "active"  # active, aggregating, complete, error
    total_tokens: int = 0
    
class TokenTunnel:
    """
    Token Tunnel - Streams tokens from source to aggregator
    """
    def __init__(self, source_id: str, endpoint: str, tunnel_type: str = "http"):
        self.source_id = source_id
        self.endpoint = endpoint
        self.tunnel_type = tunnel_type
        self.connected = False
        self.last_heartbeat = datetime.now()
        self.bytes_sent = 0
        self.chunks_sent = 0
        
    def send_chunk(self, chunk: TokenChunk) -> bool:
        """Send a token chunk through the tunnel"""
        try:
            # In real implementation, this would send via HTTP/WebSocket
            # For now, we simulate the tunnel
            self.bytes_sent += len(chunk.content)
            self.chunks_sent += 1
            return True
        except Exception as e:
            print(f"❌ Tunnel send error: {e}")
            return False
            
    def send_heartbeat(self) -> bool:
        """Send heartbeat to keep tunnel alive"""
        chunk = TokenChunk(
            chunk_id=str(uuid.uuid4()),
            source_id=self.source_id,
            content="",
            token_count=0,
            metadata={"type": "heartbeat"}
        )
        return self.send_chunk(chunk)


class TokenAggregator:
    """
    Federated Token Aggregator
    Combines tokens from multiple OpenCode instances into unified context
    """
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or str(uuid.uuid4())[:8]
        self.sources: Dict[str, TokenTunnel] = {}
        self.aggregation_queue = queue.Queue()
        self.output_buffer = ""
        self.chunks: List[TokenChunk] = []
        
        # Callbacks
        self.on_chunk: Optional[Callable] = None
        self.on_complete: Optional[Callable] = None
        self.on_error: Optional[Callable] = None
        
        # Statistics
        self.stats = {
            "total_chunks": 0,
            "total_tokens": 0,
            "sources_active": 0,
            "bytes_received": 0
        }
        
        # Background aggregation thread
        self._running = False
        self._aggregator_thread = None
        
    def add_source(self, source_id: str, endpoint: str) -> TokenTunnel:
        """Add a new source tunnel"""
        tunnel = TokenTunnel(source_id, endpoint)
        self.sources[source_id] = tunnel
        self.stats["sources_active"] = len([s for s in self.sources.values() if s.connected])
        print(f"➕ Added source: {source_id} → {endpoint}")
        return tunnel
    
    def remove_source(self, source_id: str):
        """Remove a source tunnel"""
        if source_id in self.sources:
            del self.sources[source_id]
            print(f"➖ Removed source: {source_id}")
    
    def receive_chunk(self, chunk: TokenChunk):
        """Receive a token chunk from a source"""
        self.aggregation_queue.put(chunk)
        self.stats["total_chunks"] += 1
        self.stats["total_tokens"] += chunk.token_count
        self.stats["bytes_received"] += len(chunk.content)
        
    def start_aggregation(self):
        """Start the aggregation processor"""
        self._running = True
        self._aggregator_thread = threading.Thread(target=self._aggregation_loop, daemon=True)
        self._aggregator_thread.start()
        print(f"🚀 Token aggregation started for session: {self.session_id}")
        
    def stop_aggregation(self):
        """Stop the aggregation processor"""
        self._running = False
        if self._aggregator_thread:
            self._aggregator_thread.join(timeout=5)
        print(f"🛑 Token aggregation stopped")
    
    def _aggregation_loop(self):
        """Main aggregation loop"""
        while self._running:
            try:
                chunk = self.aggregation_queue.get(timeout=1)
                self._process_chunk(chunk)
            except queue.Empty:
                continue
            except Exception as e:
                print(f"❌ Aggregation error: {e}")
                if self.on_error:
                    self.on_error(e)
    
    def _process_chunk(self, chunk: TokenChunk):
        """Process a received chunk"""
        # Add to output buffer
        self.output_buffer += chunk.content
        self.chunks.append(chunk)
        
        # Trigger callback
        if self.on_chunk:
            self.on_chunk(chunk)
            
        # Check if chunk indicates completion
        if chunk.metadata.get("type") == "complete":
            if self.on_complete:
                self.on_complete({
                    "session_id": self.session_id,
                    "total_tokens": self.stats["total_tokens"],
                    "chunks": len(self.chunks)
                })
    
    def get_context(self, max_tokens: int = None) -> str:
        """Get aggregated context, optionally limited by token count"""
        if max_tokens is None:
            return self.output_buffer
            
        # Simple token estimation (roughly 1 token = 4 chars)
        max_chars = max_tokens * 4
        return self.output_buffer[-max_chars:] if len(self.output_buffer) > max_chars else self.output_buffer
    
    def get_status(self) -> Dict:
        """Get aggregator status"""
        return {
            "session_id": self.session_id,
            "sources": len(self.sources),
            "sources_active": self.stats["sources_active"],
            "chunks_received": self.stats["total_chunks"],
            "total_tokens": self.stats["total_tokens"],
            "bytes_received": self.stats["bytes_received"],
            "buffer_size": len(self.output_buffer)
        }


class FederatedContextBuilder:
    """
    Builds unified context from multiple token sources
    Uses priority-based merging and deduplication
    """
    
    def __init__(self):
        self.sources: Dict[str, Dict] = {}
        self.priority_weights: Dict[str, float] = {}
        
    def register_source(self, source_id: str, priority: float = 1.0, metadata: Dict = None):
        """Register a source with priority weight"""
        self.sources[source_id] = {
            "priority": priority,
            "metadata": metadata or {},
            "content": [],
            "registered_at": datetime.now()
        }
        self.priority_weights[source_id] = priority
        
    def add_content(self, source_id: str, content: str, metadata: Dict = None):
        """Add content from a source"""
        if source_id not in self.sources:
            self.register_source(source_id)
            
        self.sources[source_id]["content"].append({
            "text": content,
            "timestamp": datetime.now(),
            "metadata": metadata or {}
        })
    
    def build_unified_context(self, max_tokens: int = 128000) -> str:
        """
        Build unified context from all sources
        Prioritizes by source priority, then chronological
        """
        # Sort sources by priority
        sorted_sources = sorted(
            self.sources.items(),
            key=lambda x: x[1]["priority"],
            reverse=True
        )
        
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Approximate
        
        for source_id, source_data in sorted_sources:
            for item in source_data["content"]:
                text = item["text"]
                if total_chars + len(text) > max_chars:
                    # Truncate if needed
                    remaining = max_chars - total_chars
                    if remaining > 100:  # Only add if meaningful
                        context_parts.append(text[:remaining])
                    break
                context_parts.append(text)
                total_chars += len(text)
                
            if total_chars >= max_chars:
                break
                
        return "\n\n---\n\n".join(context_parts)
    
    def deduplicate(self) -> int:
        """Remove duplicate content across sources"""
        seen_hashes = set()
        removed = 0
        
        for source_id in self.sources:
            unique_content = []
            for item in self.sources[source_id]["content"]:
                content_hash = hashlib.md5(item["text"].encode()).hexdigest()
                if content_hash not in seen_hashes:
                    seen_hashes.add(content_hash)
                    unique_content.append(item)
                else:
                    removed += 1
            self.sources[source_id]["content"] = unique_content
            
        return removed


# Singleton aggregator instance
_aggregator = None

def get_aggregator(session_id: str = None) -> TokenAggregator:
    global _aggregator
    if _aggregator is None:
        _aggregator = TokenAggregator(session_id)
    return _aggregator


# HTTP-based token receiver (for receiving from remote instances)
class TokenReceiver:
    """
    HTTP server that receives tokens from remote OpenCode instances
    """
    def __init__(self, port: int = 8765):
        self.port = port
        self.aggregator: Optional[TokenAggregator] = None
        self._running = False
        
    def set_aggregator(self, aggregator: TokenAggregator):
        self.aggregator = aggregator
        
    async def handle_request(self, handler):
        """Handle incoming token request"""
        # Simplified - would use aiohttp in production
        pass
        
    def start(self):
        """Start the receiver"""
        self._running = True
        print(f"📥 Token receiver started on port {self.port}")
        
    def stop(self):
        """Stop the receiver"""
        self._running = False


if __name__ == "__main__":
    print("🧪 Testing Token Aggregator...")
    
    agg = get_aggregator("test-session")
    
    # Add sources
    agg.add_source("instance-1", "http://localhost:8081")
    agg.add_source("instance-2", "http://localhost:8082")
    agg.add_source("instance-3", "http://localhost:8083")
    
    # Simulate receiving chunks
    agg.receive_chunk(TokenChunk(
        chunk_id="1",
        source_id="instance-1", 
        content="This is the first chunk from instance 1. ",
        token_count=10
    ))
    
    agg.receive_chunk(TokenChunk(
        chunk_id="2",
        source_id="instance-2",
        content="This is a chunk from instance 2 with different content. ",
        token_count=12
    ))
    
    agg.start_aggregation()
    time.sleep(1)
    
    print(f"\n📊 Status: {json.dumps(agg.get_status(), indent=2, default=str)}")
    print(f"\n📝 Context: {agg.get_context()[:200]}...")
    
    agg.stop_aggregation()
