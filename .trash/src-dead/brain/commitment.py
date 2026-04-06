#!/usr/bin/env python3
"""Commitment Tracker — BDI-style commitment to prevent thrashing"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from datetime import datetime


class CommitmentLevel(Enum):
    NONE = "NONE"
    WEAK = "WEAK"
    STRONG = "STRONG"
    ABSOLUTE = "ABSOLUTE"


class CommitmentStatus(Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    DROPPED = "DROPPED"
    FULFILLED = "FULFILLED"


@dataclass
class Commitment:
    commitment_id: str
    goal: str
    plan: str
    level: str
    status: str
    created_at: str
    belief_snapshot: dict = field(default_factory=dict)
    drop_conditions: list = field(default_factory=list)
    attempts: int = 0
    max_attempts: int = 3


class CommitmentTracker:
    def __init__(self):
        self.commitments: dict[str, Commitment] = {}
        self._counter = 0

    def commit(self, goal: str, plan: str, level: str = "STRONG",
               belief_snapshot: dict = None, drop_conditions: list = None) -> Commitment:
        self._counter += 1
        commitment = Commitment(
            commitment_id=f"CMT_{self._counter:04d}",
            goal=goal,
            plan=plan,
            level=level,
            status=CommitmentStatus.ACTIVE.value,
            created_at=datetime.utcnow().isoformat(),
            belief_snapshot=belief_snapshot or {},
            drop_conditions=drop_conditions or [],
        )
        self.commitments[commitment.commitment_id] = commitment
        return commitment

    def should_continue(self, commitment_id: str, current_beliefs: dict = None) -> bool:
        if commitment_id not in self.commitments:
            return False

        commitment = self.commitments[commitment_id]

        if commitment.status != CommitmentStatus.ACTIVE.value:
            return False

        if commitment.attempts >= commitment.max_attempts:
            commitment.status = CommitmentStatus.DROPPED.value
            return False

        if current_beliefs and self._beliefs_changed_significantly(commitment.belief_snapshot, current_beliefs):
            if commitment.level == CommitmentLevel.ABSOLUTE.value:
                return True
            commitment.status = CommitmentStatus.SUSPENDED.value
            return False

        return True

    def record_attempt(self, commitment_id: str, success: bool):
        if commitment_id in self.commitments:
            commitment = self.commitments[commitment_id]
            commitment.attempts += 1
            if success:
                commitment.status = CommitmentStatus.FULFILLED.value

    def drop(self, commitment_id: str, reason: str = ""):
        if commitment_id in self.commitments:
            self.commitments[commitment_id].status = CommitmentStatus.DROPPED.value

    def get_active(self) -> list:
        return [c for c in self.commitments.values() if c.status == CommitmentStatus.ACTIVE.value]

    def _beliefs_changed_significantly(self, snapshot: dict, current: dict) -> bool:
        if not snapshot:
            return False
        changed_keys = set(snapshot.keys()) ^ set(current.keys())
        for key in set(snapshot.keys()) & set(current.keys()):
            if snapshot[key] != current[key]:
                changed_keys.add(key)
        return len(changed_keys) > len(snapshot) * 0.5
