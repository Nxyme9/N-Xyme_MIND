#!/usr/bin/env python3
"""Critic/Judge — Verdict gating with loop caps"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class VerdictType(Enum):
    APPROVE = "APPROVE"
    REVISE = "REVISE"
    BLOCK = "BLOCK"


@dataclass
class Verdict:
    verdict: str
    reasons: list = field(default_factory=list)
    required_deltas: list = field(default_factory=list)
    unsupported_facts: list = field(default_factory=list)
    assumptions: list = field(default_factory=list)
    risk_level: str = "LOW"
    loop_count: int = 0


class Critic:
    def __init__(self, loop_cap: int = 1):
        self.loop_cap = loop_cap
        self.verdicts = []

    def evaluate(self, claims: list, evidence_map: dict = None, scope_fence: list = None) -> Verdict:
        reasons = []
        unsupported_facts = []
        assumptions = []
        risk_level = "LOW"

        for claim in claims:
            claim_type = claim.get('claim_type', 'INFERENCE')
            support_status = claim.get('support_status', 'UNSUPPORTED')
            text = claim.get('text', '')

            if claim_type == 'FACT' and support_status == 'UNSUPPORTED':
                unsupported_facts.append(text)
                reasons.append(f"Unsupported FACT: {text[:50]}")

            if support_status == 'ASSUMPTION':
                assumptions.append(text)

            if scope_fence and self._violates_scope(text, scope_fence):
                reasons.append(f"Scope violation: {text[:50]}")
                risk_level = "HIGH"

        if unsupported_facts:
            risk_level = "HIGH" if len(unsupported_facts) > 2 else "MEDIUM"

        loop_count = len(self.verdicts)
        recent_revises = sum(1 for v in self.verdicts[-2:] if v.verdict == VerdictType.REVISE.value)

        if recent_revises >= 2:
            verdict_type = VerdictType.BLOCK.value
            reasons.append("Two consecutive REVISEs — needs user input")
        elif risk_level == "HIGH" and unsupported_facts:
            verdict_type = VerdictType.BLOCK.value
            reasons.append("HIGH risk with unsupported facts")
        elif unsupported_facts:
            verdict_type = VerdictType.REVISE.value
        else:
            verdict_type = VerdictType.APPROVE.value

        verdict = Verdict(
            verdict=verdict_type,
            reasons=reasons,
            unsupported_facts=unsupported_facts,
            assumptions=assumptions,
            risk_level=risk_level,
            loop_count=loop_count,
        )
        self.verdicts.append(verdict)
        return verdict

    def _violates_scope(self, text: str, scope_fence: list) -> bool:
        text_lower = text.lower()
        for forbidden in scope_fence:
            if forbidden.lower() in text_lower:
                return True
        return False

    def reset(self):
        self.verdicts = []
