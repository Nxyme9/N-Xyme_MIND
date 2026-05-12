__interface_version__ = "1.0.0"

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from packages.memory_core.retrievers import (
        TEMPRRetriever,
        SemanticRetriever,
        KeywordRetriever,
        rrf_fusion,
    )
    from packages.memory_core.stores import (
        VectorStore,
        GraphStore,
        RelationalStore,
        FileStore,
    )
    from packages.memory_core.sessions import SessionContext, SessionLifecycle
    from packages.memory_core.cognitive import (
        AdaptiveDecay,
        SleepEngine,
        MemoryReconsolidation,
        PriorityEngine,
        TrustAwareRetrieval,
    )


_LAZY_MAPPINGS = {
    "TEMPRRetriever": ("packages.memory_core.retrievers", "TEMPRRetriever"),
    "SemanticRetriever": ("packages.memory_core.retrievers", "SemanticRetriever"),
    "KeywordRetriever": ("packages.memory_core.retrievers", "KeywordRetriever"),
    "rrf_fusion": ("packages.memory_core.retrievers", "rrf_fusion"),
    "VectorStore": ("packages.memory_core.stores", "VectorStore"),
    "GraphStore": ("packages.memory_core.stores", "GraphStore"),
    "RelationalStore": ("packages.memory_core.stores", "RelationalStore"),
    "FileStore": ("packages.memory_core.stores", "FileStore"),
    "KnowledgeGraph": ("packages.memory_core.stores", "KnowledgeGraph"),
    "MultiGraphMemory": ("packages.memory_core.stores", "MultiGraphMemory"),
    "SessionContext": ("packages.memory_core.sessions", "SessionContext"),
    "SessionLifecycle": ("packages.memory_core.sessions", "SessionLifecycle"),
    "AdaptiveDecay": ("packages.memory_core.cognitive", "AdaptiveDecay"),
    "SleepEngine": ("packages.memory_core.cognitive", "SleepEngine"),
    "MemoryReconsolidation": ("packages.memory_core.cognitive", "MemoryReconsolidation"),
    "PriorityEngine": ("packages.memory_core.cognitive", "PriorityEngine"),
    "TrustAwareRetrieval": ("packages.memory_core.cognitive", "TrustAwareRetrieval"),
    "search_memories": ("packages.memory_core.mcp_server", "search_memories"),
    "get_memory_stats": ("packages.memory_core.mcp_server", "get_memory_stats"),
    "recall_session": ("packages.memory_core.mcp_server", "recall_session"),
    "memory_write": ("packages.memory_core.mcp_server", "memory_write"),
    "memory_search": ("packages.memory_core.mcp_server", "memory_search"),
    "find_context": ("packages.memory_core.mcp_server", "find_context"),
    "get_capabilities": ("packages.memory_core.mcp_server", "get_capabilities"),
    "health_check": ("packages.memory_core.mcp_server", "health_check"),
    "mcp_recall": ("packages.memory_core.mcp_server", "recall_session"),
    "search": ("packages.memory_core.mcp_server", "search_memories"),
    "store": ("packages.memory_core.mcp_server", "memory_write"),
    "stats": ("packages.memory_core.mcp_server", "get_memory_stats"),
}


def __getattr__(name: str):
    if name in _LAZY_MAPPINGS:
        import importlib

        mod_path, attr_name = _LAZY_MAPPINGS[name]
        module = importlib.import_module(mod_path, package="packages.memory_core")
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return list(__all__) + list(_LAZY_MAPPINGS.keys())


__all__ = [
    "search",
    "store",
    "stats",
    "health_check",
    "mcp_recall",
    "search_memories",
    "get_memory_stats",
    "recall_session",
    "memory_write",
    "memory_search",
    "find_context",
    "get_capabilities",
    "TEMPRRetriever",
    "SemanticRetriever",
    "KeywordRetriever",
    "rrf_fusion",
    "VectorStore",
    "GraphStore",
    "KnowledgeGraph",
    "MultiGraphMemory",
    "RelationalStore",
    "FileStore",
    "SessionContext",
    "SessionLifecycle",
    "AdaptiveDecay",
    "SleepEngine",
    "MemoryReconsolidation",
    "PriorityEngine",
    "TrustAwareRetrieval",
]
