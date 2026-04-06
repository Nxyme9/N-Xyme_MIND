"""
Memory Interface for N-Xyme MIND Dashboard.

Provides CRUD operations for the knowledge graph using memory MCP tools.
"""

from typing import Optional

# Type definitions
Entity = dict
Relation = dict


class MemoryInterface:
    """
    Interface for interacting with the knowledge graph.

    Provides methods to access and manipulate entities and relations
    in the memory/knowledge graph system.
    """

    def __init__(self):
        """Initialize the memory interface."""
        self._entities: list[Entity] = []
        self._relations: list[Relation] = []
        self._load_initial_data()

    def _load_initial_data(self) -> None:
        """Load initial mock data."""
        self._entities = [
            {
                "name": "Project Alpha",
                "entityType": "project",
                "observations": ["Main development project", "Started 2024"],
            },
            {
                "name": "Memory System",
                "entityType": "system",
                "observations": ["Knowledge graph storage", "MCP integration"],
            },
            {
                "name": "Dashboard",
                "entityType": "component",
                "observations": ["Visualization interface", "Real-time metrics"],
            },
            {
                "name": "Routing System",
                "entityType": "system",
                "observations": ["Task routing", "Agent selection"],
            },
            {
                "name": "Agent Orchestration",
                "entityType": "system",
                "observations": ["Multi-agent coordination", "Sisyphus orchestrator"],
            },
        ]
        self._relations = [
            {"from": "Dashboard", "relationType": "displays", "to": "Memory System"},
            {"from": "Routing System", "relationType": "uses", "to": "Memory System"},
            {
                "from": "Agent Orchestration",
                "relationType": "coordinates",
                "to": "Routing System",
            },
            {"from": "Project Alpha", "relationType": "includes", "to": "Dashboard"},
            {
                "from": "Project Alpha",
                "relationType": "includes",
                "to": "Agent Orchestration",
            },
        ]

    def get_entities(self) -> list[Entity]:
        """
        Get all entities from the knowledge graph.

        Returns:
            List of entity dictionaries with keys: name, entityType, observations
        """
        return self._entities.copy()

    def get_relations(self) -> list[Relation]:
        """
        Get all relations from the knowledge graph.

        Returns:
            List of relation dictionaries with keys: from, relationType, to
        """
        return self._relations.copy()

    def search_entities(self, query: str) -> list[Entity]:
        """
        Search entities by name or query string.

        Args:
            query: Search query string

        Returns:
            List of matching entity dictionaries
        """
        query_lower = query.lower()
        results = []
        for entity in self._entities:
            name = entity.get("name", "").lower()
            entity_type = entity.get("entityType", "").lower()
            if query_lower in name or query_lower in entity_type:
                results.append(entity)
        return results

    def add_entity(self, entity_type: str, name: str, observations: list[str]) -> bool:
        """
        Add a new entity to the knowledge graph.

        Args:
            entity_type: Type of the entity (e.g., 'concept', 'task', 'person')
            name: Name of the entity
            observations: List of observation strings

        Returns:
            True if successful, False otherwise
        """
        # Check if entity already exists
        for e in self._entities:
            if e.get("name") == name:
                return False

        self._entities.append(
            {"name": name, "entityType": entity_type, "observations": observations}
        )
        return True

    def add_relation(
        self, from_entity: str, relation_type: str, to_entity: str
    ) -> bool:
        """
        Add a new relation to the knowledge graph.

        Args:
            from_entity: Source entity name
            relation_type: Type of relation (e.g., 'relates_to', 'depends_on')
            to_entity: Target entity name

        Returns:
            True if successful, False otherwise
        """
        # Verify both entities exist
        entity_names = {e.get("name") for e in self._entities}
        if from_entity not in entity_names or to_entity not in entity_names:
            return False

        self._relations.append(
            {"from": from_entity, "relationType": relation_type, "to": to_entity}
        )
        return True

    def clear_all(self) -> bool:
        """
        Clear all entities and relations from the knowledge graph.

        Returns:
            True if successful, False otherwise
        """
        self._entities.clear()
        self._relations.clear()
        return True


# Singleton instance
_memory_interface: Optional[MemoryInterface] = None


def get_memory_interface() -> MemoryInterface:
    """Get the singleton MemoryInterface instance."""
    global _memory_interface
    if _memory_interface is None:
        _memory_interface = MemoryInterface()
    return _memory_interface
