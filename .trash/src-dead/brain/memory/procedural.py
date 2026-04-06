"""Procedural memory for learned skills and patterns."""
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class ProductionRule:
    rule_id: str
    name: str
    condition: str
    action: str
    success_count: int = 0
    failure_count: int = 0
    activation: float = 1.0

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.5

class ProceduralMemory:
    def __init__(self, storage_path: str = "data/procedural_memory.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.rules: dict[str, ProductionRule] = {}
        self._load()

    def store(self, rule_id: str, name: str, condition: str, action: str) -> ProductionRule:
        rule = ProductionRule(rule_id=rule_id, name=name, condition=condition, action=action)
        self.rules[rule_id] = rule
        self._save()
        return rule

    def find_matching(self, context: str) -> list:
        context_lower = context.lower()
        matches = []
        for rule in self.rules.values():
            if rule.condition.lower() in context_lower:
                matches.append(rule)
        return sorted(matches, key=lambda r: r.success_rate * r.activation, reverse=True)

    def record_success(self, rule_id: str):
        if rule_id in self.rules:
            self.rules[rule_id].success_count += 1
            self.rules[rule_id].activation = min(1.0, self.rules[rule_id].activation + 0.1)
            self._save()

    def record_failure(self, rule_id: str):
        if rule_id in self.rules:
            self.rules[rule_id].failure_count += 1
            self.rules[rule_id].activation = max(0.0, self.rules[rule_id].activation - 0.2)
            self._save()

    def _load(self):
        if self.storage_path.exists():
            data = json.loads(self.storage_path.read_text())
            for rid, rdata in data.items():
                self.rules[rid] = ProductionRule(**rdata)

    def _save(self):
        data = {rid: {"rule_id": r.rule_id, "name": r.name, "condition": r.condition, "action": r.action, "success_count": r.success_count, "failure_count": r.failure_count, "activation": r.activation} for rid, r in self.rules.items()}
        self.storage_path.write_text(json.dumps(data, indent=2))
