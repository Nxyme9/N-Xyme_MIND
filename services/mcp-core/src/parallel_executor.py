#!/usr/bin/env python3
"""Parallel Task Executor — Same-session parallel execution with shared context."""
import asyncio
import threading
import time
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Optional

class ParallelExecutor:
    """Execute tasks in parallel within the same session context."""
    
    def __init__(self, max_workers: int = 10):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.session_contexts: Dict[str, dict] = {}
        self.task_results: Dict[str, dict] = {}
        self.lock = threading.Lock()
    
    def get_session_context(self, session_id: str) -> dict:
        """Get or create session context."""
        with self.lock:
            if session_id not in self.session_contexts:
                self.session_contexts[session_id] = {
                    'session_id': session_id,
                    'agent_name': '',
                    'permissions': {},
                    'memory': {},
                    'cache': {},
                    'started_at': time.time(),
                    'tasks': []
                }
            return self.session_contexts[session_id]
    
    def update_session_context(self, session_id: str, updates: dict):
        """Update session context with new data."""
        with self.lock:
            if session_id in self.session_contexts:
                self.session_contexts[session_id].update(updates)
    
    def parallel_task(self, session_id: str, agent_name: str, prompt: str, 
                     dependencies: List[str] = None, timeout: int = 300) -> str:
        """Submit a parallel task to the executor."""
        task_id = f"task_{session_id}_{int(time.time() * 1000)}"
        
        task_ctx = {
            'task_id': task_id,
            'session_id': session_id,
            'agent_name': agent_name,
            'prompt': prompt,
            'dependencies': dependencies or [],
            'timeout': timeout,
            'status': 'pending',
            'submitted_at': time.time(),
            'result': None,
            'error': None
        }
        
        # Add to session context
        with self.lock:
            if session_id in self.session_contexts:
                self.session_contexts[session_id]['tasks'].append(task_id)
        
        # Submit to executor
        future = self.executor.submit(self._execute_task, task_ctx)
        future.add_done_callback(lambda f: self._task_complete(task_id, f))
        
        return task_id
    
    def _execute_task(self, task_ctx: dict) -> dict:
        """Execute a single task."""
        task_id = task_ctx['task_id']
        session_id = task_ctx['session_id']
        
        try:
            task_ctx['status'] = 'running'
            task_ctx['started_at'] = time.time()
            
            # Wait for dependencies
            if task_ctx['dependencies']:
                self._wait_for_dependencies(task_ctx['dependencies'], task_ctx['timeout'])
            
            # Get session context
            session_ctx = self.get_session_context(session_id)
            
            # Execute agent (this is where the actual agent logic runs)
            result = self._run_agent(task_ctx['agent_name'], task_ctx['prompt'], session_ctx)
            
            task_ctx['status'] = 'completed'
            task_ctx['result'] = result
            task_ctx['completed_at'] = time.time()
            
            return task_ctx
            
        except Exception as e:
            task_ctx['status'] = 'failed'
            task_ctx['error'] = str(e)
            task_ctx['completed_at'] = time.time()
            return task_ctx
    
    def _wait_for_dependencies(self, dependencies: List[str], timeout: int):
        """Wait for dependency tasks to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            all_done = True
            for dep_id in dependencies:
                with self.lock:
                    if dep_id in self.task_results:
                        if self.task_results[dep_id]['status'] != 'completed':
                            all_done = False
                            break
                    else:
                        all_done = False
                        break
            
            if all_done:
                return
            time.sleep(0.1)
        
        raise TimeoutError(f"Dependencies not completed within {timeout}s")
    
    def _run_agent(self, agent_name: str, prompt: str, session_ctx: dict) -> dict:
        """Run an agent with the given prompt and session context."""
        # This is a placeholder - in reality, this would:
        # 1. Load agent config
        # 2. Set up the execution environment
        # 3. Run the agent's prompt
        # 4. Return the result
        
        # For now, simulate execution
        time.sleep(0.1)  # Simulate work
        
        return {
            'agent': agent_name,
            'output': f"Agent {agent_name} executed successfully",
            'session_context': session_ctx
        }
    
    def _task_complete(self, task_id: str, future):
        """Handle task completion."""
        try:
            result = future.result()
            with self.lock:
                self.task_results[task_id] = result
        except Exception as e:
            with self.lock:
                self.task_results[task_id] = {
                    'task_id': task_id,
                    'status': 'failed',
                    'error': str(e),
                    'completed_at': time.time()
                }
    
    def get_task_result(self, task_id: str) -> Optional[dict]:
        """Get the result of a task."""
        with self.lock:
            return self.task_results.get(task_id)
    
    def get_session_tasks(self, session_id: str) -> List[dict]:
        """Get all tasks for a session."""
        with self.lock:
            if session_id in self.session_contexts:
                task_ids = self.session_contexts[session_id]['tasks']
                return [self.task_results.get(tid) for tid in task_ids if tid in self.task_results]
            return []
    
    def wait_for_session(self, session_id: str, timeout: int = 300) -> List[dict]:
        """Wait for all tasks in a session to complete."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            tasks = self.get_session_tasks(session_id)
            if all(t and t['status'] in ['completed', 'failed'] for t in tasks):
                return tasks
            time.sleep(0.1)
        
        raise TimeoutError(f"Session {session_id} did not complete within {timeout}s")
    
    def shutdown(self):
        """Shutdown the executor."""
        self.executor.shutdown(wait=True)

# Global executor instance
parallel_executor = ParallelExecutor(max_workers=10)
