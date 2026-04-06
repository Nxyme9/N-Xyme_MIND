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

from packages.memory_core.stores.base import GraphStore

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Knowledge Graph (implements GraphStore ABC)
# ---------------------------------------------------------------------------


class KnowledgeGraph(GraphStore):
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

    def add_node(self, id: str, node_type: str, properties: dict = None) -> None:
        """Add a node to the graph (ABC implementation)."""
        self._nodes[id] = {"type": node_type, "properties": properties or {}}
        self._save()

    def add_edge(
        self, source: str, target: str, relation: str, properties: dict | None = None
    ) -> None:
        """Add an edge between two nodes (ABC implementation)."""
        self._edges.append(
            {
                "source": source,
                "target": target,
                "relation": relation,
                "properties": properties or {},
            }
        )
        self._save()

    def get_node(self, id: str) -> dict | None:
        """Get a node by ID (ABC implementation)."""
        return self._nodes.get(id)

    def traverse(self, start_id: str, relation: str, depth: int) -> list[str]:
        """Traverse the graph from a starting node (ABC implementation)."""
        visited: set[str] = set()
        queue = deque([(start_id, 0)])
        results = []

        while queue:
            node_id, current_depth = queue.popleft()
            if node_id in visited or current_depth > depth:
                continue
            visited.add(node_id)

            if current_depth > 0:
                results.append(node_id)

            for edge in self._edges:
                if edge["source"] == node_id and edge["relation"] == relation:
                    if edge["target"] not in visited:
                        queue.append((edge["target"], current_depth + 1))

        return results

    def stats(self) -> dict[str, Any]:
        """Get statistics about the graph store (ABC implementation)."""
        return {"nodes": len(self._nodes), "edges": len(self._edges)}

    # ---------------------------------------------------------------------------
    # Additional Methods (non-ABC)
    # ---------------------------------------------------------------------------

    def query(self, node_id: str) -> Dict:
        """Query a node and its edges."""
        node = self._nodes.get(node_id, {})
        edges = [
            e for e in self._edges if e["source"] == node_id or e["target"] == node_id
        ]
        return {"node": node, "edges": edges}

    def search(self, query: str) -> List[Dict]:
        """Search for nodes matching query."""
        results = []
        for nid, node in self._nodes.items():
            if (
                query.lower() in nid.lower()
                or query.lower() in str(node.get("properties", {})).lower()
            ):
                results.append({"id": nid, **node})
        return results

    def get_stats(self) -> Dict:
        """Get statistics (non-ABC method for compatibility)."""
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
        # Persist edge to SQLite
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """INSERT OR REPLACE INTO graph_edges (source_id, target_id, relation_type, weight, metadata) VALUES (?, ?, ?, ?, ?)""",
                (
                    edge.source_id,
                    edge.target_id,
                    edge.relation_type.value,
                    edge.weight,
                    json.dumps(edge.metadata),
                ),
            )
            conn.commit()
        finally:
            conn.close()

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
    "Neo4jGraphStore",
]


# ---------------------------------------------------------------------------
# Neo4j Backend (Optional)
# ---------------------------------------------------------------------------


class Neo4jGraphStore(GraphStore):
    """Optional Neo4j backend for production deployments.

    Usage:
        store = Neo4jGraphStore("bolt://localhost:7687", "neo4j", "password")
    """

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        try:
            from neo4j import GraphDatabase

            self.driver = GraphDatabase.driver(uri, auth=(user, password))
            self.database = database
            # Verify connection
            with self.driver.session(database=database) as session:
                session.run("RETURN 1")
        except ImportError:
            raise ImportError("neo4j package required: pip install neo4j")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Neo4j: {e}")

    def add_node(self, id: str, node_type: str, properties: dict | None = None) -> None:
        props = properties or {}
        props["id"] = id
        with self.driver.session(database=self.database) as session:
            session.run(
                f"MERGE (n:{node_type} {{id: $id}}) SET n += $props", id=id, props=props
            )

    def add_edge(
        self, source: str, target: str, relation: str, properties: dict | None = None
    ) -> None:
        props = properties or {}
        with self.driver.session(database=self.database) as session:
            session.run(
                """
                MATCH (s {id: $source}), (t {id: $target})
                MERGE (s)-[r:RELATES {type: $relation}]->(t)
                SET r += $props
                """,
                source=source,
                target=target,
                relation=relation,
                props=props,
            )

    def get_node(self, id: str) -> dict | None:
        with self.driver.session(database=self.database) as session:
            result = session.run("MATCH (n {id: $id}) RETURN n", id=id)
            record = result.single()
            if record:
                node = dict(record["n"])
                return node
        return None

    def traverse(self, start_id: str, relation: str, depth: int = 1) -> list[str]:
        with self.driver.session(database=self.database) as session:
            result = session.run(
                """
                MATCH path = (start {id: $start_id})-[r:RELATES*1..$depth]->(end)
                WHERE $relation = '' OR r.type = $relation
                RETURN DISTINCT end.id as id
                """,
                start_id=start_id,
                relation=relation,
                depth=depth,
            )
            return [record["id"] for record in result]

    def stats(self) -> dict[str, Any]:
        with self.driver.session(database=self.database) as session:
            node_count = session.run("MATCH (n) RETURN count(n) as count").single()[
                "count"
            ]
            edge_count = session.run(
                "MATCH ()-[r]->() RETURN count(r) as count"
            ).single()["count"]
            return {"nodes": node_count, "edges": edge_count, "backend": "neo4j"}

    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()

    def __del__(self):
        self.close()
