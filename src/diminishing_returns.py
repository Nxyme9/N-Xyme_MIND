#!/usr/bin/env python3
"""Diminishing Returns Detector — Detect when iteration stops adding value"""

import logging
import re
import time
from typing import List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("diminishing-returns")

TECH_TERMS = re.compile(
    r"\b(API|REST|GraphQL|OAuth|JWT|SQL|NoSQL|Docker|Kubernetes|AWS|GCP|Azure|"
    r"microservice|database|cache|queue|async|thread|socket|HTTP|TCP|UDP|"
    r"class|function|method|interface|protocol|algorithm|architecture|"
    r"deploy|infrastructure|pipeline|CI/CD|regression|integration)\b",
    re.IGNORECASE,
)


@dataclass
class IterationScore:
    iteration: int
    quality_score: float
    new_findings: int
    confidence: float
    timestamp: str


@dataclass
class DiminishingReturnsDetector:
    window: int = 3
    threshold: float = 0.03
    min_iterations: int = 2
    max_iterations: int = 5
    max_time_seconds: int = 60
    confidence_override: float = 0.9
    scores: List[IterationScore] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)

    def record(self, score: IterationScore):
        self.scores.append(score)
        logger.info(
            f"Iteration {score.iteration}: quality={score.quality_score:.2f}, "
            f"findings={score.new_findings}, confidence={score.confidence:.2f}"
        )

    def should_transition(self) -> bool:
        if not self.scores:
            return False

        latest = self.scores[-1]

        if latest.confidence >= self.confidence_override:
            logger.info("Transition: confidence override (>= 0.9)")
            return True

        if time.time() - self.start_time > self.max_time_seconds:
            logger.info("Transition: time budget exceeded (60s)")
            return True

        if len(self.scores) >= self.max_iterations:
            logger.info("Transition: max iterations reached")
            return True

        if len(self.scores) < self.min_iterations:
            return False

        if self._all_deltas_below_threshold():
            logger.info("Transition: all recent deltas below threshold")
            return True

        if self._improvement_decelerating():
            logger.info("Transition: improvement rate decelerating")
            return True

        if self._findings_dried_up():
            logger.info("Transition: new findings dried up")
            return True

        return False

    def _all_deltas_below_threshold(self) -> bool:
        if len(self.scores) < self.window + 1:
            return False
        recent = self.scores[-self.window :]
        prev = self.scores[-(self.window + 1) : -1]
        deltas = [r.quality_score - p.quality_score for r, p in zip(recent, prev)]
        return all(d < self.threshold for d in deltas)

    def _improvement_decelerating(self) -> bool:
        if len(self.scores) < 3:
            return False
        d1 = self.scores[-2].quality_score - self.scores[-3].quality_score
        d2 = self.scores[-1].quality_score - self.scores[-2].quality_score
        if d1 <= 0:
            return d2 <= 0
        return (d2 / d1) < 0.2

    def _findings_dried_up(self) -> bool:
        if len(self.scores) < self.window:
            return False
        return all(s.new_findings <= 1 for s in self.scores[-self.window :])

    def get_report(self) -> dict:
        if not self.scores:
            return {"status": "no_data"}
        latest = self.scores[-1]
        return {
            "iterations": len(self.scores),
            "latest_quality": latest.quality_score,
            "total_findings": sum(s.new_findings for s in self.scores),
            "avg_quality": sum(s.quality_score for s in self.scores) / len(self.scores),
            "confidence": latest.confidence,
            "elapsed_seconds": time.time() - self.start_time,
            "should_transition": self.should_transition(),
        }


def detect_complexity(task_description: str) -> str:
    word_count = len(task_description.split())
    has_tech_terms = bool(TECH_TERMS.search(task_description))

    if word_count < 20 and not has_tech_terms:
        return "simple"
    elif word_count < 50 and has_tech_terms:
        return "medium"
    else:
        return "complex"


def create_detector(task_description: str = "") -> DiminishingReturnsDetector:
    complexity = detect_complexity(task_description)

    configs = {
        "simple": {"threshold": 0.01, "window": 2, "min_iterations": 1, "max_iterations": 3},
        "medium": {"threshold": 0.03, "window": 3, "min_iterations": 2, "max_iterations": 5},
        "complex": {"threshold": 0.05, "window": 4, "min_iterations": 3, "max_iterations": 8},
    }

    config = configs.get(complexity, configs["medium"])
    return DiminishingReturnsDetector(**config)
