"""Memory retrieval and search functionality."""
from dataclasses import dataclass
from typing import Optional
from .working import WorkingMemory
from .episodic import EpisodicMemory
from .semantic import SemanticMemory
from .procedural import ProceduralMemory

@dataclass
class RetrievalResult:
    source: str
    key: str
    value: str
    activation: float
    relevance: float

class MemoryRetrieval:
    def __init__(self):
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()

    def retrieve(self, query: str, layers: list = None, max_results: int = 5) -> list:
        if layers is None:
            layers = ['working', 'episodic', 'semantic', 'procedural']

        results = []

        if 'working' in layers:
            for item in self.working.get_all():
                if query.lower() in item.key.lower() or query.lower() in item.value.lower():
                    results.append(RetrievalResult(
                        source='working', key=item.key, value=item.value,
                        activation=item.activation, relevance=0.9
                    ))

        if 'episodic' in layers:
            episodes = self.episodic.search(query, max_results=3)
            for ep in episodes:
                results.append(RetrievalResult(
                    source='episodic', key=ep.get('name', ''), value=ep.get('text', ''),
                    activation=0.7, relevance=0.8
                ))

        if 'semantic' in layers:
            concepts = self.semantic.search(query)
            for concept in concepts[:3]:
                results.append(RetrievalResult(
                    source='semantic', key=concept.name, value=concept.description,
                    activation=concept.activation, relevance=0.85
                ))

        if 'procedural' in layers:
            rules = self.procedural.find_matching(query)
            for rule in rules[:3]:
                results.append(RetrievalResult(
                    source='procedural', key=rule.name, value=f"IF {rule.condition} THEN {rule.action}",
                    activation=rule.activation * rule.success_rate, relevance=0.75
                ))

        results.sort(key=lambda r: r.activation * r.relevance, reverse=True)
        return results[:max_results]

    def decay_all(self, rate: float = 0.1):
        self.working.decay(rate)
