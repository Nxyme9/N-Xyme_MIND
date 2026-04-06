"""Multi-Graph Architecture — MAGMA-inspired orthogonal graph reasoning.

Based on MAGMA (Multi-Graph Agentic Memory, UT Dallas, arXiv:2601.03236).

Architecture: 4 orthogonal graphs with policy-guided traversal.
- Semantic Graph: Concept relationships, topic clustering
- Temporal Graph: Event timelines, session sequences
- Causal Graph: Cause-effect relationships, decision chains
- Entity Graph: Projects, technologies, people, files

Key innovations:
1. Decouples memory representation from retrieval logic
2. Query-adaptive graph selection (different queries traverse different graphs)
3. Transparent reasoning paths — you can see which graph contributed
4. Outperforms SOTA on LoCoMo and LongMemEval
"""

from __future__ import annotations

import json
import logging
import sqlite3
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class GraphType(str, Enum):
    """Types of orthogonal graphs."""

    SEMANTIC = "semantic"  # Concept relationships
    TEMPORAL = "temporal"  # Event timelines
    CAUSAL = "causal"  # Cause-effect chains
    ENTITY = "entity"  # Projects, tech, people, files


class RelationType(str, Enum):
    """Types of relationships between nodes."""

    # Semantic relations
    RELATED_TO = "related_to"
    SIMILAR_TO = "similar_to"
    PART_OF = "part_of"
    # Temporal relations
    BEFORE = "before"
    AFTER = "after"
    DURING = "during"
    # Causal relations
    CAUSES = "causes"
    ENABLES = "enables"
    PREVENTS = "prevents"
    # Entity relations
    USES = "uses"
    DEPENDS_ON = "depends_on"
    CONTAINS = "contains"
    IMPLEMENTS = "implements"
    OWNS = "owns"


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
    """A path through the graph (multi-hop traversal result)."""

    nodes: list[GraphNode]
    edges: list[GraphEdge]
    total_weight: float
    graph_type: GraphType
    hops: int

    @property
    def path_description(self) -> str:
        """Human-readable path description."""
        if not self.nodes:
            return "Empty path"
        parts = [self.nodes[0].label]
        for i, edge in enumerate(self.edges):
            parts.append(f"--[{edge.relation_type.value}]-->")
            if i + 1 < len(self.nodes):
                parts.append(self.nodes[i + 1].label)
        return " ".join(parts)


