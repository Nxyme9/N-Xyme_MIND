"""Graph Store — Knowledge graph and multi-graph storage.

Combines:
- knowledge_graph.py: Basic JSON-based knowledge graph
- multi_graph.py: MAGMA-style orthogonal graph system (semantic, temporal, causal, entity)
"""

import json
import logging
import sqlite3
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Knowledge Graph (Simple)
# ---------------------------------------------------------------------------


class KnowledgeGraph:
    """Simple JSON-based knowledge graph."""

    def __init__(self, storage_file: str = "data/knowledge_graph.json"):
        self.storage_file = Path(storage_file)
        self.storage_file.parent.mkdir(parents=True, exist_ok=True)
        self._nodes: Dict[str, dict] = {}
        self._edges: List[dict] = []
        self._load()

    def _load(self):
        if self.storage_file.exists():
            data = json.loads(self.storage_file.read_text(encoding="utf-8"))
            self._nodes = data.get("nodes", {})
            self._edges = data.get("edges", [])

    def _save(self):
        self.storage_file.write_text(
            json.dumps({"nodes": self._nodes, "edges": self._edges}, indent=2),
            encoding="utf-8",
        )

    def add_node(self, node_id: str, node_type: str, properties: dict = None):
        self._nodes[node_id] = {"type": node_type, "properties": properties or {}}
        self._save()

    def add_edge(
        self, source: str, target: str, relation: str, properties: dict = None
    ):
        self._edges.append(
            {
                "source": source,
                "target": target,
                "relation": relation,
                "properties": properties or {},
            }
        )
        self._save()

    def query(self, node_id: str) -> Dict:
        node = self._nodes.get(node_id, {})
        edges = [
            e for e in self._edges if e["source"] == node_id or e["target"] == node_id
        ]
        return {"node": node, "edges": edges}

    def search(self, query: str) -> List[Dict]:
        results = []
        for nid, node in self._nodes.items():
            if (
                query.lower() in nid.lower()
                or query.lower() in str(node.get("properties", {})).lower()
            ):
                results.append({"id": nid, **node})
        return results

    def get_stats(self) -> Dict:
        return {"nodes": len(self._nodes), "edges": len(self._edges)}


# ---------------------------------------------------------------------------
# Multi-Graph (MAGMA-style)
# ---------------------------------------------------------------------------


class GraphType(str, Enum):
    """Types of orthogonal graphs."""

    SEMANTIC = "semantic"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    ENTITY = "entity"


class RelationType(str, Enum):
    """Types of relationships between nodes."""

    RELATED_TO = "related_to"
    SIMILAR_TO = "similar_to"
    PART_OF = "part_of"
    BEFORE = "before"
    AFTER = "after"
    CAUSES = "causes"
    ENABLES = "enables"
    USES = "uses"
    DEPENDS_ON = "depends_on"


@dataclass
class GraphNode:
    """A node in the knowledge graph."""

    id: str
    graph_type: GraphType
    label: str
    content: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


@dataclass
class GraphEdge:
    """An edge connecting two nodes."""

    source_id: str
    target_id: str
    relation_type: RelationType
    weight: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphPath:
    """A path through the graph."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_weight: float
    graph_type: GraphType
    hops: int


class OrthogonalGraph:
    """A single orthogonal graph (semantic, temporal, causal, or entity)."""

    def __init__(self, graph_type: GraphType, db_path: Path | None = None):
        self.graph_type = graph_type
        self.db_path = db_path or Path(".sisyphus/graphs.db")
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self._adjacency: dict[str, list[tuple[str, RelationType, float]]] = {}
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS graph_nodes (id TEXT PRIMARY KEY, graph_type TEXT NOT NULL, label TEXT NOT NULL, content TEXT, metadata TEXT, created_at TEXT)"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS graph_edges (source_id TEXT NOT NULL, target_id TEXT NOT NULL, relation_type TEXT NOT NULL, weight REAL DEFAULT 0.5, metadata TEXT, PRIMARY KEY (source_id, target_id, relation_type))"""
            )
            conn.commit()
        finally:
            conn.close()

    def add_node(self, node: GraphNode) -> None:
        self.nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []

    def add_edge(self, edge: GraphEdge) -> None:
        self.edges.append(edge)
        if edge.source_id in self._adjacency:
            self._adjacency[edge.source_id].append(
                (edge.target_id, edge.relation_type, edge.weight)
            )

    def get_neighbors(
        self,
        node_id: str,
        relation_type: RelationType | None = None,
        min_weight: float = 0.0,
    ) -> list[tuple[str, RelationType, float]]:
        neighbors = self._adjacency.get(node_id, [])
        if relation_type:
            neighbors = [(t, r, w) for t, r, w in neighbors if r == relation_type]
        if min_weight > 0:
            neighbors = [(t, r, w) for t, r, w in neighbors if w >= min_weight]
        return neighbors

    def get_stats(self) -> dict[str, Any]:
        relation_counts: dict[str, int] = {}
        for edge in self.edges:
            rel = edge.relation_type.value
            relation_counts[rel] = relation_counts.get(rel, 0) + 1
        return {
            "graph_type": self.graph_type.value,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "relation_types": relation_counts,
        }


class MultiGraphMemory:
    """MAGMA-style multi-graph memory system."""

    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or Path(".sisyphus/graphs.db")
        self.graphs = {
            GraphType.SEMANTIC: OrthogonalGraph(GraphType.SEMANTIC, self.db_path),
            GraphType.TEMPORAL: OrthogonalGraph(GraphType.TEMPORAL, self.db_path),
            GraphType.CAUSAL: OrthogonalGraph(GraphType.CAUSAL, self.db_path),
            GraphType.ENTITY: OrthogonalGraph(GraphType.ENTITY, self.db_path),
        }

    def add_node(self, node: GraphNode) -> None:
        self.graphs[node.graph_type].add_node(node)

    def add_edge(self, edge: GraphEdge) -> None:
        source_graph = None
        for graph in self.graphs.values():
            if edge.source_id in graph.nodes:
                source_graph = graph
                break
        if source_graph:
            source_graph.add_edge(edge)

    def get_all_stats(self) -> dict[str, Any]:
        return {
            graph_type.value: graph.get_stats()
            for graph_type, graph in self.graphs.items()
        }


# ---------------------------------------------------------------------------
# Graph Store Wrapper
# ---------------------------------------------------------------------------


class GraphStore:
    """Unified graph store interface."""

    def __init__(self):
        self.knowledge_graph = KnowledgeGraph()
        self.multi_graph = MultiGraphMemory()

    def add_node(self, node_id: str, node_type: str, properties: dict = None):
        self.knowledge_graph.add_node(node_id, node_type, properties)

    def add_edge(
        self, source: str, target: str, relation: str, properties: dict = None
    ):
        self.knowledge_graph.add_edge(source, target, relation, properties)

    def search(self, query: str) -> List[Dict]:
        return self.knowledge_graph.search(query)

    def get_stats(self) -> Dict:
        return {
            "knowledge_graph": self.knowledge_graph.get_stats(),
            "multi_graph": self.multi_graph.get_all_stats(),
        }


__all__ = [
    "GraphStore",
    "KnowledgeGraph",
    "MultiGraphMemory",
    "GraphNode",
    "GraphEdge",
    "GraphPath",
    "GraphType",
    "RelationType",
]
