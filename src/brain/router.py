#!/usr/bin/env python3
"""Router — Rule-first routing (R0-R7)"""

from dataclasses import dataclass
from enum import Enum


class Target(Enum):
    GPU_WORKER = "GPU_WORKER"
    SMALL_UTILITY = "SMALL_UTILITY"
    CRITIC_ONLY = "CRITIC_ONLY"


class IntentType(Enum):
    ARCH_SPEC = "ARCH_SPEC"
    AUDIT = "AUDIT"
    SUMMARIZE = "SUMMARIZE"
    EXTRACT = "EXTRACT"
    FORMAT = "FORMAT"
    DECISION_LOCK = "DECISION_LOCK"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class Complexity(Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


class Risk(Enum):
    LOW = "LOW"
    MED = "MED"
    HIGH = "HIGH"


@dataclass
class RoutePlan:
    target: str
    use_evidence: bool
    use_critic: bool
    loop_cap: int
    reason: str


class Router:
    def __init__(self, scope_fence: list = None):
        self.scope_fence = scope_fence or ['pipeline build', 'model download', 'external access']

    def route(self, intent_type: str, complexity: str = 'MED', risk: str = 'LOW',
              has_fact_claims: bool = False, evidence_available: str = 'SOME') -> RoutePlan:

        if self._is_out_of_scope(intent_type):
            return RoutePlan(
                target=Target.CRITIC_ONLY.value,
                use_evidence=False,
                use_critic=True,
                loop_cap=0,
                reason='R0: Out of scope'
            )

        if intent_type in ['EXTRACT', 'FORMAT'] and complexity == 'LOW':
            return RoutePlan(
                target=Target.SMALL_UTILITY.value,
                use_evidence=False,
                use_critic=True,
                loop_cap=0,
                reason='R1: Low complexity extract/format'
            )

        if intent_type in ['ARCH_SPEC', 'DECISION_LOCK']:
            return RoutePlan(
                target=Target.GPU_WORKER.value,
                use_evidence=has_fact_claims,
                use_critic=True,
                loop_cap=1,
                reason='R2: Architecture spec or decision lock'
            )

        if intent_type == 'AUDIT':
            return RoutePlan(
                target=Target.GPU_WORKER.value,
                use_evidence=True,
                use_critic=True,
                loop_cap=1,
                reason='R3: Audit'
            )

        if risk == 'HIGH':
            return RoutePlan(
                target=Target.GPU_WORKER.value,
                use_evidence=True,
                use_critic=True,
                loop_cap=1,
                reason='R4: High risk'
            )

        if evidence_available == 'NONE' and has_fact_claims:
            return RoutePlan(
                target=Target.GPU_WORKER.value,
                use_evidence=True,
                use_critic=True,
                loop_cap=1,
                reason='R5: No evidence but has FACT claims'
            )

        if intent_type == 'SUMMARIZE' and evidence_available == 'STRONG':
            return RoutePlan(
                target=Target.SMALL_UTILITY.value,
                use_evidence=has_fact_claims,
                use_critic=True,
                loop_cap=1,
                reason='R6: Summarize with strong evidence'
            )

        return RoutePlan(
            target=Target.GPU_WORKER.value,
            use_evidence=has_fact_claims,
            use_critic=True,
            loop_cap=1,
            reason='R7: Default'
        )

    def _is_out_of_scope(self, intent_type: str) -> bool:
        return intent_type == 'OUT_OF_SCOPE'
