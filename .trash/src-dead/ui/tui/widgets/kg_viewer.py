#!/usr/bin/env python3
"""
KnowledgeGraphViewer - ASCII visualization of agent/memory knowledge graph

T4.1 from dashboard-v2-plan.md:
- Show entities and relationships
- Display delegation chains
- Visualize memory knowledge graph
"""

from typing import Optional
from textual.reactive import reactive
from textual.widget import Widget


class KnowledgeGraphViewer(Widget):
    """ASCII knowledge graph visualization."""

    # Reactive data
    entities = reactive([])
    relations = reactive([])
    depth = reactive(1)

    def __init__(self, max_depth: int = 3, **kwargs):
        super().__init__(**kwargs)
        self.max_depth = max_depth

    def set_graph(self, entities: list, relations: list) -> None:
        """Set graph data."""
        self.entities = entities
        self.relations = relations
        self.depth = min(len(entities), self.max_depth)
        self.refresh()

    def render(self) -> str:
        """Render ASCII knowledge graph."""
        if not self.entities:
            return "[dim]No graph data[/]"

        lines = ["KNOWLEDGE GRAPH", "═" * 40, ""]

        # Build adjacency from relations
        adj = {}
        for r in self.relations:
            src = r.get("from", "")
            tgt = r.get("to", "")
            rel_type = r.get("type", "relates")
            if src and tgt:
                adj.setdefault(src, []).append((tgt, rel_type))

        # Render tree from first entity as root
        root = self.entities[0].get("name", "Root") if self.entities else "Root"
        lines.extend(self._render_tree(root, adj, [], 0))

        # Summary
        lines.extend(
            [
                "",
                f"Entities: {len(self.entities)} | Relations: {len(self.relations)} | Depth: {self.depth}",
            ]
        )

        return "\n".join(lines)

    def _render_tree(self, node: str, adj: dict, visited: list, indent: int) -> list:
        """Render tree recursively."""
        lines = []
        prefix = "  " * indent

        # Check for cycles
        if node in visited:
            return [f"{prefix}[{node}]] (cycle)"]

        new_visited = visited + [node]

        # Node with icon
        if indent == 0:
            lines.append(f"  [{node}]")
        else:
            connector = "└─►" if indent > 0 else ""
            lines.append(f"{prefix}{connector} [{node}]")

        # Children
        children = adj.get(node, [])
        for i, (child, rel_type) in enumerate(children):
            is_last = i == len(children) - 1
            child_prefix = prefix + ("    " if is_last else "│   ")
            child_lines = self._render_tree(child, adj, new_visited, indent + 1)

            # Add relation type label
            if child_lines:
                rel_label = f"  ({rel_type})"
                if indent > 0:
                    rel_label = f"({rel_type})"
                # Insert after node line
                lines.append(child_lines[0])
                for cl in child_lines[1:]:
                    lines.append(cl)

        return lines


class AgentGraphViewer(Widget):
    """Agent delegation chain visualization (enhanced version)."""

    agents = reactive([])
    depth = reactive(1)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def set_agents(self, agents: list) -> None:
        """Set agent data."""
        self.agents = agents
        self.refresh()

    def render(self) -> str:
        """Render agent delegation chain."""
        if not self.agents:
            return "[dim]No agent data[/]"

        lines = ["AGENT DELEGATION CHAIN", "═" * 40, ""]

        # Find orchestrator (no parent)
        orchestrators = [a for a in self.agents if not a.get("parent")]

        if orchestrators:
            root = orchestrators[0]
            name = root.get("name", "?")
            role = root.get("role", "orchestrate")
            lines.append(f"[{name}]")
            lines.append(f" ({role})")

            # Find children
            children = [a for a in self.agents if a.get("parent") == name]
            for i, child in enumerate(children):
                cname = child.get("name", "?")
                crole = child.get("role", "")
                is_last = i == len(children) - 1
                connector = "└──>" if is_last else "├──>"
                lines.append(f"  {connector} [{cname}]")
                if crole:
                    lines.append(f"       ({crole})")

        # Summary
        active = len([a for a in self.agents if a.get("active", True)])
        lines.extend(
            ["", f"Depth: {self.depth} | Active: {active} | Total: {len(self.agents)}"]
        )

        return "\n".join(lines)
