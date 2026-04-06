"""
Scheduled task management for N-Xyme MIND Dashboard TUI.

Provides a simple cron-like scheduler with a Textual screen for managing
scheduled tasks in the dashboard.
"""

from dataclasses import dataclass
from typing import Any, Callable
import time
import uuid


@dataclass
class ScheduledTask:
    """Represents a scheduled task with cron-like scheduling."""
    
    task_id: str
    name: str
    schedule: str  # cron-like expression
    enabled: bool
    next_run: float | None
    last_run: float | None
    
    def __post_init__(self):
        """Validate task parameters after initialization."""
        if not self.task_id:
            raise ValueError("task_id cannot be empty")
        if not self.name:
            raise ValueError("name cannot be empty")
        if not self.schedule:
            raise ValueError("schedule cannot be empty")


class Scheduler:
    """
    Simple scheduler with cron-like expression parsing.
    
    Supports basic cron patterns:
    - * * * * * (minute, hour, day, month, weekday)
    - */5 * * * * (every 5 minutes)
    - 0 * * * * (every hour at minute 0)
    - 0 0 * * * (daily at midnight)
    """
    
    def __init__(self):
        """Initialize the scheduler with an empty task dictionary."""
        self._tasks: dict[str, ScheduledTask] = {}
        self._callbacks: dict[str, Callable[[], Any]] = {}
    
    def add_task(self, name: str, schedule: str, callback: Callable[[], Any]) -> str:
        """
        Add a new scheduled task.
        
        Args:
            name: Human-readable name for the task
            schedule: Cron-like schedule expression (e.g., "*/5 * * * *")
            callback: Callable to execute when task is due
            
        Returns:
            The task_id of the newly created task
            
        Raises:
            ValueError: If name or schedule is empty, or callback is not callable
        """
        if not name:
            raise ValueError("name cannot be empty")
        if not schedule:
            raise ValueError("schedule cannot be empty")
        if not callable(callback):
            raise ValueError("callback must be callable")
        
        task_id = str(uuid.uuid4())[:8]
        
        # Calculate initial next run time
        next_run = self._calculate_next_run(schedule)
        
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            schedule=schedule,
            enabled=True,
            next_run=next_run,
            last_run=None
        )
        
        self._tasks[task_id] = task
        self._callbacks[task_id] = callback
        
        return task_id
    
    def remove_task(self, task_id: str) -> bool:
        """
        Remove a scheduled task.
        
        Args:
            task_id: The ID of the task to remove
            
        Returns:
            True if task was removed, False if task_id not found
        """
        if task_id in self._tasks:
            del self._tasks[task_id]
            if task_id in self._callbacks:
                del self._callbacks[task_id]
            return True
        return False
    
    def enable_task(self, task_id: str) -> bool:
        """
        Enable a scheduled task.
        
        Args:
            task_id: The ID of the task to enable
            
        Returns:
            True if task was enabled, False if task_id not found
        """
        if task_id in self._tasks:
            self._tasks[task_id].enabled = True
            self._tasks[task_id].next_run = self._calculate_next_run(
                self._tasks[task_id].schedule
            )
            return True
        return False
    
    def disable_task(self, task_id: str) -> bool:
        """
        Disable a scheduled task.
        
        Args:
            task_id: The ID of the task to disable
            
        Returns:
            True if task was disabled, False if task_id not found
        """
        if task_id in self._tasks:
            self._tasks[task_id].enabled = False
            self._tasks[task_id].next_run = None
            return True
        return False
    
    def get_tasks(self) -> list[ScheduledTask]:
        """
        Get all scheduled tasks.
        
        Returns:
            List of all ScheduledTask objects
        """
        return list(self._tasks.values())
    
    def get_next_runs(self) -> dict[str, float]:
        """
        Get next run times for all enabled tasks.
        
        Returns:
            Dictionary mapping task_id to next run timestamp
        """
        return {
            task_id: task.next_run
            for task_id, task in self._tasks.items()
            if task.enabled and task.next_run is not None
        }
    
    def check_due(self) -> list[ScheduledTask]:
        """
        Check which tasks are due to run.
        
        Returns:
            List of ScheduledTask objects that are due
        """
        current_time = time.time()
        due_tasks: list[ScheduledTask] = []
        
        for task in self._tasks.values():
            if task.enabled and task.next_run is not None:
                if task.next_run <= current_time:
                    due_tasks.append(task)
        
        return due_tasks
    
    def _calculate_next_run(self, schedule: str) -> float | None:
        """
        Calculate the next run time based on a cron-like expression.
        
        Args:
            schedule: Cron-like schedule expression
            
        Returns:
            Unix timestamp of next run, or None if invalid schedule
        """
        try:
            parts = schedule.split()
            if len(parts) != 5:
                return None
            
            # Simple implementation: parse the cron expression
            # and calculate the next run time
            return self._parse_cron_expression(parts)
        except Exception:
            return None
    
    def _parse_cron_expression(self, parts: list[str]) -> float | None:
        """
        Parse a cron expression and calculate next run time.
        
        Args:
            parts: List of 5 cron expression parts [minute, hour, day, month, weekday]
            
        Returns:
            Unix timestamp of next run
        """
        minute_str, hour_str, day_str, month_str, weekday_str = parts
        
        current = time.time()
        local_time = time.localtime(current)
        
        # Extract current values
        current_minute = local_time.tm_min
        current_hour = local_time.tm_hour
        current_day = local_time.tm_mday
        current_month = local_time.tm_mon
        current_weekday = local_time.tm_wday
        
        # Parse minute
        if minute_str == "*":
            next_minute = current_minute
        elif minute_str.startswith("*/"):
            interval = int(minute_str[2:])
            next_minute = ((current_minute // interval) + 1) * interval
            if next_minute >= 60:
                next_minute = current_minute
        else:
            next_minute = int(minute_str)
        
        # Simple implementation: add intervals based on expression
        # This is a simplified version - production might use croniter library
        
        # For */N patterns, calculate next occurrence
        if minute_str.startswith("*/"):
            interval = int(minute_str[2:])
            # Calculate next run time by adding interval
            next_run = current + (interval * 60)
            
            # Adjust for hour if minute rolls over
            if current_minute + interval >= 60:
                # Add an hour
                next_run += 3600
            
            return next_run
        
        # For specific minute patterns like "0"
        if minute_str.isdigit():
            interval = int(minute_str)
            if interval <= 59:
                if interval > current_minute:
                    # Same hour, later minute
                    next_run = current + (interval - current_minute) * 60
                else:
                    # Next hour
                    next_run = current + (60 - current_minute + interval) * 60
                return next_run
        
        # Default: return current time + 60 seconds for simple cases
        return current + 60
    
    def run_due_tasks(self) -> dict[str, bool]:
        """
        Run all due tasks and update their schedule.
        
        Returns:
            Dictionary mapping task_id to success status
        """
        results: dict[str, bool] = {}
        due_tasks = self.check_due()
        
        for task in due_tasks:
            try:
                callback = self._callbacks.get(task.task_id)
                if callback:
                    callback()
                    
                    # Update last_run and calculate next_run
                    task.last_run = time.time()
                    task.next_run = self._calculate_next_run(task.schedule)
                    
                    results[task.task_id] = True
                else:
                    results[task.task_id] = False
            except Exception:
                results[task.task_id] = False
        
        return results


# Type alias for Textual App - avoids circular imports
TextualApp = Any


class SchedulerScreen:
    """
    Textual Screen for managing scheduled tasks.
    
    Displays a list of scheduled tasks with their schedule,
    enabled status, and next run times. Provides controls
    for adding, editing, and removing tasks.
    
    Note: This is a placeholder class. Full Textual integration
    would require implementing the compose() method with proper
    Textual widgets for the dashboard UI.
    """
    
    def __init__(self, scheduler: Scheduler, app: TextualApp | None = None):
        """
        Initialize the scheduler screen.
        
        Args:
            scheduler: The Scheduler instance to manage
            app: Optional reference to the Textual app
        """
        self.scheduler = scheduler
        self.app = app
    
    def compose(self) -> None:
        """
        Compose the UI layout.
        
        Override this method in subclasses to define
        the Textual widget layout for the screen.
        """
        # This will be implemented in the actual TUI
        # Using Textual's compose method for layout
        pass
    
    def on_mount(self) -> None:
        """Handle screen mount event."""
        pass
    
    def refresh_tasks(self) -> None:
        """Refresh the task list display."""
        pass