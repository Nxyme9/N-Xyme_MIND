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
# Neo4j Backend (Optional) - Production Implementation
# ---------------------------------------------------------------------------

import time
from contextlib import contextmanager
from typing import Any, Generator, Optional


class Neo4jGraphStore(GraphStore):
    """Production Neo4j backend for graph storage.

    Features:
    - Connection pooling with configurable pool size
    - Retry logic with exponential backoff
    - Graceful fallback to SQLite if Neo4j unavailable
    - Health check and connection status monitoring
    - Cypher query support for advanced graph traversal

    Usage:
        store = Neo4jGraphStore("bolt://localhost:7687", "neo4j", "password")
        # Or with pool config:
        store = Neo4jGraphStore("bolt://localhost:7687", "neo4j", "password",
                                max_connection_pool_size=50, max_retry_attempts=3)
    """

    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "neo4j",
        database: str = "neo4j",
        max_connection_pool_size: int = 50,
        max_retry_attempts: int = 3,
        retry_initial_delay: float = 0.5,
        connection_timeout: float = 30.0,
    ):
        """Initialize Neo4j graph store.

        Args:
            uri: Neo4j bolt URI
            user: Neo4j username
            password: Neo4j password
            database: Neo4j database name
            max_connection_pool_size: Maximum connections in pool
            max_retry_attempts: Maximum retry attempts for failed operations
            retry_initial_delay: Initial delay for exponential backoff (seconds)
            connection_timeout: Connection timeout in seconds
        """
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.max_connection_pool_size = max_connection_pool_size
        self.max_retry_attempts = max_retry_attempts
        self.retry_initial_delay = retry_initial_delay
        self.connection_timeout = connection_timeout

        self._driver = None
        self._neo4j_available = False
        self._connection_error: Optional[str] = None
        self._fallback_store: Optional["SQLiteGraphStore"] = None

        self._init_driver()

    def _init_driver(self) -> None:
        """Initialize Neo4j driver with connection pooling."""
        try:
            from neo4j import GraphDatabase

            self._driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_pool_size=self.max_connection_pool_size,
                connection_timeout=self.connection_timeout,
            )
            # Verify connection
            with self._driver.session(database=self.database) as session:
                session.run("RETURN 1")
            self._neo4j_available = True
            logger.info(f"Neo4j connected: {self.uri}")
        except ImportError:
            logger.warning("neo4j package not installed, using SQLite fallback")
            self._connection_error = "neo4j package not installed"
            self._init_fallback()
        except Exception as e:
            logger.warning(f"Failed to connect to Neo4j: {e}, using SQLite fallback")
            self._connection_error = str(e)
            self._init_fallback()

    def _init_fallback(self) -> None:
        """Initialize SQLite fallback store."""
        self._fallback_store = SQLiteGraphStore()

    @contextmanager
    def _session(self) -> Generator:
        """Get a Neo4j session with retry logic.

        Yields:
            Neo4j session

        Raises:
            ConnectionError: If Neo4j unavailable after retries
        """
        if not self._neo4j_available:
            raise ConnectionError(
                f"Neo4j unavailable: {self._connection_error}. Use fallback store."
            )

        delay = self.retry_initial_delay
        for attempt in range(self.max_retry_attempts):
            try:
                with self._driver.session(database=self.database) as session:
                    yield session
                return
            except Exception as e:
                if attempt == self.max_retry_attempts - 1:
                    raise ConnectionError(
                        f"Neo4j operation failed after {self.max_retry_attempts} attempts: {e}"
                    )
                logger.warning(
                    f"Neo4j operation failed (attempt {attempt + 1}), retrying in {delay}s: {e}"
                )
                time.sleep(delay)
                delay *= 2  # Exponential backoff

    def _execute_with_retry(self, query: str, **params) -> Any:
        """Execute a Cypher query with retry logic.

        Args:
            query: Cypher query
            **params: Query parameters

        Returns:
            Query result
        """
        with self._session() as session:
            return session.run(query, **params)

    # ---------------------------------------------------------------------------
    # GraphStore ABC Implementation
    # ---------------------------------------------------------------------------

    def add_node(self, id: str, node_type: str, properties: dict | None = None) -> None:
        """Add a node to the graph."""
        if self._fallback_store:
            self._fallback_store.add_node(id, node_type, properties)
            return

        props = properties or {}
        props["id"] = id
        self._execute_with_retry(
            f"MERGE (n:{node_type} {{id: $id}}) SET n += $props", id=id, props=props
        )

    def add_edge(
        self, source: str, target: str, relation: str, properties: dict | None = None
    ) -> None:
        """Add an edge between two nodes."""
        if self._fallback_store:
            self._fallback_store.add_edge(source, target, relation, properties)
            return

        props = properties or {}
        relation_label = relation.upper().replace(" ", "_")
        self._execute_with_retry(
            f"""
            MATCH (s {{id: $source}}), (t {{id: $target}})
            MERGE (s)-[r:{relation_label} {{type: $relation}}]->(t)
            SET r += $props
            """,
            source=source,
            target=target,
            relation=relation,
            props=props,
        )

    def get_node(self, id: str) -> dict | None:
        """Get a node by ID."""
        if self._fallback_store:
            return self._fallback_store.get_node(id)

        result = self._execute_with_retry("MATCH (n {id: $id}) RETURN n", id=id)
        record = result.single()
        if record:
            node_dict = dict(record["n"])
            return {"id": node_dict.pop("id", id), **node_dict}
        return None

    def traverse(self, start_id: str, relation: str, depth: int = 1) -> list[str]:
        """Traverse the graph from a starting node."""
        if self._fallback_store:
            return self._fallback_store.traverse(start_id, relation, depth)

        result = self._execute_with_retry(
            f"""
            MATCH path = (start {{id: $start_id}})-[r:RELATES*1..{depth}]->(end)
            WHERE $relation = '' OR r.type = $relation
            RETURN DISTINCT end.id as id
            """,
            start_id=start_id,
            relation=relation,
        )
        return [record["id"] for record in result]

    def stats(self) -> dict[str, Any]:
        """Get statistics about the graph store."""
        if self._fallback_store:
            stats = self._fallback_store.stats()
            stats["backend"] = "sqlite_fallback"
            return stats

        node_result = self._execute_with_retry("MATCH (n) RETURN count(n) as count")
        node_count = node_result.single()["count"]

        edge_result = self._execute_with_retry(
            "MATCH ()-[r]->() RETURN count(r) as count"
        )
        edge_count = edge_result.single()["count"]

        return {
            "nodes": node_count,
            "edges": edge_count,
            "backend": "neo4j",
            "neo4j_available": self._neo4j_available,
        }

    # ---------------------------------------------------------------------------
    # Additional Methods
    # ---------------------------------------------------------------------------

    def find_connections(
        self,
        node_id: str,
        relation: Optional[str] = None,
        direction: str = "both",
    ) -> list[dict]:
        """Find all connections for a node.

        Args:
            node_id: The node ID to find connections for
            relation: Filter by relation type (optional)
            direction: 'outgoing', 'incoming', or 'both' (default)

        Returns:
            List of connection dicts with source, target, relation, properties
        """
        if self._fallback_store:
            return self._fallback_store.find_connections(node_id, relation, direction)

        if direction == "outgoing":
            cypher = """
                MATCH (s {id: $node_id})-[r]->(t)
                WHERE $relation IS NULL OR r.type = $relation
                RETURN s.id as source, t.id as target, r.type as relation, r as properties
            """
        elif direction == "incoming":
            cypher = """
                MATCH (s)-[r]->(t {id: $node_id})
                WHERE $relation IS NULL OR r.type = $relation
                RETURN s.id as source, t.id as target, r.type as relation, r as properties
            """
        else:  # both
            cypher = """
                MATCH (s {id: $node_id})-[r]->(t)
                WHERE $relation IS NULL OR r.type = $relation
                RETURN s.id as source, t.id as target, r.type as relation, r as properties
                UNION
                MATCH (s)-[r]->(t {id: $node_id})
                WHERE $relation IS NULL OR r.type = $relation
                RETURN s.id as source, t.id as target, r.type as relation, r as properties
            """

        result = self._execute_with_retry(cypher, node_id=node_id, relation=relation)
        connections = []
        for record in result:
            props = dict(record["properties"]) if record["properties"] else {}
            connections.append(
                {
                    "source": record["source"],
                    "target": record["target"],
                    "relation": record["relation"],
                    "properties": props,
                }
            )
        return connections

    def get_subgraph(
        self,
        node_ids: list[str],
        depth: int = 1,
        relation_filter: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get a subgraph containing specified nodes and their neighbors.

        Args:
            node_ids: List of node IDs to include
            depth: Traversal depth from each node
            relation_filter: Filter by relation type (optional)

        Returns:
            Dict with 'nodes' and 'edges' lists
        """
        if self._fallback_store:
            return self._fallback_store.get_subgraph(node_ids, depth, relation_filter)

        # Collect all nodes within depth
        node_ids_param = ",".join(f'"{n}"' for n in node_ids)
        query = f"""
            MATCH path = (start)-[r:RELATES*1..{depth}]-(end)
            WHERE start.id IN [{node_ids_param}]
            """
        if relation_filter:
            query += f" AND r.type = '{relation_filter}'"
        query += """
            RETURN DISTINCT start.id as id, start as node_data
            UNION
            MATCH path = (start)-[r:RELATES*1..{depth}]-(end)
            WHERE end.id IN [{node_ids_param}]
            """
        if relation_filter:
            query += f" AND r.type = '{relation_filter}'"
        query += """
            RETURN DISTINCT end.id as id, end as node_data
        """

        result = self._execute_with_retry(query)
        nodes = []
        for record in result:
            node_dict = dict(record["node_data"])
            node_id = node_dict.pop("id", record["id"])
            nodes.append({"id": node_id, **node_dict})

        # Get edges between collected nodes
        edge_query = f"""
            MATCH (s)-[r]->(t)
            WHERE s.id IN [{node_ids_param}] AND t.id IN [{node_ids_param}]
            """
        if relation_filter:
            edge_query += f" AND r.type = '{relation_filter}'"
        edge_query += " RETURN s.id as source, t.id as target, r.type as relation, r as properties"

        edge_result = self._execute_with_retry(edge_query)
        edges = []
        for record in edge_result:
            props = dict(record["properties"]) if record["properties"] else {}
            edges.append(
                {
                    "source": record["source"],
                    "target": record["target"],
                    "relation": record["relation"],
                    "properties": props,
                }
            )

        return {"nodes": nodes, "edges": edges}

    def execute_cypher(self, query: str, **params) -> list[dict]:
        """Execute a custom Cypher query.

        Args:
            query: Cypher query string
            **params: Query parameters

        Returns:
            List of result records as dicts
        """
        if self._fallback_store:
            raise NotImplementedError(
                "Custom Cypher queries not supported in SQLite fallback"
            )

        result = self._execute_with_retry(query, **params)
        return [dict(record) for record in result]

    def health_check(self) -> dict[str, Any]:
        """Check Neo4j connection health.

        Returns:
            Dict with health status information
        """
        if not self._neo4j_available:
            return {
                "healthy": False,
                "backend": "sqlite_fallback",
                "reason": self._connection_error,
            }

        try:
            with self._driver.session(database=self.database) as session:
                result = session.run("RETURN 1 as health_check")
                if result.single()["health_check"] == 1:
                    return {
                        "healthy": True,
                        "backend": "neo4j",
                        "uri": self.uri,
                        "database": self.database,
                    }
        except Exception as e:
            return {
                "healthy": False,
                "backend": "neo4j",
                "error": str(e),
            }

        return {"healthy": False, "backend": "neo4j", "error": "Unknown error"}

    @property
    def is_connected(self) -> bool:
        """Check if Neo4j is currently connected."""
        return self._neo4j_available and self._driver is not None

    @property
    def connection_status(self) -> dict[str, Any]:
        """Get detailed connection status."""
        return {
            "neo4j_available": self._neo4j_available,
            "connected": self.is_connected,
            "uri": self.uri,
            "database": self.database,
            "error": self._connection_error,
            "using_fallback": self._fallback_store is not None,
        }

    def close(self) -> None:
        """Close the Neo4j driver connection."""
        if self._driver:
            self._driver.close()
            self._driver = None

    def __del__(self):
        """Cleanup on deletion."""
        self.close()


# ---------------------------------------------------------------------------
# SQLite Fallback for Neo4j
# ---------------------------------------------------------------------------


class SQLiteGraphStore(GraphStore):
    """SQLite fallback when Neo4j is unavailable.

    Provides basic graph functionality using SQLite.
    """

    def __init__(self, db_path: str = ".sisyphus/graph_fallback.db"):
        import sqlite3
        from pathlib import Path

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_tables()

    def _ensure_tables(self) -> None:
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                """CREATE TABLE IF NOT EXISTS graph_nodes (
                    id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    properties TEXT DEFAULT '{}'
                )"""
            )
            conn.execute(
                """CREATE TABLE IF NOT EXISTS graph_edges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    target TEXT NOT NULL,
                    relation TEXT NOT NULL,
                    properties TEXT DEFAULT '{}',
                    UNIQUE(source, target, relation)
                )"""
            )
            conn.commit()
        finally:
            conn.close()

    def add_node(self, id: str, node_type: str, properties: dict | None = None) -> None:
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "INSERT OR REPLACE INTO graph_nodes (id, node_type, properties) VALUES (?, ?, ?)",
                (id, node_type, json.dumps(properties or {})),
            )
            conn.commit()
        finally:
            conn.close()

    def add_edge(
        self, source: str, target: str, relation: str, properties: dict | None = None
    ) -> None:
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute(
                "INSERT OR REPLACE INTO graph_edges (source, target, relation, properties) VALUES (?, ?, ?, ?)",
                (source, target, relation, json.dumps(properties or {})),
            )
            conn.commit()
        finally:
            conn.close()

    def get_node(self, id: str) -> dict | None:
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        try:
            cursor = conn.execute(
                "SELECT id, node_type, properties FROM graph_nodes WHERE id = ?", (id,)
            )
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "type": row[1], **json.loads(row[2])}
            return None
        finally:
            conn.close()

    def traverse(self, start_id: str, relation: str, depth: int = 1) -> list[str]:
        import sqlite3
        from collections import deque

        conn = sqlite3.connect(str(self.db_path))
        try:
            visited = set()
            queue = deque([(start_id, 0)])
            results = []

            while queue:
                node_id, current_depth = queue.popleft()
                if node_id in visited or current_depth > depth:
                    continue
                visited.add(node_id)

                if current_depth > 0:
                    results.append(node_id)

                cursor = conn.execute(
                    "SELECT target FROM graph_edges WHERE source = ? AND relation = ?",
                    (node_id, relation),
                )
                for row in cursor:
                    if row[0] not in visited:
                        queue.append((row[0], current_depth + 1))

            return results
        finally:
            conn.close()

    def stats(self) -> dict[str, Any]:
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        try:
            node_cursor = conn.execute("SELECT COUNT(*) FROM graph_nodes")
            node_count = node_cursor.fetchone()[0]

            edge_cursor = conn.execute("SELECT COUNT(*) FROM graph_edges")
            edge_count = edge_cursor.fetchone()[0]

            return {"nodes": node_count, "edges": edge_count, "backend": "sqlite"}
        finally:
            conn.close()

    def find_connections(
        self,
        node_id: str,
        relation: Optional[str] = None,
        direction: str = "both",
    ) -> list[dict]:
        import sqlite3

        conn = sqlite3.connect(str(self.db_path))
        try:
            connections = []

            if direction in ("outgoing", "both"):
                query = "SELECT source, target, relation, properties FROM graph_edges WHERE source = ?"
                params = [node_id]
                if relation:
                    query += " AND relation = ?"
                    params.append(relation)
                cursor = conn.execute(query, params)
                for row in cursor:
                    connections.append(
                        {
                            "source": row[0],
                            "target": row[1],
                            "relation": row[2],
                            "properties": json.loads(row[3]),
                        }
                    )

            if direction in ("incoming", "both"):
                query = "SELECT source, target, relation, properties FROM graph_edges WHERE target = ?"
                params = [node_id]
                if relation:
                    query += " AND relation = ?"
                    params.append(relation)
                cursor = conn.execute(query, params)
                for row in cursor:
                    connections.append(
                        {
                            "source": row[0],
                            "target": row[1],
                            "relation": row[2],
                            "properties": json.loads(row[3]),
                        }
                    )

            return connections
        finally:
            conn.close()

    def get_subgraph(
        self,
        node_ids: list[str],
        depth: int = 1,
        relation_filter: Optional[str] = None,
    ) -> dict[str, Any]:
        import sqlite3
        from collections import deque

        conn = sqlite3.connect(str(self.db_path))
        try:
            visited = set(node_ids)
            queue = deque([(nid, 0) for nid in node_ids])
            all_nodes = set(node_ids)
            all_edges = []

            while queue:
                node_id, current_depth = queue.popleft()
                if current_depth >= depth:
                    continue

                cursor = conn.execute(
                    "SELECT target, relation, properties FROM graph_edges WHERE source = ?",
                    (node_id,),
                )
                for row in cursor:
                    if relation_filter and row[1] != relation_filter:
                        continue
                    all_nodes.add(row[0])
                    all_edges.append(
                        {
                            "source": node_id,
                            "target": row[0],
                            "relation": row[1],
                            "properties": json.loads(row[2]),
                        }
                    )
                    if row[0] not in visited:
                        visited.add(row[0])
                        queue.append((row[0], current_depth + 1))

            # Get node details
            nodes = []
            for nid in all_nodes:
                cursor = conn.execute(
                    "SELECT id, node_type, properties FROM graph_nodes WHERE id = ?",
                    (nid,),
                )
                row = cursor.fetchone()
                if row:
                    nodes.append({"id": row[0], "type": row[1], **json.loads(row[2])})

            return {"nodes": nodes, "edges": all_edges}
        finally:
            conn.close()
