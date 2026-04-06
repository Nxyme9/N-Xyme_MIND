#!/usr/bin/env python3
"""Impasse Handler — Auto-spawn sub-agent when stuck (SOAR pattern)"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ImpasseType(Enum):
    NO_RULE = "NO_RULE"
    CONFLICT = "CONFLICT"
    TIMEOUT = "TIMEOUT"
    ERROR = "ERROR"


@dataclass
class Impasse:
    impasse_id: str
    impasse_type: str
    context: str
    attempts: int = 0
    resolved: bool = False
    resolution: str = ""


class ImpasseHandler:
    def __init__(self, max_attempts: int = 3):
        self.max_attempts = max_attempts
        self.impasse_history: list[Impasse] = []

    def detect(self, context: str, error: str = None, timeout: bool = False) -> Optional[Impasse]:
        if timeout:
            impasse_type = ImpasseType.TIMEOUT.value
        elif error:
            impasse_type = ImpasseType.ERROR.value
        elif "no matching rule" in context.lower() or "stuck" in context.lower():
            impasse_type = ImpasseType.NO_RULE.value
        elif "conflict" in context.lower() or "contradiction" in context.lower():
            impasse_type = ImpasseType.CONFLICT.value
        else:
            return None

        impasse = Impasse(
            impasse_id=f"IMP_{len(self.impasse_history):04d}",
            impasse_type=impasse_type,
            context=context,
        )
        self.impasse_history.append(impasse)
        return impasse

    def should_spawn_subagent(self, impasse: Impasse) -> bool:
        return impasse.attempts < self.max_attempts and not impasse.resolved

    def record_attempt(self, impasse: Impasse, success: bool, resolution: str = ""):
        impasse.attempts += 1
        if success:
            impasse.resolved = True
            impasse.resolution = resolution

    def get_spawn_strategy(self, impasse: Impasse) -> dict:
        strategies = {
            ImpasseType.NO_RULE.value: {
                "agent": "explore",
                "prompt": f"Find a solution for: {impasse.context}",
                "category": "deep",
            },
            ImpasseType.CONFLICT.value: {
                "agent": "oracle",
                "prompt": f"Resolve conflict: {impasse.context}",
                "category": "ultrabrain",
            },
            ImpasseType.TIMEOUT.value: {
                "agent": "sisyphus-junior",
                "prompt": f"Complete quickly: {impasse.context}",
                "category": "quick",
            },
            ImpasseType.ERROR.value: {
                "agent": "hephaestus",
                "prompt": f"Fix error: {impasse.context}",
                "category": "deep",
            },
        }
        return strategies.get(impasse.impasse_type, strategies[ImpasseType.NO_RULE.value])

    def get_unresolved(self) -> list:
        return [i for i in self.impasse_history if not i.resolved]
