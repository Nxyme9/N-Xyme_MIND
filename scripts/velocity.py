"""Velocity tracker CLI. Usage:
  python scripts/velocity.py start "task name" [category] [estimated_minutes]
  python scripts/velocity.py stop "task name"
  python scripts/velocity.py status
  python scripts/velocity.py estimate [category]
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from metrics_store import MetricsStore

store = MetricsStore('data/nervous_system.db')

if len(sys.argv) < 2:
    print(__doc__)
    exit()

cmd = sys.argv[1]

if cmd == 'start' and len(sys.argv) >= 3:
    name = sys.argv[2]
    cat = sys.argv[3] if len(sys.argv) > 3 else 'general'
    est = int(sys.argv[4]) if len(sys.argv) > 4 else store.estimate_task(cat)
    task_id = f"task-{int(__import__('time').time())}"
    store.record_task_start(task_id, name, category=cat, estimated_minutes=est)
    print(f"Started: {name} (est: {est}min, cat: {cat})")
    print(f"Task ID: {task_id}")

elif cmd == 'stop' and len(sys.argv) >= 3:
    name = sys.argv[2]
    # Find in-progress task with this name
    import sqlite3
    conn = sqlite3.connect('data/nervous_system.db')
    row = conn.execute("SELECT task_id FROM task_velocity WHERE task_name=? AND status='in_progress' ORDER BY started_at DESC LIMIT 1", (name,)).fetchone()
    if row:
        store.record_task_complete(row[0])
        v = store.get_velocity(1)
        print(f"Completed: {name}")
        if v:
            print(f"Velocity: {v['tasks_per_hour']} tasks/hour (avg {v['avg_minutes']}min)")
    else:
        print(f"No in-progress task named '{name}'")
    conn.close()

elif cmd == 'status':
    v = store.get_velocity(7)
    if v:
        print(f"=== Velocity (7 days) ===")
        print(f"Tasks: {v['tasks']}")
        print(f"Avg: {v['avg_minutes']} min/task")
        print(f"Speed: {v['tasks_per_hour']} tasks/hour")
        print(f"Estimates: {v['estimate_ratio']}x too high")
    else:
        print("No completed tasks in last 7 days")
    
    cats = store.get_velocity_by_category(7)
    if cats:
        print(f"\nBy category:")
        for c in cats:
            print(f"  {c['category']}: {c['avg_minutes']}min avg ({c['per_hour']}/hr)")

elif cmd == 'estimate':
    cat = sys.argv[2] if len(sys.argv) > 2 else 'general'
    est = store.estimate_task(cat)
    print(f"Estimated time for '{cat}': ~{est} minutes")

else:
    print(__doc__)
