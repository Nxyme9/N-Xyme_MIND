"""Real-Time Learning Updates

Updates agent weights immediately after each task completion.
Provides instant feedback loop for routing optimization.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, field

logger = logging.getLogger("realtime-learner")


@dataclass
class LearningEvent:
    """A learning event from task execution."""
    task_id: str
    task_description: str
    agent: str
    level: int
    success: bool
    latency_ms: float
    tokens_used: int
    timestamp: float = field(default_factory=time.time)
    error: Optional[str] = None


class RealTimeLearner:
    """Updates routing weights in real-time after each task."""
    
    def __init__(self, store=None):
        self._store = store
        self._event_handlers: list = []
        self._recent_events: list = []
        self._max_recent = 100
    
    def set_store(self, store):
        """Set the SQLite store for persistence."""
        self._store = store
    
    def add_event_handler(self, handler: Callable):
        """Add a handler for learning events."""
        self._event_handlers.append(handler)
    
    async def record_event(self, event: LearningEvent):
        """Record a learning event and update weights."""
        # Store event
        self._recent_events.append(event)
        if len(self._recent_events) > self._max_recent:
            self._recent_events = self._recent_events[-self._max_recent:]
        
        # Update SQLite store
        if self._store:
            self._store.add_outcome(
                task_id=event.task_id,
                task_description=event.task_description,
                level=event.level,
                agent=event.agent,
                success=event.success,
                latency_ms=event.latency_ms,
                tokens_used=event.tokens_used
            )
            
            # Update agent weights immediately
            self._store.update_agent_weight(
                agent=event.agent,
                success=event.success,
                latency_ms=event.latency_ms,
                level=event.level
            )
        
        # Notify handlers
        for handler in self._event_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.warning(f"Event handler failed: {e}")
        
        logger.info(f"Learning event: {event.agent} {'succeeded' if event.success else 'failed'} on L{event.level} task ({event.latency_ms:.0f}ms)")
    
    def get_recent_events(self, limit: int = 10) -> list:
        """Get recent learning events."""
        return self._recent_events[-limit:]
    
    def get_agent_trend(self, agent: str, window: int = 10) -> Dict[str, Any]:
        """Get recent performance trend for an agent."""
        events = [e for e in self._recent_events if e.agent == agent][-window:]
        if not events:
            return {'agent': agent, 'trend': 'no_data', 'recent_success_rate': 0, 'recent_count': 0}
        
        success_rate = sum(1 for e in events if e.success) / len(events)
        avg_latency = sum(e.latency_ms for e in events) / len(events)
        
        # Determine trend
        if len(events) >= 4:
            first_half = sum(1 for e in events[:len(events)//2] if e.success) / (len(events)//2)
            second_half = sum(1 for e in events[len(events)//2:] if e.success) / (len(events) - len(events)//2)
            
            if second_half > first_half + 0.1:
                trend = 'improving'
            elif second_half < first_half - 0.1:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'
        
        return {
            'agent': agent,
            'trend': trend,
            'recent_success_rate': success_rate,
            'recent_avg_latency': avg_latency,
            'recent_count': len(events)
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics."""
        if not self._recent_events:
            return {'status': 'no_data', 'recent_success_rate': 0, 'total_events': 0}
        
        total = len(self._recent_events)
        success = sum(1 for e in self._recent_events if e.success)
        avg_latency = sum(e.latency_ms for e in self._recent_events) / total
        
        # Check for anomalies
        recent_failures = sum(1 for e in self._recent_events[-5:] if not e.success)
        anomaly = recent_failures >= 3
        
        return {
            'status': 'anomaly_detected' if anomaly else 'healthy',
            'recent_success_rate': success / total,
            'recent_avg_latency': avg_latency,
            'total_events': total,
            'anomaly': anomaly,
            'recent_failures': recent_failures
        }


# Global learner instance
_learner = None

def get_learner() -> RealTimeLearner:
    """Get or create the global learner."""
    global _learner
    if _learner is None:
        _learner = RealTimeLearner()
    return _learner
