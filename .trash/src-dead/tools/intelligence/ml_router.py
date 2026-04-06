"""Advanced ML Routing

Uses machine learning to predict the best agent for a task based on
historical data, task features, and agent performance.
"""

import json
import time
import math
import logging
import sqlite3
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict
from contextlib import contextmanager

logger = logging.getLogger("ml-router")


class MLRouter:
    """Machine learning-based routing system."""
    
    def __init__(self, db_path: str = ".sisyphus/routing.db"):
        self.db_path = Path(db_path)
        self._model_weights: Dict[str, Dict[str, float]] = {}
        self._feature_importance: Dict[str, float] = {}
        self._training_count: int = 0
        self._last_trained: float = 0.0
        self._min_training_samples: int = 50
        self._load_model()
    
    def _load_model(self):
        """Load model weights from file."""
        model_file = self.db_path.parent / "ml_model.json"
        if model_file.exists():
            try:
                with open(model_file) as f:
                    data = json.load(f)
                self._model_weights = data.get('model_weights', {})
                self._feature_importance = data.get('feature_importance', {})
                self._training_count = data.get('training_count', 0)
                self._last_trained = data.get('last_trained', 0.0)
            except Exception as e:
                logger.error(f"Error loading ML model: {e}")
    
    def _save_model(self):
        """Save model weights to file."""
        model_file = self.db_path.parent / "ml_model.json"
        data = {
            'model_weights': self._model_weights,
            'feature_importance': self._feature_importance,
            'training_count': self._training_count,
            'last_trained': self._last_trained
        }
        with open(model_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _extract_features(self, task_description: str) -> Dict[str, float]:
        """Extract features from task description."""
        features = {}
        desc = task_description.lower()
        
        # Text features
        features['length'] = len(desc) / 100.0  # Normalized length
        features['word_count'] = len(desc.split()) / 20.0  # Normalized word count
        
        # Keyword features
        keywords = {
            'fix': 1.0 if 'fix' in desc else 0.0,
            'bug': 1.0 if 'bug' in desc else 0.0,
            'add': 1.0 if 'add' in desc else 0.0,
            'create': 1.0 if 'create' in desc else 0.0,
            'implement': 1.0 if 'implement' in desc else 0.0,
            'refactor': 1.0 if 'refactor' in desc else 0.0,
            'test': 1.0 if 'test' in desc else 0.0,
            'review': 1.0 if 'review' in desc else 0.0,
            'debug': 1.0 if 'debug' in desc else 0.0,
            'optimize': 1.0 if 'optim' in desc else 0.0,
            'document': 1.0 if 'doc' in desc else 0.0,
            'design': 1.0 if 'design' in desc else 0.0,
            'architect': 1.0 if 'architect' in desc else 0.0,
            'security': 1.0 if 'secur' in desc else 0.0,
            'performance': 1.0 if 'perform' in desc else 0.0,
            'auth': 1.0 if 'auth' in desc else 0.0,
            'api': 1.0 if 'api' in desc else 0.0,
            'database': 1.0 if 'database' in desc or 'db' in desc else 0.0,
            'ui': 1.0 if 'ui' in desc or 'frontend' in desc else 0.0,
            'backend': 1.0 if 'backend' in desc else 0.0,
        }
        features.update(keywords)
        
        # Complexity indicators
        features['complexity_indicators'] = sum([
            1.0 if word in desc else 0.0
            for word in ['entire', 'system', 'architecture', 'complex', 'large', 'major']
        ]) / 6.0
        
        return features
    
    def _get_historical_data(self) -> List[Dict[str, Any]]:
        """Get historical routing data for training."""
        if not self.db_path.exists():
            return []
        
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT task_description, agent, success, latency_ms, level
                FROM outcomes
                ORDER BY timestamp DESC
                LIMIT 1000
            """).fetchall()
            conn.close()
            
            data = []
            for row in rows:
                data.append({
                    'task_description': row['task_description'],
                    'agent': row['agent'],
                    'success': row['success'],
                    'latency_ms': row['latency_ms'],
                    'level': row['level']
                })
            
            return data
        except Exception as e:
            logger.error(f"Error getting historical data: {e}")
            return []
    
    def train(self):
        """Train the ML model on historical data."""
        data = self._get_historical_data()
        
        if len(data) < self._min_training_samples:
            logger.info(f"Not enough data for training: {len(data)} < {self._min_training_samples}")
            return False
        
        # Initialize model weights
        agents = set(d['agent'] for d in data)
        features = self._extract_features(data[0]['task_description'])
        
        for agent in agents:
            if agent not in self._model_weights:
                self._model_weights[agent] = {
                    feature: 0.0 for feature in features.keys()
                }
        
        # Train using simple online learning (perceptron-like)
        learning_rate = 0.01
        epochs = 5
        
        for epoch in range(epochs):
            for sample in data:
                features = self._extract_features(sample['task_description'])
                actual_agent = sample['agent']
                success = sample['success']
                
                # Predict scores for all agents
                scores = {}
                for agent in agents:
                    weights = self._model_weights.get(agent, {})
                    score = sum(weights.get(f, 0.0) * v for f, v in features.items())
                    scores[agent] = score
                
                # Update weights based on outcome
                if success:
                    # Increase weights for actual agent
                    for feature, value in features.items():
                        if actual_agent in self._model_weights:
                            self._model_weights[actual_agent][feature] += learning_rate * value
                else:
                    # Decrease weights for actual agent
                    for feature, value in features.items():
                        if actual_agent in self._model_weights:
                            self._model_weights[actual_agent][feature] -= learning_rate * value
                
                # Update feature importance
                for feature, value in features.items():
                    if value > 0:
                        self._feature_importance[feature] = self._feature_importance.get(feature, 0.0) + 0.001
        
        self._training_count += 1
        self._last_trained = time.time()
        self._save_model()
        
        logger.info(f"ML model trained: {len(data)} samples, {self._training_count} epochs")
        return True
    
    def predict(self, task_description: str) -> Dict[str, Any]:
        """Predict the best agent for a task."""
        # Train if needed
        if self._training_count == 0 or (time.time() - self._last_trained > 3600):
            self.train()
        
        features = self._extract_features(task_description)
        
        # Calculate scores for all agents
        scores = {}
        for agent, weights in self._model_weights.items():
            score = sum(weights.get(f, 0.0) * v for f, v in features.items())
            scores[agent] = score
        
        if not scores:
            return {
                'predicted_agent': 'hephaestus',
                'confidence': 0.5,
                'method': 'ml_fallback',
                'reason': 'No ML model trained yet'
            }
        
        # Get best agent
        best_agent = max(scores, key=scores.get)
        best_score = scores[best_agent]
        
        # Calculate confidence based on score difference
        sorted_scores = sorted(scores.values(), reverse=True)
        if len(sorted_scores) > 1:
            score_diff = sorted_scores[0] - sorted_scores[1]
            confidence = min(0.5 + score_diff, 1.0)
        else:
            confidence = 0.5
        
        # Get top features contributing to prediction
        top_features = []
        if best_agent in self._model_weights:
            weights = self._model_weights[best_agent]
            feature_contributions = [
                (f, weights.get(f, 0.0) * v)
                for f, v in features.items()
                if v > 0
            ]
            feature_contributions.sort(key=lambda x: abs(x[1]), reverse=True)
            top_features = [f for f, _ in feature_contributions[:3]]
        
        return {
            'predicted_agent': best_agent,
            'confidence': confidence,
            'method': 'ml',
            'reason': f"ML prediction based on {len(self._model_weights.get(best_agent, {}))} features",
            'top_features': top_features,
            'scores': scores
        }
    
    def get_model_stats(self) -> Dict[str, Any]:
        """Get ML model statistics."""
        return {
            'training_count': self._training_count,
            'last_trained': self._last_trained,
            'agents_tracked': len(self._model_weights),
            'features_used': len(self._feature_importance),
            'model_weights': {
                agent: len(weights)
                for agent, weights in self._model_weights.items()
            }
        }


# Global ML router instance
_ml_router = None

def get_ml_router() -> MLRouter:
    """Get or create the global ML router."""
    global _ml_router
    if _ml_router is None:
        _ml_router = MLRouter()
    return _ml_router
