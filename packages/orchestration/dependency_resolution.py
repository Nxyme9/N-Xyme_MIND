"""Dependency Resolution — Topological sort for startup order"""

import logging
from typing import Dict, List, Set

logger = logging.getLogger(__name__)


class DependencyResolver:
    def __init__(self):
        self._graph: Dict[str, List[str]] = {}

    def add(self, name: str, dependencies: List[str] = None):
        self._graph[name] = dependencies or []

    def resolve(self) -> List[str]:
        visited: Set[str] = set()
        result: List[str] = []

        def visit(node: str, path: Set[str]):
            if node in path:
                raise ValueError(f"Circular dependency: {' -> '.join(path)} -> {node}")
            if node in visited:
                return
            path.add(node)
            for dep in self._graph.get(node, []):
                visit(dep, path.copy())
            visited.add(node)
            result.append(node)

        for node in self._graph:
            visit(node, set())
        return result

    def get_dependencies(self, name: str) -> List[str]:
        return self._graph.get(name, [])

    def get_dependents(self, name: str) -> List[str]:
        return [n for n, deps in self._graph.items() if name in deps]
