#!/usr/bin/env python3
"""Athena Executor — Queue manager for BMAD pipeline tasks"""

import json
import logging
from pathlib import Path
from graphlib import TopologicalSorter, CycleError
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger("athena-executor")

GRAPHITI_URL = "http://localhost:8001/json-rpc"


def load_manifest(queue_dir: Path) -> dict:
    manifest = queue_dir / "manifest.json"
    return json.loads(manifest.read_text())


def load_task(queue_dir: Path, task_id: str) -> dict:
    slot_file = queue_dir / f"{task_id}.json"
    return json.loads(slot_file.read_text())


def save_task(queue_dir: Path, task: dict):
    slot_file = queue_dir / f"{task['id']}.json"
    slot_file.write_text(json.dumps(task, indent=2))


def build_execution_waves(tasks: List[dict]) -> List[List[str]]:
    graph = {}
    for t in tasks:
        tid = t["id"]
        deps = t.get("dependencies", [])
        graph[tid] = set(deps)

    ts = TopologicalSorter(graph)
    ts.prepare()

    waves = []
    while ts.is_active():
        ready = list(ts.get_ready())
        waves.append(ready)
        for tid in ready:
            ts.done(tid)
    return waves


def get_next_tasks(queue_dir: str = ".athena-queue") -> List[dict]:
    queue_path = Path(queue_dir)
    manifest = load_manifest(queue_path)
    tasks = []

    for entry in manifest.get("tasks", []):
        task = load_task(queue_path, entry["id"])
        if task.get("status") == "queued":
            tasks.append(task)

    if not tasks:
        return []

    try:
        waves = build_execution_waves(tasks)
    except CycleError as e:
        logger.error(f"Dependency cycle detected: {e}")
        return []

    wave_map = {t["id"]: t for t in tasks}
    ready_tasks = []
    for tid in waves[0]:
        ready_tasks.append(wave_map[tid])

    return ready_tasks


def mark_task_running(queue_dir: str, task_id: str):
    queue_path = Path(queue_dir)
    task = load_task(queue_path, task_id)
    task["status"] = "running"
    task["started_at"] = datetime.utcnow().isoformat()
    save_task(queue_path, task)


def mark_task_completed(queue_dir: str, task_id: str, result: str):
    queue_path = Path(queue_dir)
    task = load_task(queue_path, task_id)
    task["status"] = "completed"
    task["completed_at"] = datetime.utcnow().isoformat()
    task["result"] = result
    save_task(queue_path, task)
    log_to_graphiti(task, result)


def mark_task_failed(queue_dir: str, task_id: str, error: str):
    queue_path = Path(queue_dir)
    task = load_task(queue_path, task_id)

    # Impasse detection: spawn sub-agent if stuck
    try:
        from brain.impasse import ImpasseHandler
        impasse = ImpasseHandler()
        imp = impasse.detect(task.get("title", ""), error=error)
        if imp and impasse.should_spawn_subagent(imp):
            strategy = impasse.get_spawn_strategy(imp)
            new_task = {
                "id": f"s{len(list(queue_path.glob('s*.json'))) + 100}",
                "title": f"[IMPASSE] {strategy['prompt'][:50]}",
                "agent": strategy["agent"],
                "category": strategy["category"],
                "status": "queued",
                "dependencies": [],
                "thinking_config": {"temperature": 0.7, "max_tokens": 2000},
            }
            new_file = queue_path / f"{new_task['id']}.json"
            new_file.write_text(json.dumps(new_task, indent=2))
            logger.info(f"Impasse: spawned {strategy['agent']} for {task_id}")
    except Exception as e:
        logger.warning(f"Impasse detection failed: {e}")

    task["status"] = "failed"
    task["error"] = error
    task["completed_at"] = datetime.utcnow().isoformat()
    save_task(queue_path, task)


def log_to_graphiti(task: dict, result: str):
    try:
        import requests

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "graphiti_add_episode",
            "params": {
                "name": f"Task: {task.get('title', task['id'])}",
                "text": f"Agent: {task['agent']}\nResult: {result[:500]}",
                "source": "athena-executor",
                "group_id": "pipeline-runs",
            },
        }
        requests.post(GRAPHITI_URL, json=payload, timeout=5)
    except Exception:
        pass


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

    parser = argparse.ArgumentParser(description="Athena Queue Manager")
    parser.add_argument("--queue", default=".athena-queue", help="Queue directory")
    parser.add_argument("--list", action="store_true", help="List ready tasks")
    args = parser.parse_args()

    if args.list:
        tasks = get_next_tasks(args.queue)
        for t in tasks:
            print(f"{t['id']}: {t['title']} -> {t['agent']} ({t['category']})")
    else:
        print("Use --list to see ready tasks. Execution is handled by Sisyphus via task().")
