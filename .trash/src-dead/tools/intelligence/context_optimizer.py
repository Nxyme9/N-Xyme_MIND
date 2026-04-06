"""Context Window Optimizer

Optimizes context window usage for cloud models by:
1. Compressing routing decisions into compact format
2. Prioritizing recent and relevant context
3. Truncating old/irrelevant context when approaching limits
4. Maintaining essential system information
"""

import json
import time
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger("context-optimizer")


class ContextOptimizer:
    """Optimizes context window usage for cloud models."""
    
    def __init__(self, max_tokens: int = 8000):
        self.max_tokens = max_tokens
        self._context_history: List[Dict[str, Any]] = []
        self._max_history = 100
    
    def add_context(self, context_type: str, content: str, priority: int = 1, ttl: float = 3600):
        """Add context to history with priority and TTL."""
        self._context_history.append({
            'type': context_type,
            'content': content,
            'priority': priority,
            'timestamp': time.time(),
            'ttl': ttl,
            'token_estimate': len(content) // 4  # Rough estimate
        })
        
        # Trim old history
        if len(self._context_history) > self._max_history:
            self._context_history = self._context_history[-self._max_history:]
    
    def get_optimized_context(self) -> str:
        """Get optimized context within token limits."""
        # Remove expired context
        now = time.time()
        active_context = [
            ctx for ctx in self._context_history
            if now - ctx['timestamp'] < ctx['ttl']
        ]
        
        # Sort by priority (higher first) and recency
        active_context.sort(
            key=lambda x: (x['priority'], x['timestamp']),
            reverse=True
        )
        
        # Build context within token limit
        total_tokens = 0
        optimized_parts = []
        
        for ctx in active_context:
            if total_tokens + ctx['token_estimate'] <= self.max_tokens:
                optimized_parts.append(ctx['content'])
                total_tokens += ctx['token_estimate']
            else:
                # Truncate content to fit
                remaining_tokens = self.max_tokens - total_tokens
                if remaining_tokens > 100:  # Minimum useful content
                    truncated = ctx['content'][:remaining_tokens * 4]
                    optimized_parts.append(truncated + "... [truncated]")
                    total_tokens += remaining_tokens
                break
        
        return "\n\n".join(optimized_parts)
    
    def get_context_stats(self) -> Dict[str, Any]:
        """Get context window statistics."""
        now = time.time()
        active = [ctx for ctx in self._context_history if now - ctx['timestamp'] < ctx['ttl']]
        total_tokens = sum(ctx['token_estimate'] for ctx in active)
        
        return {
            'total_context': len(self._context_history),
            'active_context': len(active),
            'estimated_tokens': total_tokens,
            'max_tokens': self.max_tokens,
            'utilization': total_tokens / self.max_tokens if self.max_tokens > 0 else 0,
            'oldest_active': min((ctx['timestamp'] for ctx in active), default=0),
            'newest_active': max((ctx['timestamp'] for ctx in active), default=0)
        }
    
    def clear_expired(self):
        """Clear expired context."""
        now = time.time()
        before = len(self._context_history)
        self._context_history = [
            ctx for ctx in self._context_history
            if now - ctx['timestamp'] < ctx['ttl']
        ]
        cleared = before - len(self._context_history)
        if cleared > 0:
            logger.info(f"Cleared {cleared} expired context entries")
    
    def add_routing_decision(self, task_description: str, level: int, agent: str, strategy: str):
        """Add routing decision to context."""
        content = f"Task: '{task_description[:50]}...' → L{level} {agent} ({strategy})"
        self.add_context('routing', content, priority=2, ttl=1800)  # 30 min TTL
    
    def add_outcome(self, task_id: str, success: bool, latency_ms: float):
        """Add outcome to context."""
        content = f"Outcome: {task_id} → {'success' if success else 'failed'} ({latency_ms:.0f}ms)"
        self.add_context('outcome', content, priority=1, ttl=3600)  # 1 hour TTL
    
    def add_system_info(self, info: str):
        """Add system information to context."""
        self.add_context('system', info, priority=3, ttl=7200)  # 2 hour TTL


# Global optimizer instance
_optimizer = None

def get_context_optimizer() -> ContextOptimizer:
    """Get or create the global context optimizer."""
    global _optimizer
    if _optimizer is None:
        _optimizer = ContextOptimizer()
    return _optimizer
