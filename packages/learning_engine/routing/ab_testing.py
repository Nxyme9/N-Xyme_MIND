"""A/B Testing Framework.

Provides A/B testing capabilities for routing strategies, prompt templates,
and other system components. Tracks statistical significance and automatically
selects winners.
"""

from __future__ import annotations

import json
import time
import math
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("ab-testing")


class TestStatus(Enum):
    """Status of an A/B test."""
    RUNNING = "running"
    COMPLETED = "completed"
    INCONCLUSIVE = "inconclusive"


@dataclass
class TestVariant:
    """A variant in an A/B test."""
    name: str
    traffic_weight: float  # 0.0-1.0
    impressions: int = 0
    successes: int = 0
    failures: int = 0
    total_latency_ms: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        total = self.successes + self.failures
        return self.successes / total if total > 0 else 0.0
    
    @property
    def avg_latency(self) -> float:
        """Calculate average latency."""
        return self.total_latency_ms / self.impressions if self.impressions > 0 else 0.0


@dataclass
class ABTest:
    """An A/B test configuration."""
    id: str
    name: str
    description: str
    variants: Dict[str, TestVariant]
    status: TestStatus = TestStatus.RUNNING
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    winner: Optional[str] = None
    confidence: float = 0.0
    min_sample_size: int = 100
    significance_level: float = 0.05  # 95% confidence
    
    def record_outcome(self, variant_name: str, success: bool, latency_ms: float):
        """Record an outcome for a variant."""
        if variant_name not in self.variants:
            logger.warning(f"Unknown variant: {variant_name}")
            return
        
        variant = self.variants[variant_name]
        variant.impressions += 1
        variant.total_latency_ms += latency_ms
        
        if success:
            variant.successes += 1
        else:
            variant.failures += 1
        
        # Check if test is complete
        self._check_completion()
    
    def _check_completion(self):
        """Check if test has reached statistical significance."""
        if self.status != TestStatus.RUNNING:
            return
        
        # Check minimum sample size
        total_impressions = sum(v.impressions for v in self.variants.values())
        if total_impressions < self.min_sample_size:
            return
        
        # Calculate statistical significance
        variant_names = list(self.variants.keys())
        if len(variant_names) < 2:
            return
        
        # Simple z-test for two proportions
        v1 = self.variants[variant_names[0]]
        v2 = self.variants[variant_names[1]]
        
        p1 = v1.success_rate
        p2 = v2.success_rate
        n1 = v1.successes + v1.failures
        n2 = v2.successes + v2.failures
        
        if n1 == 0 or n2 == 0:
            return
        
        # Pooled proportion
        p_pool = (v1.successes + v2.successes) / (n1 + n2)
        
        if p_pool == 0 or p_pool == 1:
            return
        
        # Standard error
        se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
        
        if se == 0:
            return
        
        # Z-score
        z = (p1 - p2) / se
        
        # Approximate p-value (two-tailed)
        p_value = 2 * (1 - self._normal_cdf(abs(z)))
        
        self.confidence = 1 - p_value
        
        if p_value < self.significance_level:
            # Test is complete
            self.status = TestStatus.COMPLETED
            self.completed_at = time.time()
            self.winner = variant_names[0] if p1 > p2 else variant_names[1]
            logger.info(f"Test '{self.id}' complete: {self.winner} wins with {self.confidence:.0%} confidence")
    
    def _normal_cdf(self, x: float) -> float:
        """Approximate normal CDF."""
        return 0.5 * (1 + math.erf(x / math.sqrt(2)))
    
    def get_variant(self) -> str:
        """Get variant to use based on traffic weights."""
        import random
        r = random.random()
        cumulative = 0.0
        
        for name, variant in self.variants.items():
            cumulative += variant.traffic_weight
            if r <= cumulative:
                return name
        
        # Fallback to last variant
        return list(self.variants.keys())[-1]
    
    def get_results(self) -> Dict[str, Any]:
        """Get test results."""
        results = {
            'id': self.id,
            'name': self.name,
            'status': self.status.value,
            'winner': self.winner,
            'confidence': self.confidence,
            'variants': {}
        }
        
        for name, variant in self.variants.items():
            results['variants'][name] = {
                'impressions': variant.impressions,
                'success_rate': variant.success_rate,
                'avg_latency': variant.avg_latency,
                'traffic_weight': variant.traffic_weight
            }
        
        return results


