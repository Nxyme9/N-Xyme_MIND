"""Knowledge tab - knowledge graph visualization."""

# Import from parent module
_safe_json = None


def init(safe_json):
    global _safe_json
    _safe_json = safe_json


def get_content() -> str:
    content = "═══ KNOWLEDGE GRAPH ═══\n\n"

    # Load from cross-session knowledge
    knowledge = _safe_json(".sisyphus/cross_session/knowledge.json")

    if not knowledge:
        # Try to get from memory
        try:
            from src.memory.mcp_server import get_memory_stats

            mem_stats = get_memory_stats()
            entities = mem_stats.get("entities", [])
            relations = mem_stats.get("relations", [])
        except (ImportError, AttributeError, OSError):
            entities = []
            relations = []

        if not entities:
            content += "  No knowledge graph data available\n\n"
            content += "  Entities will appear as system learns from interactions.\n"
            return content

    entities = knowledge.get("entities", [])
    relations = knowledge.get("relations", [])

    # Show entity summary
    content += f"  Entities: {len(entities)}\n"
    content += f"  Relations: {len(relations)}\n\n"

    # Show sample entities
    if entities:
        content += "▸ TOP ENTITIES\n"
        for e in entities[:8]:
            name = e.get("name", "?")
            etype = e.get("type", "unknown")
            content += f"  [{etype}] {name}\n"

    # Show agent relationships
    content += "\n▸ AGENT DELEGATION\n"
    content += "  Sisyphus → Hephaestus (implementation)\n"
    content += "  Sisyphus → Oracle (review)\n"
    content += "  Sisyphus → Explore (search)\n"
    content += "  Sisyphus → Librarian (research)\n"

    content += "\n▸ KEYBOARD SHORTCUTS\n"
    content += "  K: Knowledge tab  L: Costs tab  M: Activity feed\n"

    return content
