"""Embed PowerShell command history into Graphiti."""

import requests, os, time

GRAPHITI = "http://localhost:8001/json-rpc"
HISTORY = os.path.expanduser(
    "~/AppData/Roaming/Microsoft/Windows/PowerShell/PSReadLine/ConsoleHost_history.txt"
)
STATE_FILE = "data/last-history-line.txt"


def get_last_line():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return int(f.read().strip())
    return 0


def set_last_line(n):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        f.write(str(n))


def add_episode(text, name):
    r = requests.post(
        GRAPHITI,
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "graphiti_add_episode",
                "arguments": {"text": text, "name": name, "source": "command-history"},
            },
        },
    )
    return r.status_code == 200


if not os.path.exists(HISTORY):
    print("No history file found")
    exit()

with open(HISTORY, "r", encoding="utf-8") as f:
    lines = f.readlines()
last = get_last_line()
new_lines = lines[last:]

if not new_lines:
    print("No new commands")
    exit()

# Batch commands into episodes (group of 10)
batch_size = 10
embedded = 0
for i in range(0, len(new_lines), batch_size):
    batch = new_lines[i : i + batch_size]
    text = "Command history batch:\n" + "\n".join(
        f"  {j + 1}. {cmd.strip()}" for j, cmd in enumerate(batch) if cmd.strip()
    )
    name = f"cmd-history-{int(time.time())}-{i}"
    if add_episode(text, name):
        embedded += len(batch)

set_last_line(len(lines))
print(f"Embedded {embedded} commands ({len(lines)} total in history)")
