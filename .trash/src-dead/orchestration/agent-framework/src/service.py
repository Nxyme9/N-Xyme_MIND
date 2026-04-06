from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uvicorn
import asyncio
import uuid
import logging

from .router import Router
from .permission_manager import PermissionManager
from .cancellation import CancellationToken, TaskState, TaskTracker

app = FastAPI(
    title="Agent Framework API",
    description="API for Agent Framework & Permissions service",
    version="1.0.0",
)

# Initialize router and permission manager
router = Router("../../configs/opencode/agents")
permission_manager = PermissionManager("../../configs/opencode/permissions.json")

# Cancellation / task tracking
task_tracker = TaskTracker()
logger = logging.getLogger("agent-framework")


class TaskRequest(BaseModel):
    task: str
    context: Optional[Dict[str, Any]] = None


class PermissionCheckRequest(BaseModel):
    role: str
    permission: str


class PermissionEvaluateRequest(BaseModel):
    command: str
    role: str


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "agent-framework",
        "version": "1.0.0",
        "timestamp": __import__("time").time(),
    }


@app.get("/agents")
async def get_agents():
    agents = router.get_all_agents()
    return [agent.config for agent in agents]


@app.get("/agents/{name}")
async def get_agent(name: str):
    agent = router.get_agent_by_name(name)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.config


@app.post("/route")
async def route_task(request: TaskRequest, response: Response):
    agent = router.route_task(request.task, request.context or {})
    if not agent:
        raise HTTPException(status_code=500, detail="Routing failed")

    # Start an interruptible, background task for the routed agent
    task_id = str(uuid.uuid4())
    token = task_tracker.register_task(
        task_id, agent.get_name(), {"task": request.task, "context": request.context}
    )

    async def _run_task():
        try:
            total_seconds = 30  # Simulated long-running task duration
            for _ in range(total_seconds):
                if token.is_cancelled():
                    task_tracker.update_state(task_id, TaskState.CANCELLED)
                    return
                await asyncio.sleep(1)
            task_tracker.update_state(task_id, TaskState.COMPLETED)
        except Exception as e:
            logger.exception("Error while executing task %s: %s", task_id, e)
            task_tracker.update_state(task_id, TaskState.ERROR)

    # Fire-and-forget background execution
    asyncio.create_task(_run_task())
    # Expose the task_id to clients via header for cancellation later
    response.headers["X-Task-Id"] = task_id
    return agent.config


@app.get("/status")
async def get_status():
    # Return a snapshot of all active tasks and their states
    return task_tracker.get_all()


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    status = task_tracker.get_status(task_id)
    if not status:
        raise HTTPException(status_code=404, detail="Task not found")
    return status


@app.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    cancelled = task_tracker.cancel(task_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"task_id": task_id, "status": "CANCELLING"}


@app.post("/permissions/check")
async def check_permission(request: PermissionCheckRequest):
    allowed = permission_manager.check_permission(request.role, request.permission)
    return {"allowed": allowed}


@app.post("/permissions/evaluate")
async def evaluate_permission(request: PermissionEvaluateRequest):
    action = permission_manager.evaluate_rule(request.command, request.role)
    return {"action": action}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)