class ABTestingFramework:
    """Framework for managing A/B tests."""
    
    def __init__(self, tests_file: str = ".sisyphus/ab_tests.json"):
        self.tests_file = Path(tests_file)
        self.tests_file.parent.mkdir(parents=True, exist_ok=True)
        self._tests: Dict[str, ABTest] = {}
        self._load_tests()
    
    def _load_tests(self):
        """Load tests from file."""
        if self.tests_file.exists():
            try:
                with open(self.tests_file) as f:
                    data = json.load(f)
                
                for test_id, test_data in data.items():
                    variants = {}
                    for var_name, var_data in test_data.get('variants', {}).items():
                        variants[var_name] = TestVariant(
                            name=var_name,
                            traffic_weight=var_data.get('traffic_weight', 0.5),
                            impressions=var_data.get('impressions', 0),
                            successes=var_data.get('successes', 0),
                            failures=var_data.get('failures', 0),
                            total_latency_ms=var_data.get('total_latency_ms', 0.0)
                        )
                    
                    self._tests[test_id] = ABTest(
                        id=test_id,
                        name=test_data.get('name', test_id),
                        description=test_data.get('description', ''),
                        variants=variants,
                        status=TestStatus(test_data.get('status', 'running')),
                        created_at=test_data.get('created_at', time.time()),
                        completed_at=test_data.get('completed_at'),
                        winner=test_data.get('winner'),
                        confidence=test_data.get('confidence', 0.0),
                        min_sample_size=test_data.get('min_sample_size', 100),
                        significance_level=test_data.get('significance_level', 0.05)
                    )
            except Exception as e:
                logger.error(f"Error loading tests: {e}")
    
    def _save_tests(self):
        """Save tests to file."""
        data = {}
        for test_id, test in self._tests.items():
            data[test_id] = {
                'id': test.id,
                'name': test.name,
                'description': test.description,
                'variants': {
                    name: {
                        'traffic_weight': v.traffic_weight,
                        'impressions': v.impressions,
                        'successes': v.successes,
                        'failures': v.failures,
                        'total_latency_ms': v.total_latency_ms
                    }
                    for name, v in test.variants.items()
                },
                'status': test.status.value,
                'created_at': test.created_at,
                'completed_at': test.completed_at,
                'winner': test.winner,
                'confidence': test.confidence,
                'min_sample_size': test.min_sample_size,
                'significance_level': test.significance_level
            }
        
        with open(self.tests_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def create_test(self, test_id: str, name: str, description: str,
                   variants: Dict[str, float], min_sample_size: int = 100) -> ABTest:
        """Create a new A/B test.
        
        Args:
            test_id: Unique test identifier
            name: Test name
            description: Test description
            variants: Dict of variant_name -> traffic_weight
            min_sample_size: Minimum samples before checking significance
        """
        # Normalize traffic weights
        total_weight = sum(variants.values())
        normalized = {name: weight / total_weight for name, weight in variants.items()}
        
        test_variants = {
            name: TestVariant(name=name, traffic_weight=weight)
            for name, weight in normalized.items()
        }
        
        test = ABTest(
            id=test_id,
            name=name,
            description=description,
            variants=test_variants,
            min_sample_size=min_sample_size
        )
        
        self._tests[test_id] = test
        self._save_tests()
        
        logger.info(f"Created test: {test_id} with {len(variants)} variants")
        return test
    
    def get_variant(self, test_id: str) -> Optional[str]:
        """Get variant to use for a test."""
        test = self._tests.get(test_id)
        if not test or test.status != TestStatus.RUNNING:
            return None
        
        return test.get_variant()
    
    def record_outcome(self, test_id: str, variant_name: str, success: bool, latency_ms: float):
        """Record an outcome for a test variant."""
        test = self._tests.get(test_id)
        if not test:
            return
        
        test.record_outcome(variant_name, success, latency_ms)
        self._save_tests()
    
    def get_test_results(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get results for a test."""
        test = self._tests.get(test_id)
        if not test:
            return None
        
        return test.get_results()
    
    def get_all_tests(self) -> Dict[str, Dict[str, Any]]:
        """Get all tests and their results."""
        return {
            test_id: test.get_results()
            for test_id, test in self._tests.items()
        }
    
    def get_winner(self, test_id: str) -> Optional[str]:
        """Get the winner of a completed test."""
        test = self._tests.get(test_id)
        if not test or test.status != TestStatus.COMPLETED:
            return None
        
        return test.winner


# Global A/B testing framework instance
_ab_testing = None

def get_ab_testing() -> ABTestingFramework:
    """Get or create the global A/B testing framework."""
    global _ab_testing
    if _ab_testing is None:
        _ab_testing = ABTestingFramework()
    return _ab_testing