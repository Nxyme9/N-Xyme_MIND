"""Semantic task classifier using embeddings + SGDClassifier."""

import logging
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
from sklearn.linear_model import SGDClassifier
from sklearn.calibration import CalibratedClassifierCV

from packages.learning_engine.embeddings.model_cache import get_embedding_cache

logger = logging.getLogger(__name__)

AGENTS = [
    "sisyphus", "hephaestus", "prometheus", "atlas", "oracle",
    "momus", "metis", "explore", "librarian", "sisyphus-junior", "multimodal-looker",
]

TASK_CLUSTERS = {
    "fix_bug": "fix bug error crash broken issue debug trace",
    "add_feature": "add feature implement create new functionality build",
    "refactor": "refactor restructure improve clean up reorganize optimize",
    "research": "find search explore investigate look up discover locate",
    "review": "review audit check verify validate inspect analyze",
    "architect": "architecture design system redesign plan structure blueprint",
    "test": "test write tests unit integration coverage verify",
    "document": "document docs readme explain describe write docs",
}

CLUSTER_TO_AGENT = {
    "fix_bug": "hephaestus",
    "add_feature": "hephaestus",
    "refactor": "hephaestus",
    "research": "explore",
    "review": "oracle",
    "architect": "prometheus",
    "test": "sisyphus-junior",
    "document": "librarian",
}


@dataclass
class ClassificationResult:
    predicted_agent: str
    predicted_level: int
    confidence: float
    method: str
    all_scores: Dict[str, float]
    top_features: List[str]


class SemanticTaskClassifier:
    """Classifies tasks to agents using semantic embeddings + SGDClassifier."""

    def __init__(self, db_path: str = ".sisyphus/routing.db"):
        self._cache = get_embedding_cache()
        self._classifier: Optional[SGDClassifier] = None
        self._calibrator: Optional[CalibratedClassifierCV] = None
        self._trained = False
        self._training_samples = 0
        self._min_samples = 50
        self._db_path = Path(db_path)

    def classify(self, task_description: str) -> ClassificationResult:
        """Main entry point — classify task to agent."""
        embedding = self._cache.encode(task_description)

        if self._trained and self._training_samples >= self._min_samples:
            return self._predict_with_classifier(task_description, embedding)
        else:
            return self._embedding_similarity_fallback(task_description, embedding)

    def _predict_with_classifier(self, task: str, embedding: np.ndarray) -> ClassificationResult:
        """Predict using trained SGDClassifier with calibrated probabilities."""
        probs = self._calibrator.predict_proba([embedding])[0]
        best_idx = int(np.argmax(probs))

        return ClassificationResult(
            predicted_agent=AGENTS[best_idx],
            predicted_level=2,
            confidence=float(probs[best_idx]),
            method="semantic_classifier",
            all_scores={AGENTS[i]: float(probs[i]) for i in range(len(AGENTS))},
            top_features=self._get_top_features(embedding),
        )

    def _embedding_similarity_fallback(self, task: str, embedding: np.ndarray) -> ClassificationResult:
        """Cold-start fallback: cosine similarity to task cluster centroids."""
        scores = {}
        for cluster_name, centroid_text in TASK_CLUSTERS.items():
            centroid_emb = self._cache.encode(centroid_text)
            sim = float(np.dot(embedding, centroid_emb))
            scores[cluster_name] = sim

        best_cluster = max(scores, key=scores.get)
        best_score = scores[best_cluster]

        return ClassificationResult(
            predicted_agent=CLUSTER_TO_AGENT.get(best_cluster, "hephaestus"),
            predicted_level=2,
            confidence=min(best_score, 0.7),
            method="embedding_similarity",
            all_scores={agent: 0.0 for agent in AGENTS},
            top_features=[best_cluster],
        )

    def partial_fit(self, task_description: str, agent: str, success: bool):
        """Online learning — update classifier with new outcome."""
        if agent not in AGENTS:
            return

        embedding = self._cache.encode(task_description)
        agent_idx = AGENTS.index(agent)

        if self._classifier is None:
            self._classifier = SGDClassifier(
                loss="log_loss",
                penalty="l2",
                alpha=0.0001,
                class_weight="balanced",
                max_iter=1000,
                tol=1e-4,
                random_state=42,
            )
            self._classifier.partial_fit(
                [embedding], [agent_idx], classes=list(range(len(AGENTS)))
            )
        else:
            self._classifier.partial_fit([embedding], [agent_idx])

        self._training_samples += 1

        if self._training_samples >= self._min_samples and self._training_samples % 100 == 0:
            self._recalibrate()

    def _recalibrate(self):
        """Recalibrate probabilities using isotonic regression."""
        tasks, agents = self._load_historical_data()
        if len(tasks) < self._min_samples:
            return

        embeddings = self._cache.encode(tasks)
        agent_indices = [AGENTS.index(a) for a in agents]

        self._calibrator = CalibratedClassifierCV(
            self._classifier, cv=3, method="isotonic"
        )
        self._calibrator.fit(embeddings, agent_indices)
        self._trained = True

    def _load_historical_data(self) -> tuple:
        """Load historical outcomes from routing.db."""
        if not self._db_path.exists():
            return [], []
        conn = sqlite3.connect(str(self._db_path))
        rows = conn.execute(
            "SELECT task_description, agent FROM outcomes WHERE agent IS NOT NULL ORDER BY timestamp DESC LIMIT 1000"
        ).fetchall()
        conn.close()
        tasks = [r[0] for r in rows if r[0]]
        agents_list = [r[1] for r in rows if r[1] and r[1] in AGENTS]
        # Keep only matched pairs
        matched = [(t, a) for t, a in zip(tasks, agents_list)]
        return [m[0] for m in matched], [m[1] for m in matched]

    def _get_top_features(self, embedding: np.ndarray) -> List[str]:
        """Get top contributing agents for interpretability."""
        if self._classifier is None:
            return []
        scores = self._classifier.decision_function([embedding])[0]
        sorted_indices = np.argsort(scores)[::-1]
        return [AGENTS[i] for i in sorted_indices[:3]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "trained": self._trained,
            "training_samples": self._training_samples,
            "min_samples_needed": self._min_samples,
            "classifier_type": "SGDClassifier" if self._classifier else None,
        }
