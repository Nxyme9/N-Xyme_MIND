"""Predictive Routing

Uses historical data to predict the best agent for a task.
Simple ML-like approach using pattern matching and success rates.
"""

import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger("predictive-router")


class PredictiveRouter:
    """Predicts best agent based on historical patterns."""
    
    def __init__(self, store=None):
        self._store = store
        self._patterns: Dict[str, Dict[str, Any]] = {}
        self._min_samples = 3  # Minimum samples for a pattern to be reliable
    
    def set_store(self, store):
        """Set the SQLite store for historical data."""
        self._store = store
    
    def build_patterns(self):
        """Build prediction patterns from historical data."""
        if not self._store:
            return
        
        outcomes = self._store.get_outcomes(limit=1000)
        
        # Group by task description patterns
        pattern_stats = defaultdict(lambda: {'agents': defaultdict(lambda: {'success': 0, 'total': 0, 'avg_latency': 0})})
        
        for outcome in outcomes:
            desc = outcome.get('task_description', '').lower()
            agent = outcome.get('agent', 'unknown')
            success = outcome.get('success', False)
            latency = outcome.get('latency_ms', 0)
            
            # Extract keywords
            keywords = self._extract_keywords(desc)
            
            for keyword in keywords:
                stats = pattern_stats[keyword]['agents'][agent]
                stats['total'] += 1
                if success:
                    stats['success'] += 1
                stats['avg_latency'] = (stats['avg_latency'] * (stats['total'] - 1) + latency) / stats['total'] if stats['total'] > 1 else latency
        
        # Convert to patterns
        self._patterns = {}
        for keyword, data in pattern_stats.items():
            best_agent = None
            best_score = -1
            
            for agent, stats in data['agents'].items():
                if stats['total'] >= self._min_samples:
                    success_rate = stats['success'] / stats['total']
                    # Score: success_rate * 0.7 + (1 - normalized_latency) * 0.3
                    latency_score = 1 - min(stats['avg_latency'] / 1000, 1.0)
                    score = success_rate * 0.7 + latency_score * 0.3
                    
                    if score > best_score:
                        best_score = score
                        best_agent = agent
            
            if best_agent:
                self._patterns[keyword] = {
                    'agent': best_agent,
                    'confidence': best_score,
                    'samples': sum(s['total'] for s in data['agents'].values())
                }
        
        logger.info(f"Built {len(self._patterns)} predictive patterns")
    
    def predict(self, task_description: str) -> Dict[str, Any]:
        """Predict best agent for a task."""
        if not self._patterns:
            self.build_patterns()
        
        desc = task_description.lower()
        keywords = self._extract_keywords(desc)
        
        # Find matching patterns
        matches = []
        for keyword in keywords:
            if keyword in self._patterns:
                pattern = self._patterns[keyword]
                matches.append((keyword, pattern))
        
        if not matches:
            return {
                'predicted_agent': 'hephaestus',  # Default
                'confidence': 0.5,
                'method': 'default',
                'patterns_matched': 0
            }
        
        # Weight by confidence and samples
        weighted_scores = defaultdict(lambda: {'score': 0, 'weight': 0})
        for keyword, pattern in matches:
            agent = pattern['agent']
            confidence = pattern['confidence']
            samples = pattern['samples']
            weight = min(samples / 10, 1.0)  # Normalize weight
            
            weighted_scores[agent]['score'] += confidence * weight
            weighted_scores[agent]['weight'] += weight
        
        # Find best agent
        best_agent = None
        best_score = 0
        for agent, data in weighted_scores.items():
            score = data['score'] / data['weight'] if data['weight'] > 0 else 0
            if score > best_score:
                best_score = score
                best_agent = agent
        
        return {
            'predicted_agent': best_agent or 'hephaestus',
            'confidence': best_score,
            'method': 'predictive',
            'patterns_matched': len(matches),
            'patterns': [m[0] for m in matches[:5]]
        }
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract meaningful keywords from text."""
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
                     'should', 'may', 'might', 'must', 'shall', 'can', 'need', 'dare',
                     'ought', 'used', 'to', 'of', 'in', 'for', 'on', 'with', 'at', 'by',
                     'from', 'as', 'into', 'through', 'during', 'before', 'after', 'above',
                     'below', 'between', 'under', 'again', 'further', 'then', 'once', 'here',
                     'there', 'when', 'where', 'why', 'how', 'all', 'each', 'few', 'more',
                     'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own',
                     'same', 'so', 'than', 'too', 'very', 'just', 'don', 'now', 'i', 'me',
                     'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours',
                     'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her',
                     'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their',
                     'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that',
                     'these', 'those', 'am', 'and', 'but', 'if', 'or', 'because', 'until',
                     'while', 'about', 'against', 'new'}
        
        # Extract words
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        
        # Filter stop words and return unique keywords
        return list(set(w for w in words if w not in stop_words))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get predictive router statistics."""
        return {
            'total_patterns': len(self._patterns),
            'min_samples': self._min_samples,
            'top_patterns': sorted(
                [(k, v['confidence'], v['samples']) for k, v in self._patterns.items()],
                key=lambda x: x[1], reverse=True
            )[:10]
        }


# Global router instance
_predictive_router = None

def get_predictive_router() -> PredictiveRouter:
    """Get or create the global predictive router."""
    global _predictive_router
    if _predictive_router is None:
        _predictive_router = PredictiveRouter()
    return _predictive_router
