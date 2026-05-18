"""
Adversarial GAN loop — generates hard examples to expose blind spots.
Story 5.4: Generator produces confusing queries, discriminator (Rosetta) learns.
"""
import numpy as np
from typing import Callable


class AdversarialGenerator:
    """Generates queries that fool the current routing model."""

    def __init__(self, tool_descriptions: dict):
        self.tool_descriptions = tool_descriptions

    def generate_confusing_query(self, target_tool: str, confuse_with: str) -> str:
        """Generate a query that should route to target_tool but uses vocabulary of confuse_with."""
        # Mix vocabulary from both tools
        target_words = self.tool_descriptions[target_tool].split()
        confuse_words = self.tool_descriptions[confuse_with].split()
        # Create query with confused intent
        confused_query = f"{' '.join(confuse_words[:3])} for {' '.join(target_words[:2])}"
        return confused_query

    def adversarial_accuracy(self, routing_fn: Callable, n_attempts: int = 100) -> float:
        """Measure accuracy on generated adversarial examples."""
        import random
        tools = list(self.tool_descriptions.keys())
        correct = 0
        for _ in range(n_attempts):
            target = random.choice(tools)
            confuse = random.choice([t for t in tools if t != target])
            query = self.generate_confusing_query(target, confuse)
            result = routing_fn(query)
            if result == target:
                correct += 1
        return correct / n_attempts