class OrthogonalGraph:
    """A single orthogonal graph (semantic, temporal, causal, or entity)."""

    def __init__(self, graph_type: GraphType, db_path: Path | None = None):
        """Initialize orthogonal graph.

        Args:
            graph_type: Type of this graph.
            db_path: Path to the database.
        """
        self.graph_type = graph_type
        self.db_path = db_path or Path(".sisyphus/graphs.db")
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []
        self._adjacency: dict[str, list[tuple[str, RelationType, float]]] = {}
        self._ensure_tables()
        self._load_graph()

    def _ensure_tables(self) -> None:
        """Create graph tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_nodes (
                    id TEXT PRIMARY KEY,
                    graph_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    content TEXT,
                    metadata TEXT,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS graph_edges (
                    source_id TEXT NOT NULL,
                    target_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    weight REAL DEFAULT 0.5,
                    metadata TEXT,
                    PRIMARY KEY (source_id, target_id, relation_type)
                )
                """
            )
            conn.commit()
        finally:
            conn.close()

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the graph."""
        self.nodes[node.id] = node
        if node.id not in self._adjacency:
            self._adjacency[node.id] = []
        self._save_node(node)

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to the graph."""
        self.edges.append(edge)
        # Update adjacency list
        if edge.source_id in self._adjacency:
            self._adjacency[edge.source_id].append(
                (edge.target_id, edge.relation_type, edge.weight)
            )
        self._save_edge(edge)

    def get_neighbors(
        self,
        node_id: str,
        relation_type: RelationType | None = None,
        min_weight: float = 0.0,
    ) -> list[tuple[str, RelationType, float]]:
        """Get neighbors of a node."""
        neighbors = self._adjacency.get(node_id, [])
        if relation_type:
            neighbors = [(t, r, w) for t, r, w in neighbors if r == relation_type]
        if min_weight > 0:
            neighbors = [(t, r, w) for t, r, w in neighbors if w >= min_weight]
        return neighbors

    def bfs_traversal(
        self,
        seed_node_id: str,
        max_hops: int = 3,
        min_edge_weight: float = 0.3,
        relation_types: list[RelationType] | None = None,
    ) -> list[GraphPath]:
        """BFS traversal with semantic edge scoring.

        Args:
            seed_node_id: Starting node.
            max_hops: Maximum number of hops.
            min_edge_weight: Minimum edge weight to traverse.
            relation_types: Filter by relation types (None = all).

        Returns:
            List of GraphPath objects.
        """
        if seed_node_id not in self.nodes:
            return []

        visited = set()
        queue: deque[tuple[str, int, list[str], list[GraphEdge]]] = deque()
        queue.append((seed_node_id, 0, [seed_node_id], []))
        paths: list[GraphPath] = []

        while queue:
            node_id, hop, path_nodes, path_edges = queue.popleft()

            if hop > max_hops or node_id in visited:
                continue
            visited.add(node_id)

            neighbors = self.get_neighbors(node_id, min_weight=min_edge_weight)
            for target_id, rel_type, weight in neighbors:
                if relation_types and rel_type not in relation_types:
                    continue
                if target_id in visited:
                    continue

                new_path_nodes = path_nodes + [target_id]
                edge = GraphEdge(
                    source_id=node_id,
                    target_id=target_id,
                    relation_type=rel_type,
                    weight=weight,
                )
                new_path_edges = path_edges + [edge]

                # Create path object
                path_nodes_obj = [
                    self.nodes[nid] for nid in new_path_nodes if nid in self.nodes
                ]
                if path_nodes_obj:
                    total_weight = sum(e.weight for e in new_path_edges) / max(
                        1, len(new_path_edges)
                    )
                    paths.append(
                        GraphPath(
                            nodes=path_nodes_obj,
                            edges=new_path_edges,
                            total_weight=round(total_weight, 4),
                            graph_type=self.graph_type,
                            hops=hop + 1,
                        )
                    )

                queue.append((target_id, hop + 1, new_path_nodes, new_path_edges))

        return paths

    def _save_node(self, node: GraphNode) -> None:
        """Save node to database."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO graph_nodes
                (id, graph_type, label, content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    node.id,
                    node.graph_type.value,
                    node.label,
                    node.content,
                    json.dumps(node.metadata),
                    node.created_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _save_edge(self, edge: GraphEdge) -> None:
        """Save edge to database."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO graph_edges
                (source_id, target_id, relation_type, weight, metadata)
                VALUES (?, ?, ?, ?, ?)
                """,
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

    def _load_graph(self) -> None:
        """Load graph from database."""
        if not self.db_path.exists():
            return

        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            # Load nodes
            cursor = conn.execute(
                "SELECT * FROM graph_nodes WHERE graph_type = ?",
                (self.graph_type.value,),
            )
            for row in cursor.fetchall():
                node = GraphNode(
                    id=row["id"],
                    graph_type=self.graph_type,
                    label=row["label"],
                    content=row["content"] or "",
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                    created_at=row["created_at"] or "",
                )
                self.nodes[node.id] = node
                if node.id not in self._adjacency:
                    self._adjacency[node.id] = []

            # Load edges
            cursor = conn.execute("SELECT * FROM graph_edges")
            for row in cursor.fetchall():
                edge = GraphEdge(
                    source_id=row["source_id"],
                    target_id=row["target_id"],
                    relation_type=RelationType(row["relation_type"]),
                    weight=row["weight"],
                    metadata=json.loads(row["metadata"]) if row["metadata"] else {},
                )
                self.edges.append(edge)
                if edge.source_id in self._adjacency:
                    self._adjacency[edge.source_id].append(
                        (edge.target_id, edge.relation_type, edge.weight)
                    )
        finally:
            conn.close()

    def get_stats(self) -> dict[str, Any]:
        """Get graph statistics."""
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
    """MAGMA-style multi-graph memory system.

    Manages 4 orthogonal graphs with policy-guided traversal.
    """

    def __init__(self, db_path: Path | None = None):
        """Initialize multi-graph memory.

        Args:
            db_path: Path to the database.
        """
        self.db_path = db_path or Path(".sisyphus/graphs.db")
        self.graphs = {
            GraphType.SEMANTIC: OrthogonalGraph(GraphType.SEMANTIC, self.db_path),
            GraphType.TEMPORAL: OrthogonalGraph(GraphType.TEMPORAL, self.db_path),
            GraphType.CAUSAL: OrthogonalGraph(GraphType.CAUSAL, self.db_path),
            GraphType.ENTITY: OrthogonalGraph(GraphType.ENTITY, self.db_path),
        }

    def add_node(self, node: GraphNode) -> None:
        """Add a node to the appropriate graph."""
        self.graphs[node.graph_type].add_node(node)

    def add_edge(self, edge: GraphEdge) -> None:
        """Add an edge to all relevant graphs."""
        # Edges can span graphs, but we store them in the source node's graph
        source_graph = None
        for graph in self.graphs.values():
            if edge.source_id in graph.nodes:
                source_graph = graph
                break
        if source_graph:
            source_graph.add_edge(edge)

    def multi_hop_query(
        self,
        seed_node_id: str,
        max_hops: int = 3,
        min_edge_weight: float = 0.3,
        graph_types: list[GraphType] | None = None,
        relation_types: list[RelationType] | None = None,
    ) -> list[GraphPath]:
        """Multi-hop query across specified graphs.

        Args:
            seed_node_id: Starting node ID.
            max_hops: Maximum hops.
            min_edge_weight: Minimum edge weight.
            graph_types: Graphs to traverse (None = all).
            relation_types: Relation types to follow (None = all).

        Returns:
            List of GraphPath objects, sorted by weight.
        """
        all_paths: list[GraphPath] = []
        graphs_to_search = [self.graphs[gt] for gt in (graph_types or list(GraphType))]

        for graph in graphs_to_search:
            if seed_node_id in graph.nodes:
                paths = graph.bfs_traversal(
                    seed_node_id,
                    max_hops=max_hops,
                    min_edge_weight=min_edge_weight,
                    relation_types=relation_types,
                )
                all_paths.extend(paths)

        # Sort by total weight (highest first)
        all_paths.sort(key=lambda p: p.total_weight, reverse=True)
        return all_paths

    def policy_guided_query(
        self,
        query: str,
        seed_node_id: str,
        max_hops: int = 3,
    ) -> list[GraphPath]:
        """Policy-guided graph selection based on query intent.

        Automatically selects which graph(s) to traverse based on
        the query content.

        Args:
            query: User query.
            seed_node_id: Starting node.
            max_hops: Maximum hops.

        Returns:
            List of GraphPath objects.
        """
        query_lower = query.lower()

        # Determine which graphs to search based on query intent
        graph_types = []

        # Temporal queries
        if any(
            w in query_lower
            for w in ["when", "timeline", "history", "sequence", "before", "after"]
        ):
            graph_types.append(GraphType.TEMPORAL)

        # Causal queries
        if any(
            w in query_lower
            for w in ["why", "cause", "effect", "because", "led to", "result"]
        ):
            graph_types.append(GraphType.CAUSAL)

        # Entity queries
        if any(
            w in query_lower
            for w in ["who", "what project", "what technology", "uses", "depends"]
        ):
            graph_types.append(GraphType.ENTITY)

        # Semantic queries (default)
        if not graph_types or any(
            w in query_lower for w in ["related", "similar", "about", "concept"]
        ):
            graph_types.append(GraphType.SEMANTIC)

        return self.multi_hop_query(
            seed_node_id,
            max_hops=max_hops,
            graph_types=graph_types,
        )

    def get_all_stats(self) -> dict[str, Any]:
        """Get statistics for all graphs."""
        return {
            graph_type.value: graph.get_stats()
            for graph_type, graph in self.graphs.items()
        }


# Global singleton
_multi_graph = MultiGraphMemory()


def add_node(node: GraphNode) -> None:
    """Convenience function to add a node."""
    _multi_graph.add_node(node)


def add_edge(edge: GraphEdge) -> None:
    """Convenience function to add an edge."""
    _multi_graph.add_edge(edge)


def multi_hop_query(
    seed_node_id: str,
    max_hops: int = 3,
    min_edge_weight: float = 0.3,
    graph_types: list[GraphType] | None = None,
) -> list[GraphPath]:
    """Convenience function for multi-hop query."""
    return _multi_graph.multi_hop_query(
        seed_node_id, max_hops, min_edge_weight, graph_types
    )


def policy_guided_query(
    query: str,
    seed_node_id: str,
    max_hops: int = 3,
) -> list[GraphPath]:
    """Convenience function for policy-guided query."""
    return _multi_graph.policy_guided_query(query, seed_node_id, max_hops)
