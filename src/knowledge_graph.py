"""Knowledge Graph — Local knowledge graph"""

import json, logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)


class KnowledgeGraph:
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
            json.dumps({"nodes": self._nodes, "edges": self._edges}, indent=2), encoding="utf-8"
        )

    def add_node(self, node_id: str, node_type: str, properties: dict = None):
        self._nodes[node_id] = {"type": node_type, "properties": properties or {}}
        self._save()

    def add_edge(self, source: str, target: str, relation: str, properties: dict = None):
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
        edges = [e for e in self._edges if e["source"] == node_id or e["target"] == node_id]
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
