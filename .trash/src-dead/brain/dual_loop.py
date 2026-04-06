#!/usr/bin/env python3
"""Dual-Loop Architecture — Reactive (fast) + Deliberative (complex)"""

import re
from dataclasses import dataclass
from enum import Enum

TECH_TERMS = re.compile(
    r"\b(API|REST|GraphQL|OAuth|JWT|SQL|NoSQL|Docker|Kubernetes|AWS|GCP|Azure|"
    r"microservice|database|cache|queue|async|thread|socket|HTTP|TCP|UDP|"
    r"class|function|method|interface|protocol|algorithm|architecture|"
    r"deploy|infrastructure|pipeline|CI/CD|regression|integration)\b",
    re.IGNORECASE,
)


class LoopType(Enum):
    REACTIVE = "REACTIVE"
    DELIBERATIVE = "DELIBERATIVE"


@dataclass
class LoopDecision:
    loop_type: str
    reason: str
    word_count: int
    has_tech_terms: bool
    intent_type: str
    risk: str


class DualLoop:
    def __init__(self):
        self.reactive_count = 0
        self.deliberative_count = 0

    def select_loop(self, task_description: str, intent_type: str = "UNKNOWN",
                    risk: str = "LOW") -> LoopDecision:
        word_count = len(task_description.split())
        has_tech = bool(TECH_TERMS.search(task_description))

        if intent_type in ['OUT_OF_SCOPE']:
            decision = LoopDecision(
                loop_type=LoopType.DELIBERATIVE.value,
                reason="Out of scope requires deliberation",
                word_count=word_count,
                has_tech_terms=has_tech,
                intent_type=intent_type,
                risk=risk,
            )
            self.deliberative_count += 1
            return decision

        if risk == 'HIGH':
            decision = LoopDecision(
                loop_type=LoopType.DELIBERATIVE.value,
                reason="High risk requires deliberation",
                word_count=word_count,
                has_tech_terms=has_tech,
                intent_type=intent_type,
                risk=risk,
            )
            self.deliberative_count += 1
            return decision

        if intent_type in ['ARCH_SPEC', 'DECISION_LOCK', 'AUDIT']:
            decision = LoopDecision(
                loop_type=LoopType.DELIBERATIVE.value,
                reason=f"Intent {intent_type} requires deliberation",
                word_count=word_count,
                has_tech_terms=has_tech,
                intent_type=intent_type,
                risk=risk,
            )
            self.deliberative_count += 1
            return decision

        if word_count < 20 and not has_tech and intent_type in ['EXTRACT', 'FORMAT', 'SUMMARIZE']:
            decision = LoopDecision(
                loop_type=LoopType.REACTIVE.value,
                reason="Simple task, fast path",
                word_count=word_count,
                has_tech_terms=has_tech,
                intent_type=intent_type,
                risk=risk,
            )
            self.reactive_count += 1
            return decision

        if word_count >= 50 or has_tech:
            decision = LoopDecision(
                loop_type=LoopType.DELIBERATIVE.value,
                reason="Complex task with technical terms",
                word_count=word_count,
                has_tech_terms=has_tech,
                intent_type=intent_type,
                risk=risk,
            )
            self.deliberative_count += 1
            return decision

        decision = LoopDecision(
            loop_type=LoopType.REACTIVE.value,
            reason="Default reactive path",
            word_count=word_count,
            has_tech_terms=has_tech,
            intent_type=intent_type,
            risk=risk,
        )
        self.reactive_count += 1
        return decision

    def get_stats(self) -> dict:
        total = self.reactive_count + self.deliberative_count
        return {
            "reactive_count": self.reactive_count,
            "deliberative_count": self.deliberative_count,
            "total": total,
            "reactive_pct": self.reactive_count / total * 100 if total > 0 else 0,
            "deliberative_pct": self.deliberative_count / total * 100 if total > 0 else 0,
        }
