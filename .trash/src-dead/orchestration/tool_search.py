"""Tool Search — Keyword-based tool discovery and deferred loading."""
from typing import List, Dict, Any, Optional
from .tool_registry import ToolRegistry


class ToolSearcher:
    """Searches and ranks tools by keyword relevance."""
    
    def __init__(self, registry: ToolRegistry):
        self._registry = registry
        self._index: Dict[str, List[str]] = {}  # keyword -> tool names
        self._build_index()
    
    def _build_index(self) -> None:
        """Build keyword index from registered tools."""
        self._index.clear()
        for tool in self._registry.all():
            keywords = self._extract_keywords(tool)
            for keyword in keywords:
                if keyword not in self._index:
                    self._index[keyword] = []
                self._index[keyword].append(tool.name)
    
    def _extract_keywords(self, tool) -> List[str]:
        """Extract searchable keywords from a tool."""
        keywords = []
        
        # Tool name (split by underscores/camelCase)
        import re
        name_parts = re.findall(r'[a-z]+', tool.name.lower())
        keywords.extend(name_parts)
        
        # Description words
        desc = getattr(tool, 'description', '').lower()
        keywords.extend(re.findall(r'[a-z]+', desc))
        
        # Input schema keys
        schema = getattr(tool, 'input_schema', {})
        keywords.extend(schema.keys())
        
        return list(set(keywords))
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search tools by keyword query."""
        import re
        query_keywords = re.findall(r'[a-z]+', query.lower())
        
        # Score tools by keyword matches
        scores: Dict[str, int] = {}
        for tool in self._registry.all():
            score = 0
            tool_keywords = set(self._extract_keywords(tool))
            for keyword in query_keywords:
                if keyword in tool_keywords:
                    score += 1
            if score > 0:
                scores[tool.name] = score
        
        # Sort by score descending
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        
        # Return top results
        results = []
        for name, score in ranked[:limit]:
            tool = self._registry.get(name)
            if tool:
                results.append({
                    'name': tool.name,
                    'description': getattr(tool, 'description', ''),
                    'score': score,
                    'is_read_only': tool.is_read_only({}),
                    'input_schema': getattr(tool, 'input_schema', {}),
                })
        
        return results
    
    def refresh(self) -> None:
        """Rebuild index (call after registering new tools)."""
        self._build_index()


# Global tool searcher (lazy, auto-refreshes on registry size change)
_searcher: Optional[ToolSearcher] = None
_last_registry_size: int = 0

def get_tool_searcher(registry: Optional[ToolRegistry] = None) -> ToolSearcher:
    """Get or create the global tool searcher. Auto-refreshes if registry changed."""
    global _searcher, _last_registry_size
    from .tool_registry import registry as default_registry
    r = registry or default_registry
    
    # Check if registry has changed since last build
    if _searcher is None or len(r) != _last_registry_size:
        _searcher = ToolSearcher(r)
        _last_registry_size = len(r)
    
    return _searcher
_searcher = None

def get_tool_searcher(registry: Optional[ToolRegistry] = None) -> ToolSearcher:
    """Get or create the global tool searcher."""
    global _searcher
    if _searcher is None:
        from .tool_registry import registry as default_registry
        r = registry or default_registry
        _searcher = ToolSearcher(r)
    return _searcher