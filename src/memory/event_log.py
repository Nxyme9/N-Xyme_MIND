#!/usr/bin/env python3
"""Event Log — Append-only JSONL event storage"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict


@dataclass
class Event:
    event_id: str
    timestamp: str
    event_type: str
    agent: str
    content: dict
    parent_id: Optional[str] = None
    invariants_checked: list = None

    def __post_init__(self):
        if self.invariants_checked is None:
            self.invariants_checked = []


class EventLog:
    def __init__(self, log_path: str):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.log_path.exists():
            self.log_path.touch()

    def append(self, event_type: str, agent: str, content: dict,
               parent_id: str = None, invariants: list = None) -> Event:
        event = Event(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.utcnow().isoformat(),
            event_type=event_type,
            agent=agent,
            content=content,
            parent_id=parent_id,
            invariants_checked=invariants or [],
        )
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(asdict(event)) + '\n')
        return event

    def read_all(self) -> list:
        events = []
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def read_by_type(self, event_type: str) -> list:
        return [e for e in self.read_all() if e['event_type'] == event_type]

    def read_by_agent(self, agent: str) -> list:
        return [e for e in self.read_all() if e['agent'] == agent]

    def count(self) -> int:
        return len(self.read_all())

    def rewrite(self, events: list):
        raise PermissionError("EventLog is append-only. Use append() instead.")
