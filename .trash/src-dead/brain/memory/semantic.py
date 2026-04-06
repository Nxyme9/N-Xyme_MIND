"""Semantic memory for facts and knowledge."""
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class Concept:
    concept_id: str
    name: str
    description: str
    relations: dict = field(default_factory=dict)
    activation: float = 1.0

class SemanticMemory:
    def __init__(self, storage_path: str = "data/semantic_memory.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.concepts: dict[str, Concept] = {}
        self._load()

    def store(self, concept_id: str, name: str, description: str, relations: dict = None) -> Concept:
        concept = Concept(concept_id=concept_id, name=name, description=description, relations=relations or {})
        self.concepts[concept_id] = concept
        self._save()
        return concept

    def retrieve(self, concept_id: str) -> Optional[Concept]:
        if concept_id in self.concepts:
            concept = self.concepts[concept_id]
            concept.activation = min(1.0, concept.activation + 0.1)
            return concept
        return None

    def search(self, query: str) -> list:
        query_lower = query.lower()
        results = []
        for concept in self.concepts.values():
            if query_lower in concept.name.lower() or query_lower in concept.description.lower():
                results.append(concept)
        return sorted(results, key=lambda c: c.activation, reverse=True)

    def _load(self):
        if self.storage_path.exists():
            data = json.loads(self.storage_path.read_text())
            for cid, cdata in data.items():
                self.concepts[cid] = Concept(**cdata)

    def _save(self):
        data = {cid: {"concept_id": c.concept_id, "name": c.name, "description": c.description, "relations": c.relations, "activation": c.activation} for cid, c in self.concepts.items()}
        self.storage_path.write_text(json.dumps(data, indent=2))
