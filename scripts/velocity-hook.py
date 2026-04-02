"""Velocity hook: auto-detect task completion from plan checkbox changes.
Run this after each task to auto-record velocity.
Usage: python scripts/velocity-hook.py [task_name] [category]
"""
import sys, os, re, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from metrics_store import MetricsStore

PLAN_DIR = ".sisyphus/plans"
STATE_FILE = "data/plan-checkbox-state.json"
store = MetricsStore('data/nervous_system.db')

def get_checkboxes(plan_path):
    if not os.path.exists(plan_path):
        return {}
    content = open(plan_path, 'r', encoding='utf-8').read()
    checkboxes = {}
    for line in content.splitlines():
        match = re.match(r'^- \[([ x])\] (.+)', line)
        if match:
            checkboxes[match.group(2).strip()[:80]] = match.group(1)
    return checkboxes

def load_state():
    if os.path.exists(STATE_FILE):
        return json.load(open(STATE_FILE))
    return {}

def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(state, open(STATE_FILE, 'w'), indent=2)

def categorize(name):
    n = name.lower()
    if any(w in n for w in ['fix', 'bug', 'error']): return 'bugfix'
    if any(w in n for w in ['test', 'verify']): return 'testing'
    if any(w in n for w in ['config', 'setting']): return 'config'
    if any(w in n for w in ['integrate', 'wire', 'hook']): return 'integration'
    if any(w in n for w in ['create', 'add', 'build', 'new']): return 'feature'
    return 'general'

# If task name provided manually
if len(sys.argv) >= 2:
    task_name = sys.argv[1]
    cat = sys.argv[2] if len(sys.argv) > 2 else categorize(task_name)
    est = store.estimate_task(cat)
    task_id = f"task-{int(time.time())}"
    store.record_task_start(task_id, task_name, category=cat, estimated_minutes=est)
    store.record_task_complete(task_id)
    
# Fire velocity trigger
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from trigger_router import TriggerRouter
router = TriggerRouter('triggers.json')

for plan_name, task_name in completions:
    router.process_event({
        'source': 'velocity',
        'type': 'task_completed',
        'severity': 'info',
        'data': {'task_name': task_name, 'category': categorize(task_name)}
    })

v = store.get_velocity(7)
    print(f"Tracked: {task_name} ({cat}, ~{est}min)")
    if v:
        print(f"Velocity: {v['tasks_per_hour']}/hr (avg {v['avg_minutes']}min)")
    exit()

# Auto-detect from plan files
old_state = load_state()
new_state = {}
completions = []

for f in os.listdir(PLAN_DIR):
    if not f.endswith('.md'):
        continue
    plan_path = os.path.join(PLAN_DIR, f)
    plan_name = f.replace('.md', '')
    checkboxes = get_checkboxes(plan_path)
    
    for name, state in checkboxes.items():
        key = f"{plan_name}::{name}"
        new_state[key] = state
        if state == 'x' and old_state.get(key) == ' ':
            completions.append((plan_name, name))

save_state(new_state)

if completions:
    for plan_name, task_name in completions:
        cat = categorize(task_name)
        est = store.estimate_task(cat)
        task_id = f"auto-{int(time.time())}-{hash(task_name) % 10000}"
        store.record_task_start(task_id, task_name, plan_name, est, cat)
        store.record_task_complete(task_id)
        print(f"Auto-tracked: {task_name} ({cat}, ~{est}min)")
    
    
# Fire velocity trigger
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
from trigger_router import TriggerRouter
router = TriggerRouter('triggers.json')

for plan_name, task_name in completions:
    router.process_event({
        'source': 'velocity',
        'type': 'task_completed',
        'severity': 'info',
        'data': {'task_name': task_name, 'category': categorize(task_name)}
    })

v = store.get_velocity(7)
    if v:
        print(f"Velocity: {v['tasks_per_hour']}/hr (avg {v['avg_minutes']}min)")
else:
    print("No new completions detected")
