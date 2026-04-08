"""Bayesian confidence intervals for success rate estimation."""

from __future__ import annotations

from typing import TypedDict

from scipy.stats import beta


class ConfidenceResult(TypedDict):
    """Result from confidence estimation."""
    mean: float
    lower_credible: float
    upper_credible: float


class BayesianConfidenceEstimator:
    """Estimates confidence intervals using Beta distribution."""

    def __init__(self, alpha: float = 0.05, prior_alpha: float = 1.0, prior_beta: float = 1.0):
        self.alpha = alpha
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta

    def estimate(self, successes: int, total: int) -> ConfidenceResult:
        """Compute credible interval for success rate.
        
        Args:
            successes: Number of successful outcomes
            total: Total number of trials
            
        Returns:
            Dict with mean, lower_credible (1-alpha), upper_credible (1-alpha)
        """
        if total == 0:
            return {"mean": 0.5, "lower_credible": 0.0, "upper_credible": 1.0}
        
        posterior_alpha = self.prior_alpha + successes
        posterior_beta = self.prior_beta + (total - successes)
        
        dist = beta(posterior_alpha, posterior_beta)
        
        return {
            "mean": dist.mean(),
            "lower_credible": dist.ppf(self.alpha / 2),
            "upper_credible": dist.ppf(1 - self.alpha / 2),
        }


if __name__ == "__main__":
    est = BayesianConfidenceEstimator()
    
    print("Test 1: 8 successes out of 10")
    print(est.estimate(8, 10))
    
    print("\nTest 2: 1 success out of 10")
    print(est.estimate(1, 10))
    
    print("\nTest 3: 0 successes out of 5")
    print(est.estimate(0, 5))
    
    print("\nTest 4: 50 successes out of 100")
    print(est.estimate(50, 100))