"""Memory Router — Query routing to optimal retrievers based on query analysis.

Implements:
- Query type detection (semantic vs keyword vs hybrid vs filtered)
- Retriever selection based on query characteristics
- Integration with TEMPRRetriever for hybrid search
- Integration with QLearningEngine for routing decisions
- Graph-based context retrieval via NetworkX
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Query type classification
class QueryType(Enum):
    SEMANTIC = "semantic"  # Natural language, 3+ words
    KEYWORD = "keyword"  # Short, specific terms
    HYBRID = "hybrid"  # Mixed characteristics
    FILTERED = "filtered"  # Has filters dict


# Retriever action types for Q-learning routing
class RetrieverAction(Enum):
    TEMPR = "tempr"  # Hybrid semantic+keyword
    KEYWORD = "keyword"  # FTS5 keyword search
    SEMANTIC = "semantic"  # Vector semantic search
    HINDSIGHT = "hindsight"  # Session-based context retrieval


@dataclass
class UnifiedMemoryQuery:
    query: str
    max_results_per_source: int = 10
    use_semantic: bool = True
    filters: dict = field(default_factory=dict)
    query_type: Optional[QueryType] = None  # Cached after first classification
    rerank: bool = False  # Apply semantic reranking after retrieval


@dataclass
class MemoryResult:
    source: str
    content: Any
    relevance_score: float = 0.0


@dataclass
class SearchResults:
    results: List[MemoryResult]
    total_results: int = 0
    sources_queried: List[str] = field(default_factory=list)
    query_time_ms: float = 0.0


class MemoryRouter:
    """Routes queries to optimal retrievers based on query analysis."""

    def __init__(self, q_learning_db_path: Optional[str] = None):
        """Initialize router with retriever instances.

        Args:
            q_learning_db_path: Optional path to Q-learning DB for routing decisions
        """
        self._tempr_retriever: Optional[Any] = None
        self._keyword_retriever: Optional[Any] = None
        self._semantic_retriever: Optional[Any] = None
        self._hindsight_retriever: Optional[Any] = None
        self._q_learning = None
        self._q_learning_db_path = q_learning_db_path
        self._graph_store = None
        self._use_graph = True
        self._reranker = None

    def _get_graph_store(self):
        """Lazy-load NetworkX graph store."""
        if self._graph_store is None:
            try:
                from .stores.graph_store import get_networkx_graph

                self._graph_store = get_networkx_graph()
                self._use_graph = self._graph_store is not None
            except ImportError as e:
                logger.warning(f"NetworkX graph store not available: {e}")
                self._use_graph = False
                self._graph_store = None
        return self._graph_store

    def query_graph_agent_task_success(
        self, agent_id: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Query graph: Which agents succeeded with similar tasks recently?"""
        if not self._use_graph or self._graph_store is None:
            return []
        try:
            return self._graph_store.query_agent_successes(agent_id, days)
        except Exception as e:
            logger.warning(f"Graph query failed: {e}")
            return []

    def query_graph_similar_tasks(
        self, task_id: str, max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """Query graph for similar tasks."""
        if not self._use_graph or self._graph_store is None:
            return []
        try:
            return self._graph_store.query_similar_tasks(task_id, max_results)
        except Exception as e:
            logger.warning(f"Graph query failed: {e}")
            return []

    def add_graph_context(
        self,
        node_type: str,
        node_id: str,
        label: str = "",
        properties: dict = None,
        outcomes: list = None,
    ) -> bool:
        """Add graph context from search results for learning."""
        if not self._use_graph or self._graph_store is None:
            return False
        try:
            self._graph_store.add_node(node_id, node_type, label, properties)

            if outcomes:
                for outcome in outcomes:
                    outcome_id = f"{node_id}_outcome_{outcome.get('success', False)}"
                    self._graph_store.add_node(
                        outcome_id,
                        "Outcome",
                        outcome.get("label", ""),
                        outcome.get("properties", {}),
                    )
                    self._graph_store.add_edge(
                        node_id,
                        outcome_id,
                        "resulted_in",
                        weight=1.0 if outcome.get("success") else 0.5,
                    )
            return True
        except Exception as e:
            logger.warning(f"Graph add failed: {e}")
            return False

    def get_graph_stats(self) -> Dict[str, Any]:
        """Get graph store statistics."""
        if not self._use_graph or self._graph_store is None:
            return {"available": False}
        try:
            return self._graph_store.get_stats()
        except Exception as e:
            logger.warning(f"Graph stats failed: {e}")
            return {"available": False, "error": str(e)}

    def _get_tempr_retriever(self):
        """Lazy-load TEMPR retriever."""
        if self._tempr_retriever is None:
            from .retrievers.fusion import TEMPRRetriever

            self._tempr_retriever = TEMPRRetriever()
        return self._tempr_retriever

    def _get_keyword_retriever(self):
        """Lazy-load keyword retriever."""
        if self._keyword_retriever is None:
            from .retrievers.keyword import KeywordRetriever

            self._keyword_retriever = KeywordRetriever()
        return self._keyword_retriever

    def _get_semantic_retriever(self):
        """Lazy-load semantic retriever."""
        if self._semantic_retriever is None:
            from .retrievers.semantic import SemanticRetriever

            self._semantic_retriever = SemanticRetriever()
        return self._semantic_retriever

    def _get_hindsight_retriever(self):
        """Lazy-load Hindsight retriever for session queries."""
        if self._hindsight_retriever is None:
            try:
                from .retrievers.hindsight import HindsightRetriever

                self._hindsight_retriever = HindsightRetriever()
            except ImportError as e:
                logger.warning(f"Hindsight retriever not available: {e}")
                self._hindsight_retriever = None
        return self._hindsight_retriever

    def _get_reranker(self):
        """Lazy-load semantic reranker."""
        if self._reranker is None:
            try:
                from .reranker import get_reranker

                self._reranker = get_reranker()
            except ImportError as e:
                logger.warning(f"Reranker not available: {e}")
                self._reranker = None
        return self._reranker

    def _get_q_learning(self):
        """Lazy-load Q-learning engine."""
        if self._q_learning is None:
            try:
                from packages.learning_engine.rl.q_learning import (
                    QLearningEngine,
                    QState,
                )

                self._q_learning = QLearningEngine(db_path=self._q_learning_db_path)
                self._q_state_class = QState
            except ImportError as e:
                logger.warning(f"Q-learning not available: {e}")
                self._q_learning = None
        return self._q_learning

    def _classify_query(self, query: UnifiedMemoryQuery) -> QueryType:
        """Classify query type based on characteristics.

        Args:
            query: The unified memory query

        Returns:
            QueryType classification
        """
        # Return cached classification if available
        if query.query_type is not None:
            return query.query_type

        q = query.query.strip()

        # Check for filters first
        if query.filters and len(query.filters) > 0:
            result = QueryType.FILTERED
            query.query_type = result
            return result

        # Keyword: short query (1-2 words), possibly specific terms
        word_count = len(q.split())
        if word_count <= 2:
            # Short queries are typically keyword searches
            # But check if it looks like natural language
            if len(q) < 20 and not any(c in q for c in "aeiou"):
                result = QueryType.KEYWORD
                query.query_type = result
                return result
            result = QueryType.KEYWORD
            query.query_type = result
            return result

        # Semantic: natural language, 3+ words
        if word_count >= 3:
            # Contains question words or natural language patterns
            if any(
                q.lower().startswith(w)
                for w in ["how", "what", "why", "when", "where", "explain", "find"]
            ):
                result = QueryType.SEMANTIC
                query.query_type = result
                return result
            result = QueryType.SEMANTIC
            query.query_type = result
            return result

    def _select_retriever_actions(
        self, query_type: QueryType, query: UnifiedMemoryQuery
    ) -> List[RetrieverAction]:
        """Select available retriever actions based on query type.

        Args:
            query_type: Classified query type
            query: The unified memory query

        Returns:
            List of viable retriever actions
        """
        if query_type == QueryType.KEYWORD:
            return [RetrieverAction.KEYWORD, RetrieverAction.TEMPR]
        elif query_type == QueryType.FILTERED:
            return [RetrieverAction.TEMPR, RetrieverAction.KEYWORD]
        elif query_type == QueryType.SEMANTIC:
            return [RetrieverAction.TEMPR, RetrieverAction.SEMANTIC]
        else:  # HYBRID or default
            return [
                RetrieverAction.TEMPR,
                RetrieverAction.KEYWORD,
                RetrieverAction.SEMANTIC,
            ]

    def _route_with_q_learning(
        self, query: UnifiedMemoryQuery, available_actions: List[RetrieverAction]
    ) -> RetrieverAction:
        """Use Q-learning to select optimal retriever.

        Args:
            query: The unified memory query
            available_actions: List of viable retriever actions

        Returns:
            Selected retriever action
        """
        ql = self._get_q_learning()
        if ql is None:
            # Default to TEMPR if Q-learning unavailable
            return RetrieverAction.TEMPR

        try:
            # Create state from query characteristics
            context = {
                "query_type": self._classify_query(query).value,
                "query_length": len(query.query),
                "has_filters": bool(query.filters),
                "use_semantic": query.use_semantic,
            }
            state = self._q_state_class.from_context(query.query[:50], context)

            # Select action using epsilon-greedy
            selected = ql.select_action(
                state=state,
                available_actions=[RetrieverAction(a.value) for a in available_actions],
                epsilon=0.1,  # 10% exploration
            )
            return RetrieverAction(selected.value)
        except Exception as e:
            logger.warning(f"Q-learning routing failed: {e}, defaulting to TEMPR")
            return RetrieverAction.TEMPR

    def _execute_search(
        self, retriever_action: RetrieverAction, query: UnifiedMemoryQuery
    ) -> List[dict]:
        """Execute search using specified retriever.

        Args:
            retriever_action: Selected retriever action
            query: The unified memory query

        Returns:
            List of search result dicts
        """
        top_k = query.max_results_per_source
        tier = query.filters.get("tier") if query.filters else None

        try:
            if retriever_action == RetrieverAction.TEMPR:
                retriever = self._get_tempr_retriever()
                return retriever.search(query.query, top_k=top_k, tier=tier)

            elif retriever_action == RetrieverAction.KEYWORD:
                retriever = self._get_keyword_retriever()
                return retriever.search(query.query, top_k=top_k, tier=tier)

            elif retriever_action == RetrieverAction.SEMANTIC:
                retriever = self._get_semantic_retriever()
                return retriever.search(query.query, top_k=top_k, tier=tier)

        except Exception as e:
            logger.error(f"Retriever {retriever_action.value} failed: {e}")
            return []

    def search(self, query: UnifiedMemoryQuery) -> SearchResults:
        """Route and execute search based on query analysis.

        Args:
            query: The unified memory query

        Returns:
            SearchResults with actual data from selected retriever
        """
        start_time = time.time()

        # Step 1: Classify query type
        query_type = self._classify_query(query)
        logger.info(f"Query classified as: {query_type.value}")

        # Step 2: Get available retriever actions
        available_actions = self._select_retriever_actions(query_type, query)

        # Step 3: Route to optimal retriever (with fallback chain)
        selected_action = None
        results: List[dict] = []  # Initialize to avoid unbound variable

        for action in available_actions:
            try:
                # Try Q-learning route if multiple options
                if selected_action is None and len(available_actions) > 1:
                    selected_action = self._route_with_q_learning(
                        query, available_actions
                    )
                elif selected_action is None:
                    selected_action = action

                # Execute search
                results = self._execute_search(selected_action, query)

                if results and len(results) > 0:
                    break  # Success

                # Empty results - try next retriever
                logger.info(
                    f"Retriever {selected_action.value} returned empty, trying next"
                )
                selected_action = action  # Use current action for next retry
                continue

            except Exception as e:
                logger.warning(f"Retriever {action.value} failed: {e}")
                selected_action = None
                continue

        # If all retrievers failed, return empty results
        if not results or len(results) == 0:
            elapsed_ms = (time.time() - start_time) * 1000
            return SearchResults(
                results=[],
                total_results=0,
                sources_queried=["all-failed"],
                query_time_ms=elapsed_ms,
            )

        # Convert dict results to MemoryResult objects
        memory_results = []
        for r in results:
            memory_results.append(
                MemoryResult(
                    source=r.get(
                        "source",
                        selected_action.value if selected_action else "unknown",
                    ),
                    content=r.get("content", ""),
                    relevance_score=r.get("score", 0.0),
                )
            )

        # Step 4: Apply semantic reranking if requested
        if query.rerank and memory_results:
            reranker = self._get_reranker()
            if reranker and reranker.is_available():
                try:
                    # Convert MemoryResult to format expected by reranker

                    reranked = reranker.rerank(
                        query.query,
                        memory_results,
                        top_k=query.max_results_per_source,
                    )
                    # Replace memory_results with reranked results
                    memory_results = []
                    for rr in reranked:
                        mr = MemoryResult(
                            source=rr.source,
                            content=rr.content,
                            relevance_score=rr.rerank_score,
                        )
                        # Preserve reranking metadata
                        mr.rerank_score = rr.rerank_score
                        mr.rank_change = rr.rank_change
                        mr.rerank_metadata = rr.metadata
                        memory_results.append(mr)
                    logger.info(f"Reranked {len(memory_results)} results")
                except Exception as e:
                    logger.warning(f"Reranking failed: {e}, using original order")

        elapsed_ms = (time.time() - start_time) * 1000
        sources = [selected_action.value] if selected_action else ["tempr"]

        return SearchResults(
            results=memory_results,
            total_results=len(memory_results),
            sources_queried=sources,
            query_time_ms=elapsed_ms,
        )


# Preserve backward compatibility - default instance
_default_router: Optional[MemoryRouter] = None


def get_default_router() -> MemoryRouter:
    """Get or create default router instance."""
    global _default_router
    if _default_router is None:
        _default_router = MemoryRouter()
    return _default_router
