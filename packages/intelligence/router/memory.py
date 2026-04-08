"""Memory-Augmented Routing — Uses past task outcomes to influence routing decisions."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import numpy as np

logger = logging.getLogger("memory-routing")


@dataclass
class SimilarTask:
    """A similar past task."""
    task_description: str
    level: int
    agent: str
    success: bool
    error: Optional[str] = None
    timestamp: str = ""
    similarity: float = 0.0


@dataclass
class RoutingRecommendation:
    """Memory-influenced routing recommendation."""
    original_level: int
    recommended_level: int
    confidence: float
    reason: str
    similar_tasks: List[SimilarTask] = field(default_factory=list)
    fallback_to_keyword: bool = False


class MemoryAugmentedRouter:
    """Routes tasks using memory of past similar tasks."""

    def __init__(self, memory_search_fn=None, memory_record_fn=None):
        self._memory_search_fn = memory_search_fn
        self._memory_record_fn = memory_record_fn
        self._outcome_cache: Dict[str, List[SimilarTask]] = {}
        self._embedding_cache = None
        self._outcome_embeddings_cache: Dict[str, np.ndarray] = {}
        self._embedding_available = False
        
        # Initialize embedding cache
        self._init_embedding_cache()

        # Auto-wire to outcome logger if no functions provided
        if memory_search_fn is None or memory_record_fn is None:
            try:
                from packages.intelligence.delegation.logger import get_outcome_logger
                outcome_logger = get_outcome_logger()
                if memory_search_fn is None:
                    self._memory_search_fn = lambda query, limit=5: outcome_logger.get_outcomes(limit=limit * 2)
                if memory_record_fn is None:
                    async def _record_wrapper(task_id, task_description, level, agent, success, error=None, latency_ms=0, tokens_used=0):
                        return await outcome_logger.log_outcome(
                            task_id=task_id,
                            task_description=task_description,
                            level=level,
                            agent=agent,
                            success=success,
                            error=error,
                            latency_ms=latency_ms,
                            tokens_used=tokens_used
                        )
                    self._memory_record_fn = _record_wrapper
            except Exception as e:
                logger.warning(f"Failed to wire outcome logger to memory router: {e}")

    def _init_embedding_cache(self) -> None:
        """Initialize embedding cache for semantic search."""
        try:
            from packages.learning_engine.embeddings.model_cache import get_embedding_cache
            self._embedding_cache = get_embedding_cache()
            self._embedding_available = True
            logger.info("Embedding cache initialized for memory router")
        except Exception as e:
            logger.warning(f"Embedding cache not available: {e}. Using keyword fallback.")
            self._embedding_available = False

    def _compute_cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        if emb1 is None or emb2 is None:
            return 0.0
        norm1 = np.linalg.norm(emb1)
        norm2 = np.linalg.norm(emb2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(emb1, emb2) / (norm1 * norm2))

    async def _get_task_embedding(self, task_description: str) -> Optional[np.ndarray]:
        """Get embedding for a task description."""
        if not self._embedding_available or self._embedding_cache is None:
            return None
        try:
            return self._embedding_cache.encode(task_description)
        except Exception as e:
            logger.warning(f"Failed to encode task: {e}")
            return None

    async def _search_by_embedding(self, task_description: str, outcomes: List[Dict], limit: int = 5) -> List[Dict]:
        """Search outcomes by embedding similarity."""
        if not self._embedding_available or not outcomes:
            return []
        
        query_embedding = await self._get_task_embedding(task_description)
        if query_embedding is None:
            return []
        
        # Compute similarities
        scored = []
        for outcome in outcomes:
            try:
                desc = outcome.get("task_description", "")
                if not desc:
                    continue
                
                # Check cache first
                cache_key = f"outcome_{desc[:50]}"
                if cache_key in self._outcome_embeddings_cache:
                    outcome_emb = self._outcome_embeddings_cache[cache_key]
                else:
                    outcome_emb = await self._get_task_embedding(desc)
                    if outcome_emb is not None:
                        self._outcome_embeddings_cache[cache_key] = outcome_emb
                
                if outcome_emb is not None:
                    similarity = self._compute_cosine_similarity(query_embedding, outcome_emb)
                    scored.append((similarity, outcome))
            except Exception as e:
                logger.debug(f"Skipping outcome due to error: {e}")
                continue
        
        # Sort by similarity descending
        scored.sort(key=lambda x: x[0], reverse=True)
        
        # Add similarity scores to outcomes
        results = []
        for sim, outcome in scored[:limit]:
            outcome_copy = outcome.copy()
            outcome_copy["embedding_similarity"] = sim
            results.append(outcome_copy)
        
        return results

    async def query_similar_tasks(self, task_description: str, limit: int = 5) -> List[SimilarTask]:
        """Find similar past tasks from memory using hybrid approach (embedding + keyword)."""
        cache_key = task_description.lower()[:50]
        if cache_key in self._outcome_cache:
            return self._outcome_cache[cache_key]

        try:
            if self._memory_search_fn:
                search_result = self._memory_search_fn(query=f"delegation task: {task_description}", limit=limit * 2)
                if asyncio.iscoroutine(search_result):
                    results = await search_result
                else:
                    results = search_result
                
                # Handle both dict and list return types
                if isinstance(results, dict):
                    outcome_list = results.get("results", [])
                elif isinstance(results, list):
                    outcome_list = results
                else:
                    outcome_list = []
                
                # Try embedding-based search first
                if self._embedding_available and outcome_list:
                    embedded_results = await self._search_by_embedding(task_description, outcome_list, limit)
                    if embedded_results:
                        similar_tasks = []
                        for result in embedded_results:
                            task = self._parse_task_outcome(result)
                            if task:
                                # Use embedding similarity if available
                                emb_sim = result.get("embedding_similarity", 0.0)
                                task.similarity = emb_sim
                                similar_tasks.append(task)
                        self._outcome_cache[cache_key] = similar_tasks[:limit]
                        return similar_tasks[:limit]
                
                # Fallback to keyword-based search (original behavior)
                similar_tasks = []
                for result in outcome_list:
                    task = self._parse_task_outcome(result)
                    if task:
                        similar_tasks.append(task)
                self._outcome_cache[cache_key] = similar_tasks[:limit]
                return similar_tasks[:limit]
            return []
        except Exception as e:
            logger.warning(f"Memory search failed: {e}")
            return []

    async def get_routing_recommendation(self, task_description: str, current_level: int) -> RoutingRecommendation:
        """Get memory-influenced routing recommendation using hybrid approach."""
        try:
            # First try embedding-based classification
            classification = await self.classify_task_by_embedding(task_description)
            use_embedding_fallback = classification.get("fallback", True)
            
            # Get similar tasks
            similar_tasks = await self.query_similar_tasks(task_description)
            if not similar_tasks:
                return RoutingRecommendation(
                    original_level=current_level, recommended_level=current_level,
                    confidence=0.5, reason="No similar tasks found in memory", fallback_to_keyword=True
                )

            success_rate = sum(1 for t in similar_tasks if t.success) / len(similar_tasks)
            
            # Adjust recommendation based on task classification
            task_type = classification.get("classification", "unknown")
            if task_type == "implementation":
                # Implementation tasks benefit from higher confidence
                base_confidence = success_rate + 0.1
            elif task_type == "debug":
                # Debug tasks often need more context
                base_confidence = success_rate + 0.05
            else:
                base_confidence = success_rate
            
            if success_rate < 0.5:
                recommended_level = min(current_level + 1, 5)
                reason = f"Low success rate ({success_rate:.0%}) for similar tasks"
            elif success_rate > 0.8:
                recommended_level = max(current_level - 1, 1)
                reason = f"High success rate ({success_rate:.0%}) for similar tasks"
            else:
                recommended_level = current_level
                reason = f"Moderate success rate ({success_rate:.0%})"

            # Add classification info to reason
            if not use_embedding_fallback:
                reason += f" (classified as {task_type})"
            
            return RoutingRecommendation(
                original_level=current_level, recommended_level=recommended_level,
                confidence=min(base_confidence, 1.0), reason=reason, similar_tasks=similar_tasks[:5],
                fallback_to_keyword=use_embedding_fallback
            )
        except Exception as e:
            logger.warning(f"Routing recommendation failed: {e}")
            return RoutingRecommendation(
                original_level=current_level, recommended_level=current_level,
                confidence=0.3, reason=f"Memory routing failed: {e}", fallback_to_keyword=True
            )

    async def record_delegation_outcome(self, task_id: str, task_description: str, level: int, agent: str, success: bool, error: Optional[str] = None, latency_ms: float = 0, tokens_used: int = 0) -> bool:
        """Record delegation outcome to memory for future learning."""
        try:
            if self._memory_record_fn:
                await self._memory_record_fn(
                    task_id=task_id, task_description=task_description, level=level,
                    agent=agent, success=success, error=error, latency_ms=latency_ms, tokens_used=tokens_used
                )
                self._outcome_cache.clear()
                # Pre-compute and cache embedding for future similarity search
                if self._embedding_available:
                    cache_key = f"outcome_{task_description[:50]}"
                    emb = await self._get_task_embedding(task_description)
                    if emb is not None:
                        self._outcome_embeddings_cache[cache_key] = emb
                return True
            return False
        except Exception as e:
            logger.warning(f"Failed to record outcome: {e}")
            return False

    async def classify_task_by_embedding(self, task_description: str) -> Dict[str, Any]:
        """Classify task type using embedding-based similarity to known patterns."""
        if not self._embedding_available:
            return {"classification": "unknown", "confidence": 0.0, "fallback": True}
        
        try:
            query_embedding = await self._get_task_embedding(task_description)
            if query_embedding is None:
                return {"classification": "unknown", "confidence": 0.0, "fallback": True}
            
            # Known task patterns with their embeddings
            patterns = {
                "implementation": ["write code", "implement feature", "create function", "add handler"],
                "research": ["find", "search", "explore", "lookup", "research"],
                "review": ["review", "verify", "check", "validate", "QA"],
                "debug": ["fix bug", "error", "debug", "issue", "broken"],
                "refactor": ["refactor", "improve", "clean", "optimize"],
                "config": ["configure", "setup", "config", "install"],
            }
            
            best_match = None
            best_similarity = 0.0
            
            for pattern_name, pattern_examples in patterns.items():
                # Get embedding for pattern examples and compute average
                pattern_embeddings = []
                for example in pattern_examples:
                    example_emb = await self._get_task_embedding(example)
                    if example_emb is not None:
                        pattern_embeddings.append(example_emb)
                
                if pattern_embeddings:
                    avg_pattern_emb = np.mean(pattern_embeddings, axis=0)
                    similarity = self._compute_cosine_similarity(query_embedding, avg_pattern_emb)
                    
                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_match = pattern_name
            
            confidence = min(best_similarity, 1.0)
            return {
                "classification": best_match if best_similarity > 0.5 else "unknown",
                "confidence": confidence,
                "fallback": confidence < 0.5
            }
        except Exception as e:
            logger.warning(f"Embedding classification failed: {e}")
            return {"classification": "unknown", "confidence": 0.0, "fallback": True}

    def _parse_task_outcome(self, memory_result: Dict[str, Any]) -> Optional[SimilarTask]:
        """Parse a memory result into a SimilarTask."""
        try:
            metadata = memory_result.get("metadata", {})
            return SimilarTask(
                task_description=metadata.get("task_description", memory_result.get("content", "")),
                level=metadata.get("level", 2), agent=metadata.get("agent", "unknown"),
                success=metadata.get("success", False), error=metadata.get("error"),
                timestamp=metadata.get("timestamp", ""), similarity=memory_result.get("score", 0.0)
            )
        except Exception as e:
            logger.warning(f"Failed to parse task outcome: {e}")
            return None


_memory_router: Optional[MemoryAugmentedRouter] = None

def get_memory_router() -> MemoryAugmentedRouter:
    """Get or create the global memory router."""
    global _memory_router
    if _memory_router is None:
        _memory_router = MemoryAugmentedRouter()
    return _memory_router

def clear_embedding_cache() -> None:
    """Clear cached embeddings (useful for memory refresh)."""
    global _memory_router
    if _memory_router is not None:
        _memory_router._outcome_embeddings_cache.clear()
        logger.info("Embedding cache cleared")
