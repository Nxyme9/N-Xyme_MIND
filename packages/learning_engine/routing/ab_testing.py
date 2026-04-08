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
import hashlib
import random
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("ab-testing")

# Try to import statsmodels for advanced statistics
try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    logger.warning("scipy not available, using basic statistics")


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
    
    def get_significance_report(self) -> Dict[str, Any]:
        """Get detailed statistical significance report."""
        if len(self.variants) < 2:
            return {'error': 'Need at least 2 variants'}
        
        variant_names = list(self.variants.keys())
        v1 = self.variants[variant_names[0]]
        v2 = self.variants[variant_names[1]]
        
        n1 = v1.successes + v1.failures
        n2 = v2.successes + v2.failures
        
        report = {
            'test_id': self.id,
            'test_name': self.name,
            'status': self.status.value,
            'total_impressions': v1.impressions + v2.impressions,
            'variants': {}
        }
        
        for name, v in self.variants.items():
            report['variants'][name] = {
                'impressions': v.impressions,
                'successes': v.successes,
                'failures': v.failures,
                'success_rate': v.success_rate,
                'avg_latency_ms': v.avg_latency
            }
        
        if n1 > 0 and n2 > 0:
            p1 = v1.success_rate
            p2 = v2.success_rate
            
            # Chi-square test (more robust than z-test)
            observed = [[v1.successes, v1.failures], [v2.successes, v2.failures]]
            try:
                chi2, p_value, dof, expected = scipy_stats.chi2_contingency(observed)
                report['chi_square'] = {'statistic': chi2, 'p_value': p_value, 'dof': dof}
            except Exception:
                # Fallback to z-test
                p_pool = (v1.successes + v2.successes) / (n1 + n2)
                se = math.sqrt(p_pool * (1 - p_pool) * (1/n1 + 1/n2))
                z = (p1 - p2) / se if se > 0 else 0
                p_value = 2 * (1 - self._normal_cdf(abs(z)))
                report['z_test'] = {'statistic': z, 'p_value': p_value}
            
            # Latency comparison (t-test)
            if v1.impressions > 0 and v2.impressions > 0:
                # Use ratio-based approximation for latency
                if v1.avg_latency > 0 and v2.avg_latency > 0:
                    latency_ratio = v1.avg_latency / v2.avg_latency
                    report['latency_comparison'] = {
                        'variant_a_avg_ms': v1.avg_latency,
                        'variant_b_avg_ms': v2.avg_latency,
                        'ratio': latency_ratio,
                        'faster': variant_names[0] if v1.avg_latency < v2.avg_latency else variant_names[1]
                    }
            
            # Recommendation
            if self.status == TestStatus.COMPLETED:
                report['winner'] = self.winner
                report['confidence'] = self.confidence
                report['recommendation'] = f"Use '{self.winner}' with {self.confidence:.0%} confidence"
            elif self.status == TestStatus.INCONCLUSIVE:
                report['recommendation'] = "More data needed - test inconclusive"
            else:
                needed = self.min_sample_size - (v1.impressions + v2.impressions)
                report['recommendation'] = f"Need {needed} more impressions for significance"
        
        return report
    
    def compare_latency(self, variant_a: str, variant_b: str) -> Dict[str, Any]:
        """Compare latency between two variants."""
        if variant_a not in self.variants or variant_b not in self.variants:
            return {'error': 'Invalid variant names'}
        
        v1 = self.variants[variant_a]
        v2 = self.variants[variant_b]
        
        comparison = {
            'variant_a': variant_a,
            'variant_b': variant_b,
            'variant_a_avg_ms': v1.avg_latency,
            'variant_b_avg_ms': v2.avg_latency,
            'difference_ms': v1.avg_latency - v2.avg_latency,
            'percent_faster': ((v2.avg_latency - v1.avg_latency) / v2.avg_latency * 100) if v2.avg_latency > 0 else 0
        }
        
        if v1.avg_latency < v2.avg_latency:
            comparison['winner'] = variant_a
            comparison['reason'] = f"{variant_a} is {abs(comparison['percent_faster']):.1f}% faster"
        else:
            comparison['winner'] = variant_b
            comparison['reason'] = f"{variant_b} is {abs(comparison['percent_faster']):.1f}% faster"
        
        return comparison
    
    def get_recommendation(self) -> Dict[str, Any]:
        """Get recommendation for which variant to use."""
        if self.status == TestStatus.COMPLETED:
            return {
                'action': 'use_winner',
                'variant': self.winner,
                'confidence': self.confidence,
                'reason': f"Winner determined with {self.confidence:.0%} statistical confidence"
            }
        elif self.status == TestStatus.INCONCLUSIVE:
            return {
                'action': 'continue_testing',
                'reason': 'Test inconclusive, continue collecting data'
            }
        
        # Check if we have enough data
        total = sum(v.impressions for v in self.variants.values())
        if total < self.min_sample_size:
            return {
                'action': 'continue_testing',
                'reason': f"Need {self.min_sample_size - total} more impressions"
            }
        
        # Check current best performer
        best_variant = max(self.variants.items(), key=lambda x: x[1].success_rate)
        return {
            'action': 'use_best_so_far',
            'variant': best_variant[0],
            'current_success_rate': best_variant[1].success_rate,
            'reason': f"Leading with {best_variant[1].success_rate:.0%} success rate, but not yet significant"
        }
    
    def get_variant(self, task_key: Optional[str] = None) -> str:
        """Get variant to use based on traffic weights.
        
        Args:
            task_key: Optional key for deterministic routing (e.g., task_id)
                     If provided, uses consistent hashing for same key.
        """
        if task_key:
            hash_value = int(hashlib.md5(task_key.encode()).hexdigest(), 16)
            normalized_hash = (hash_value % 10000) / 10000.0
            
            cumulative = 0.0
            for name, variant in self.variants.items():
                cumulative += variant.traffic_weight
                if normalized_hash <= cumulative:
                    return name
            
            return list(self.variants.keys())[-1]
        else:
            r = random.random()
            cumulative = 0.0
            
            for name, variant in self.variants.items():
                cumulative += variant.traffic_weight
                if r <= cumulative:
                    return name
            
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
    
    def activate_test(self, test_id: str, task_key: Optional[str] = None) -> Optional[str]:
        """Activate a test and get variant assignment for a task.
        
        Args:
            test_id: The test to activate
            task_key: Optional key for deterministic assignment
            
        Returns:
            Variant name to use, or None if test not found/not running
        """
        test = self._tests.get(test_id)
        if not test:
            logger.warning(f"Test {test_id} not found")
            return None
        
        if test.status != TestStatus.RUNNING:
            logger.info(f"Test {test_id} is {test.status.value}, not activating")
            return None
        
        return test.get_variant(task_key)
    
    def get_significance_report(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed statistical significance report for a test."""
        test = self._tests.get(test_id)
        if not test:
            return None
        return test.get_significance_report()
    
    def get_recommendation(self, test_id: str) -> Optional[Dict[str, Any]]:
        """Get recommendation for a test."""
        test = self._tests.get(test_id)
        if not test:
            return None
        return test.get_recommendation()
    
    def compare_latency(self, test_id: str, variant_a: str, variant_b: str) -> Optional[Dict[str, Any]]:
        """Compare latency between two variants in a test."""
        test = self._tests.get(test_id)
        if not test:
            return None
        return test.compare_latency(variant_a, variant_b)
    
    def create_routing_test(self, test_type: str, traffic_split: Optional[Dict[str, float]] = None) -> ABTest:
        """Create a standard routing A/B test.
        
        Args:
            test_type: One of 'embedding_vs_keyword', 'graph_vs_sql', 'meta_vs_static'
            traffic_split: Optional custom traffic split (e.g., {'embedding': 0.5, 'keyword': 0.5})
            
        Returns:
            The created ABTest
        """
        if test_type == 'embedding_vs_keyword':
            variants = traffic_split or {'embedding': 0.5, 'keyword': 0.5}
            return self.create_test(
                test_id='routing_embedding_vs_keyword',
                name='Embedding vs Keyword Routing',
                description='Test semantic embedding-based routing vs keyword matching',
                variants=variants,
                min_sample_size=100
            )
        elif test_type == 'graph_vs_sql':
            variants = traffic_split or {'graph': 0.5, 'sql': 0.5}
            return self.create_test(
                test_id='routing_graph_vs_sql',
                name='Graph vs SQL Lookup',
                description='Test knowledge graph traversal vs SQL database lookup',
                variants=variants,
                min_sample_size=100
            )
        elif test_type == 'meta_vs_static':
            variants = traffic_split or {'meta': 0.5, 'static': 0.5}
            return self.create_test(
                test_id='routing_meta_vs_static',
                name='Meta-Learning vs Static Weights',
                description='Test meta-learning adaptive weights vs static routing weights',
                variants=variants,
                min_sample_size=100
            )
        else:
            raise ValueError(f"Unknown test type: {test_type}. Use: embedding_vs_keyword, graph_vs_sql, meta_vs_static")
    
    def start_routing_test(self, test_type: str, traffic_split: Optional[Dict[str, float]] = None) -> str:
        """Create and start a routing A/B test, returning variant for current task.
        
        Args:
            test_type: Type of routing test
            traffic_split: Optional traffic split configuration
            
        Returns:
            Variant name to use for this request
        """
        test = self.create_routing_test(test_type, traffic_split)
        logger.info(f"Started routing test: {test.id}")
        return test.get_variant()
    
    def get_routing_test_status(self) -> Dict[str, Any]:
        """Get status of all routing-related tests."""
        routing_tests = {
            'embedding_vs_keyword': self.get_test_results('routing_embedding_vs_keyword'),
            'graph_vs_sql': self.get_test_results('routing_graph_vs_sql'),
            'meta_vs_static': self.get_test_results('routing_meta_vs_static')
        }
        
        return {
            'active_tests': [k for k, v in routing_tests.items() if v and v.get('status') == 'running'],
            'completed_tests': [k for k, v in routing_tests.items() if v and v.get('status') == 'completed'],
            'tests': routing_tests
        }


# Global A/B testing framework instance
_ab_testing = None

def get_ab_testing() -> ABTestingFramework:
    """Get or create the global A/B testing framework."""
    global _ab_testing
    if _ab_testing is None:
        _ab_testing = ABTestingFramework()
    return _ab_testing