"""Error Recovery System

Provides graceful degradation and recovery paths for:
1. MCP server failures
2. Routing system failures
3. Database connection issues
4. Agent execution failures
5. Context window overflow
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, Callable
from pathlib import Path

logger = logging.getLogger("error-recovery")


class RecoveryState:
    """Tracks recovery state for different components."""
    
    def __init__(self):
        self.component_states: Dict[str, Dict[str, Any]] = {}
    
    def mark_failure(self, component: str, error: str):
        """Mark a component as failed."""
        if component not in self.component_states:
            self.component_states[component] = {
                'failures': 0,
                'last_failure': 0,
                'last_error': '',
                'recovery_attempts': 0,
                'is_healthy': True
            }
        
        state = self.component_states[component]
        state['failures'] += 1
        state['last_failure'] = time.time()
        state['last_error'] = str(error)
        state['is_healthy'] = False
        
        logger.warning(f"Component '{component}' failed: {error} (failure #{state['failures']})")
    
    def mark_recovery(self, component: str):
        """Mark a component as recovered."""
        if component in self.component_states:
            state = self.component_states[component]
            state['recovery_attempts'] += 1
            state['is_healthy'] = True
            logger.info(f"Component '{component}' recovered (attempt #{state['recovery_attempts']})")
    
    def is_healthy(self, component: str) -> bool:
        """Check if a component is healthy."""
        if component not in self.component_states:
            return True
        return self.component_states[component]['is_healthy']
    
    def get_recovery_strategy(self, component: str) -> str:
        """Get recovery strategy for a failed component."""
        if component not in self.component_states:
            return 'none'
        
        state = self.component_states[component]
        failures = state['failures']
        
        if failures == 1:
            return 'retry'
        elif failures == 2:
            return 'fallback'
        elif failures == 3:
            return 'degraded'
        else:
            return 'circuit_open'
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health."""
        healthy = sum(1 for s in self.component_states.values() if s['is_healthy'])
        total = len(self.component_states) if self.component_states else 1
        
        return {
            'overall_health': healthy / total,
            'components': {
                name: {
                    'healthy': state['is_healthy'],
                    'failures': state['failures'],
                    'recovery_attempts': state['recovery_attempts']
                }
                for name, state in self.component_states.items()
            }
        }


class ErrorRecovery:
    """Handles error recovery for the delegation system."""
    
    def __init__(self):
        self.state = RecoveryState()
        self._recovery_handlers: Dict[str, Callable] = {}
    
    def register_recovery_handler(self, component: str, handler: Callable):
        """Register a recovery handler for a component."""
        self._recovery_handlers[component] = handler
    
    async def handle_error(self, component: str, error: Exception, fallback_result: Any = None) -> Any:
        """Handle an error with appropriate recovery strategy."""
        self.state.mark_failure(component, error)
        strategy = self.state.get_recovery_strategy(component)
        
        logger.info(f"Recovery strategy for '{component}': {strategy}")
        
        if strategy == 'retry':
            return await self._retry(component, error, fallback_result)
        elif strategy == 'fallback':
            return await self._fallback(component, error, fallback_result)
        elif strategy == 'degraded':
            return await self._degraded_mode(component, error, fallback_result)
        else:  # circuit_open
            return await self._circuit_open(component, error, fallback_result)
    
    async def _retry(self, component: str, error: Exception, fallback_result: Any) -> Any:
        """Retry the operation once."""
        logger.info(f"Retrying component '{component}'...")
        try:
            if component in self._recovery_handlers:
                result = await self._recovery_handlers[component]()
                self.state.mark_recovery(component)
                return result
        except Exception as retry_error:
            logger.warning(f"Retry failed for '{component}': {retry_error}")
            self.state.mark_failure(component, retry_error)
        
        return fallback_result
    
    async def _fallback(self, component: str, error: Exception, fallback_result: Any) -> Any:
        """Use fallback component."""
        logger.info(f"Using fallback for component '{component}'...")
        
        fallback_map = {
            'mcp_server': 'local_routing',
            'sqlite_store': 'memory_store',
            'predictive_router': 'trigger_router',
            'multi_agent_coordinator': 'single_agent',
        }
        
        fallback_component = fallback_map.get(component)
        if fallback_component and fallback_component in self._recovery_handlers:
            try:
                result = await self._recovery_handlers[fallback_component]()
                self.state.mark_recovery(component)
                return result
            except Exception as fallback_error:
                logger.warning(f"Fallback failed for '{component}': {fallback_error}")
        
        return fallback_result
    
    async def _degraded_mode(self, component: str, error: Exception, fallback_result: Any) -> Any:
        """Enter degraded mode."""
        logger.warning(f"Component '{component}' in degraded mode")
        return fallback_result
    
    async def _circuit_open(self, component: str, error: Exception, fallback_result: Any) -> Any:
        """Circuit breaker open - component unavailable."""
        logger.error(f"Circuit breaker open for component '{component}'")
        return fallback_result
    
    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health."""
        return self.state.get_system_health()


# Global recovery instance
_recovery = None

def get_error_recovery() -> ErrorRecovery:
    """Get or create the global error recovery system."""
    global _recovery
    if _recovery is None:
        _recovery = ErrorRecovery()
    return _recovery
