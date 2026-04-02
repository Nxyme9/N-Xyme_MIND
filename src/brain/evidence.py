#!/usr/bin/env python3
"""Evidence Cortex — Claim classification and evidence tracking"""

import re
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class ClaimType(Enum):
    FACT = "FACT"
    INFERENCE = "INFERENCE"
    PLAN = "PLAN"
    REQUIREMENT = "REQUIREMENT"


class SupportStatus(Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    ASSUMPTION = "ASSUMPTION"


FACT_PATTERNS = [
    r'\b(returns?|is|are|has|have|contains?|supports?|implements?|uses?)\b.*\b(\d+|true|false|yes|no|always|never)\b',
    r'\b(API|HTTP|database|server|client|endpoint)\b.*\b(returns?|responds?|sends?|receives?)\b',
    r'\b(version|status|code|error|response)\b.*[:=]\s*\S+',
]

INFERENCE_PATTERNS = [
    r'\b(because|therefore|thus|hence|so|consequently|as a result)\b',
    r'\b(better|worse|faster|slower|more efficient|less efficient)\b',
    r'\b(probably|likely|unlikely|might|could|should|would)\b',
]

PLAN_PATTERNS = [
    r'\b(will|going to|plan to|intend to|aim to|design)\b',
    r'\b(step \d|phase \d|first|then|next|finally)\b',
    r'\b(implement|build|create|develop|deploy)\b',
]

REQUIREMENT_PATTERNS = [
    r'\b(must|shall|should|needs? to|required|mandatory)\b',
    r'\b(user|system|component)\b.*\b(require|expect|need)\b',
]


@dataclass
class Claim:
    claim_id: str
    text: str
    claim_type: str
    evidence_refs: list = field(default_factory=list)
    support_status: str = "UNSUPPORTED"
    confidence: float = 0.0


class EvidenceCortex:
    def __init__(self):
        self.claims = []
        self._counter = 0

    def classify(self, text: str) -> Claim:
        self._counter += 1
        claim_id = f"CLM_{self._counter:04d}"

        if self._matches_any(text, FACT_PATTERNS):
            claim_type = ClaimType.FACT.value
            confidence = 0.8
        elif self._matches_any(text, REQUIREMENT_PATTERNS):
            claim_type = ClaimType.REQUIREMENT.value
            confidence = 0.7
        elif self._matches_any(text, PLAN_PATTERNS):
            claim_type = ClaimType.PLAN.value
            confidence = 0.6
        elif self._matches_any(text, INFERENCE_PATTERNS):
            claim_type = ClaimType.INFERENCE.value
            confidence = 0.5
        else:
            claim_type = ClaimType.INFERENCE.value
            confidence = 0.4

        claim = Claim(
            claim_id=claim_id,
            text=text,
            claim_type=claim_type,
            confidence=confidence,
        )
        self.claims.append(claim)
        return claim

    def check_support(self, claim: Claim, evidence_refs: list = None) -> Claim:
        if evidence_refs:
            claim.evidence_refs = evidence_refs
            claim.support_status = SupportStatus.SUPPORTED.value
        elif claim.claim_type == ClaimType.FACT.value:
            claim.support_status = SupportStatus.UNSUPPORTED.value
        else:
            claim.support_status = SupportStatus.ASSUMPTION.value
        return claim

    def get_unsupported_facts(self) -> list:
        return [c for c in self.claims
                if c.claim_type == ClaimType.FACT.value
                and c.support_status == SupportStatus.UNSUPPORTED.value]

    def _matches_any(self, text: str, patterns: list) -> bool:
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False
