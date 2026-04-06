"""Prompt Evolution — PromptWizard: Generate → Critique → Refine → Evaluate.

Implements an iterative prompt improvement loop with version tracking,
scoring, and SQLite persistence.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class EvaluationGrade(str, Enum):
    """Qualitative grade assigned to a prompt version."""

    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"


@dataclass
class PromptVersion:
    """A single version of an evolved prompt."""

    version: int
    content: str
    generation_method: str = "manual"
    critique: str = ""
    refinements: List[str] = field(default_factory=list)
    score: float = 0.0
    grade: EvaluationGrade = EvaluationGrade.POOR
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def content_hash(self) -> str:
        """SHA-256 hash of the prompt content."""
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()[:16]


@dataclass
class PromptEvolutionRecord:
    """Full evolution history for one prompt template."""

    prompt_id: str
    versions: List[PromptVersion] = field(default_factory=list)
    best_version: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def current(self) -> Optional[PromptVersion]:
        """Return the latest version, or None."""
        return self.versions[-1] if self.versions else None

    def best(self) -> Optional[PromptVersion]:
        """Return the highest-scoring version, or None."""
        if not self.versions:
            return None
        return max(self.versions, key=lambda v: v.score)


class PromptWizard:
    """Iterative prompt evolution engine.

    The loop:
        1. **Generate** — produce a candidate prompt
        2. **Critique** — identify weaknesses
        3. **Refine** — apply targeted improvements
        4. **Evaluate** — score the result

    Usage::

        wizard = PromptWizard(db_path="prompts.db")
        wizard.register("code_review", "Review this code: {code}")
        wizard.evolve("code_review", max_iterations=5)
        best = wizard.get_best("code_review")
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        generator: Optional[Callable[[str, str], str]] = None,
        critic: Optional[Callable[[str], str]] = None,
        refiner: Optional[Callable[[str, str], str]] = None,
        evaluator: Optional[Callable[[str], float]] = None,
    ) -> None:
        self._db_path = db_path or ":memory:"
        self._conn = None
        self._records: Dict[str, PromptEvolutionRecord] = {}
        self._generator = generator or self._default_generator
        self._critic = critic or self._default_critic
        self._refiner = refiner or self._default_refiner
        self._evaluator = evaluator or self._default_evaluator
        self._init_db()
        self._load_from_db()

    # ------------------------------------------------------------------
    # Database helpers
    # ------------------------------------------------------------------

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS prompt_records (
                    prompt_id TEXT PRIMARY KEY,
                    best_version INTEGER NOT NULL DEFAULT 0,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS prompt_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_id TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    generation_method TEXT NOT NULL DEFAULT 'manual',
                    critique TEXT NOT NULL DEFAULT '',
                    refinements_json TEXT NOT NULL DEFAULT '[]',
                    score REAL NOT NULL DEFAULT 0.0,
                    grade TEXT NOT NULL DEFAULT 'poor',
                    created_at REAL NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}',
                    FOREIGN KEY (prompt_id) REFERENCES prompt_records(prompt_id)
                );
            """)

    def _connect(self) -> sqlite3.Connection:
        if self._db_path == ":memory:":
            if self._conn is None:
                self._conn = sqlite3.connect(":memory:")
                self._conn.row_factory = sqlite3.Row
            return self._conn
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _load_from_db(self) -> None:
        import json

        with self._connect() as conn:
            records = conn.execute("SELECT * FROM prompt_records").fetchall()
        for row in records:
            record = PromptEvolutionRecord(
                prompt_id=row["prompt_id"],
                best_version=row["best_version"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            versions = conn.execute(
                "SELECT * FROM prompt_versions WHERE prompt_id = ? ORDER BY version",
                (row["prompt_id"],),
            ).fetchall()
            for v in versions:
                pv = PromptVersion(
                    version=v["version"],
                    content=v["content"],
                    generation_method=v["generation_method"],
                    critique=v["critique"],
                    refinements=json.loads(v["refinements_json"]),
                    score=v["score"],
                    grade=EvaluationGrade(v["grade"]),
                    created_at=v["created_at"],
                    metadata=json.loads(v["metadata_json"]),
                )
                record.versions.append(pv)
            self._records[record.prompt_id] = record

    def _persist_record(self, record: PromptEvolutionRecord) -> None:
        import json

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO prompt_records (prompt_id, best_version, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(prompt_id) DO UPDATE SET
                    best_version=excluded.best_version,
                    updated_at=excluded.updated_at
                """,
                (
                    record.prompt_id,
                    record.best_version,
                    record.created_at,
                    record.updated_at,
                ),
            )
            for v in record.versions:
                conn.execute(
                    """
                    INSERT INTO prompt_versions (
                        prompt_id, version, content, generation_method,
                        critique, refinements_json, score, grade,
                        created_at, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT DO NOTHING
                    """,
                    (
                        record.prompt_id,
                        v.version,
                        v.content,
                        v.generation_method,
                        v.critique,
                        json.dumps(v.refinements),
                        v.score,
                        v.grade.value,
                        v.created_at,
                        json.dumps(v.metadata),
                    ),
                )

    # ------------------------------------------------------------------
    # Default strategies (rule-based, no external deps)
    # ------------------------------------------------------------------

    @staticmethod
    def _default_generator(prompt_id: str, previous: str) -> str:
        """Generate a new candidate from the previous version."""
        if not previous:
            return f"You are an expert assistant. {prompt_id}: Please follow these instructions carefully."
        additions = [
            "Be specific and actionable.",
            "Provide concrete examples where helpful.",
            "Consider edge cases and error conditions.",
            "Structure the output clearly with headings.",
            "Prioritize clarity over brevity.",
        ]
        idx = hash(previous) % len(additions)
        return f"{previous}\n\n{additions[idx]}"

    @staticmethod
    def _default_critic(content: str) -> str:
        """Return a critique string identifying weaknesses."""
        issues: List[str] = []
        if len(content) < 20:
            issues.append("Too short — lacks sufficient detail")
        if content.lower().count("please") > 2:
            issues.append("Overly polite — wastes tokens")
        if "{placeholder}" in content:
            issues.append("Contains unexpanded placeholder '{placeholder}'")
        if not any(c.isupper() for c in content[:50]):
            issues.append("No capitalization in opening — may reduce authority")
        if len(content.split()) > 500:
            issues.append("Too verbose — risk of context overflow")
        if not issues:
            issues.append("No major issues detected")
        return "; ".join(issues)

    @staticmethod
    def _default_refiner(content: str, critique: str) -> str:
        """Apply targeted refinements based on critique."""
        refined = content
        if "Too short" in critique:
            refined += "\n\nProvide step-by-step reasoning before your final answer."
        if "Overly polite" in critique:
            refined = refined.replace("Please ", "")
        if "Contains unexpanded placeholder" in critique:
            refined = refined.replace("{placeholder}", "[SPECIFY_INPUT]")
        if "Too verbose" in critique:
            sentences = refined.split(". ")
            refined = ". ".join(sentences[:10]) + "."
        return refined

    @staticmethod
    def _default_evaluator(content: str) -> float:
        """Score a prompt on a 0-1 scale using heuristic rules."""
        score = 0.0
        words = content.split()
        word_count = len(words)

        # Optimal length: 30-200 words
        if 30 <= word_count <= 200:
            score += 0.3
        elif 10 <= word_count < 30 or 200 < word_count <= 400:
            score += 0.15

        # Has actionable language
        actionable = ["must", "should", "ensure", "verify", "check", "provide", "use"]
        if any(w in content.lower() for w in actionable):
            score += 0.2

        # Has structure indicators
        if any(c in content for c in [":", "-", "#", "1.", "2.", "•"]):
            score += 0.15

        # No obvious placeholders
        if "{placeholder}" not in content:
            score += 0.1

        # Diversity of vocabulary
        unique_ratio = len(set(w.lower() for w in words)) / max(word_count, 1)
        if unique_ratio > 0.7:
            score += 0.15
        elif unique_ratio > 0.5:
            score += 0.1

        # Penalty for repetition
        if word_count > 0:
            most_common = max(set(words), key=words.count)
            rep_ratio = words.count(most_common) / word_count
            if rep_ratio > 0.15:
                score -= 0.15

        return max(0.0, min(1.0, score))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, prompt_id: str, initial_content: str) -> PromptEvolutionRecord:
        """Register a new prompt template with its initial version."""
        if prompt_id in self._records:
            raise ValueError(f"Prompt '{prompt_id}' already exists")

        version = PromptVersion(
            version=1,
            content=initial_content,
            generation_method="manual",
            score=self._evaluator(initial_content),
        )
        version.grade = self._score_to_grade(version.score)

        record = PromptEvolutionRecord(
            prompt_id=prompt_id,
            versions=[version],
            best_version=1,
        )
        self._records[prompt_id] = record
        self._persist_record(record)
        logger.info(
            "Registered prompt '%s' (v%d, score=%.2f)", prompt_id, 1, version.score
        )
        return record

    def evolve(
        self,
        prompt_id: str,
        max_iterations: int = 5,
        score_threshold: float = 0.85,
    ) -> PromptEvolutionRecord:
        """Run the Generate → Critique → Refine → Evaluate loop.

        Stops when *max_iterations* is reached or *score_threshold* is met.

        Raises:
            KeyError: If the prompt_id does not exist.
            ValueError: If max_iterations < 1.
        """
        record = self._get(prompt_id)
        if max_iterations < 1:
            raise ValueError("max_iterations must be >= 1")

        for i in range(max_iterations):
            current = record.current()
            if current is None:
                break
            if current.score >= score_threshold:
                logger.info(
                    "Prompt '%s' reached threshold %.2f at v%d",
                    prompt_id,
                    current.score,
                    current.version,
                )
                break

            # 1. Generate
            new_content = self._generator(prompt_id, current.content)

            # 2. Critique
            critique = self._critic(new_content)

            # 3. Refine
            refined = self._refiner(new_content, critique)

            # 4. Evaluate
            score = self._evaluator(refined)
            grade = self._score_to_grade(score)

            new_version = PromptVersion(
                version=current.version + 1,
                content=refined,
                generation_method="promptwizard",
                critique=critique,
                refinements=[critique],
                score=score,
                grade=grade,
            )
            record.versions.append(new_version)

            # Update best
            best = record.best()
            if best is not None:
                record.best_version = best.version

            record.updated_at = time.time()
            self._persist_record(record)
            logger.info(
                "Prompt '%s' v%d: score=%.2f, grade=%s",
                prompt_id,
                new_version.version,
                score,
                grade.value,
            )

        return record

    def get(self, prompt_id: str) -> Optional[PromptEvolutionRecord]:
        """Return a prompt record by ID, or None."""
        return self._records.get(prompt_id)

    def get_best(self, prompt_id: str) -> Optional[PromptVersion]:
        """Return the best version of a prompt, or None."""
        record = self._get(prompt_id)
        return record.best()

    def get_current(self, prompt_id: str) -> Optional[PromptVersion]:
        """Return the latest version of a prompt, or None."""
        record = self._get(prompt_id)
        return record.current()

    def list_prompts(self) -> List[PromptEvolutionRecord]:
        """Return all registered prompt records."""
        return list(self._records.values())

    def compare_versions(self, prompt_id: str) -> List[Tuple[int, float, str]]:
        """Return a summary of all versions: (version, score, grade)."""
        record = self._get(prompt_id)
        return [(v.version, v.score, v.grade.value) for v in record.versions]

    def delete(self, prompt_id: str) -> None:
        """Remove a prompt record and all its versions.

        Raises:
            KeyError: If the prompt_id does not exist.
        """
        self._get(prompt_id)
        del self._records[prompt_id]
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM prompt_versions WHERE prompt_id = ?", (prompt_id,)
            )
            conn.execute("DELETE FROM prompt_records WHERE prompt_id = ?", (prompt_id,))
        logger.info("Deleted prompt '%s'", prompt_id)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _score_to_grade(score: float) -> EvaluationGrade:
        if score >= 0.85:
            return EvaluationGrade.EXCELLENT
        if score >= 0.65:
            return EvaluationGrade.GOOD
        if score >= 0.40:
            return EvaluationGrade.FAIR
        return EvaluationGrade.POOR

    def _get(self, prompt_id: str) -> PromptEvolutionRecord:
        if prompt_id not in self._records:
            raise KeyError(f"Prompt '{prompt_id}' not found")
        return self._records[prompt_id]
