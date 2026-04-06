#!/usr/bin/env python3
"""
Agent Graph - Visualize agent delegation chains

T3.3 from dashboard-v2-plan.md:
- Show delegation depth
- ASCII graph visualization
"""

from typing import Dict, List, Optional, Set


class AgentNode:
    """Represents an agent in the delegation graph."""
    
    def __init__(self, name: str, role: str = "", parent: Optional[str] = None):
        self.name = name
        self.role = role
        self.parent = parent
        self.children: List[str] = []
        self.depth = 0
    
    def __repr__(self):
        return f"AgentNode({self.name}, depth={self.depth})"


class AgentGraph:
    """Build and render agent delegation graph."""
    
    # Default delegation relationships
    DEFAULT_RELATIONSHIPS = {
        "Sisyphus": {"role": "orchestrator", "delegates": ["Hephaestus", "Explore", "Oracle"]},
        "Hephaestus": {"role": "implement", "delegates": []},
        "Explore": {"role": "search", "delegates": []},
        "Oracle": {"role": "review", "delegates": []},
        "Prometheus": {"role": "plan", "delegates": ["Hephaestus"]},
        "Metis": {"role": "analyze", "delegates": []},
        "Momus": {"role": "critic", "delegates": []},
        "Atlas": {"role": "execute", "delegates": []},
    }
    
    def __init__(self):
        self._nodes: Dict[str, AgentNode] = {}
        self._build_default_graph()
    
    def _build_default_graph(self) -> None:
        """Build the default agent graph."""
        for name, info in self.DEFAULT_RELATIONSHIPS.items():
            parent = None
            # Find parent
            for other_name, other_info in self.DEFAULT_RELATIONSHIPS.items():
                if name in other_info.get("delegates", []):
                    parent = other_name
                    break
            
            node = AgentNode(name, info["role"], parent)
            self._nodes[name] = node
            
            # Add children
            for child in info.get("delegates", []):
                if child in self._nodes:
                    self._nodes[child].parent = name
                if child not in self._nodes:
                    self._nodes[child] = AgentNode(child, "", name)
            
            # Update children list
            for child in info.get("delegates", []):
                if child in self._nodes and child not in self._nodes[name].children:
                    self._nodes[name].children.append(child)
        
        # Calculate depths
        self._calculate_depths()
    
    def _calculate_depths(self) -> None:
        """Calculate depth for all nodes."""
        # Find root nodes (no parent)
        roots = [n for n in self._nodes.values() if n.parent is None]
        
        def set_depth(node: AgentNode, depth: int):
            node.depth = depth
            for child_name in node.children:
                if child_name in self._nodes:
                    set_depth(self._nodes[child_name], depth + 1)
        
        for root in roots:
            set_depth(root, 0)
    
    def get_node(self, name: str) -> Optional[AgentNode]:
        """Get a node by name."""
        return self._nodes.get(name)
    
    def get_children(self, name: str) -> List[str]:
        """Get children of a node."""
        node = self._nodes.get(name)
        return node.children if node else []
    
    def get_parent(self, name: str) -> Optional[str]:
        """Get parent of a node."""
        node = self._nodes.get(name)
        return node.parent if node else None
    
    def get_depth(self, name: str) -> int:
        """Get depth of a node."""
        node = self._nodes.get(name)
        return node.depth if node else 0
    
    def get_max_depth(self) -> int:
        """Get maximum depth in the graph."""
        return max(n.depth for n in self._nodes.values()) if self._nodes else 0
    
    def get_all_agents(self) -> List[str]:
        """Get all agent names."""
        return sorted(self._nodes.keys())
    
    def render(self, root: Optional[str] = None, max_depth: Optional[int] = None) -> str:
        """Render the graph as ASCII art."""
        if not self._nodes:
            return "No agents configured"
        
        # Determine starting point
        if root is None:
            # Find roots
            roots = [n for n in self._nodes.values() if n.parent is None]
            if not roots:
                roots = [list(self._nodes.values())[0]]
        else:
            roots = [self._nodes[root]] if root in self._nodes else []
        
        if max_depth is None:
            max_depth = self.get_max_depth()
        
        lines = []
        lines.append("AGENT DELEGATION CHAIN")
        lines.append("═" * 40)
        
        def render_node(node: AgentNode, prefix: str = "", is_last: bool = True):
            # Node representation
            if node.depth == 0:
                lines.append(f"[{node.name}]")
                lines.append(f" ({node.role})" if node.role else "")
            else:
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}[{node.name}]" + (f" ({node.role})" if node.role else ""))
            
            # Children
            children = node.children
            for i, child_name in enumerate(children):
                child = self._nodes.get(child_name)
                if child and (max_depth is None or child.depth <= max_depth):
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    render_node(child, new_prefix, i == len(children) - 1)
        
        for root_node in roots:
            render_node(root_node)
            lines.append("")
        
        # Summary
        lines.append(f"Depth: {self.get_max_depth() + 1} | Active: {len(self._nodes)}")
        
        return "\n".join(lines)


def get_agent_graph() -> str:
    """Quick function to get agent graph."""
    graph = AgentGraph()
    return graph.render()