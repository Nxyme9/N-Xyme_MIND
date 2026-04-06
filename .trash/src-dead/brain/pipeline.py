#!/usr/bin/env python3
"""BrainPipeline â€” Single class composing all brain modules"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

from brain.router import Router
from brain.evidence import EvidenceCortex
from brain.critic import Critic
from brain.dual_loop import DualLoop
from brain.memory.working import WorkingMemory
from brain.memory.semantic import SemanticMemory
from brain.impasse import ImpasseHandler
from brain.commitment import CommitmentTracker
from brain.local_llm_wrapper import LocalLLMWrapper
from brain.mcp_tool_registry import MCPToolRegistry, get_tools
from infrastructure.circuit_breaker import CircuitBreaker
import logging

logger = logging.getLogger(__name__)
import hashlib
import time
from collections import defaultdict, deque

NL = chr(10)

AGENT_MAPPING = {
    "GPU_WORKER": {"REACTIVE": "sisyphus junior", "DELIBERATIVE": "hephaestus"},
    "SMALL_UTILITY": {"REACTIVE": "sisyphus junior", "DELIBERATIVE": "sisyphus junior"},
    "CRITIC_ONLY": {"REACTIVE": "momus", "DELIBERATIVE": "oracle"},
}


class BrainPipeline:
    def __init__(self, use_local_wrapper: bool = True):
        self.router = Router()
        self.dual_loop = DualLoop()
        self.evidence = EvidenceCortex()
        self.critic = Critic()
        self.working_memory = WorkingMemory()
        self.semantic_memory = SemanticMemory(storage_path="data/semantic_memory.json")
        self.impasse = ImpasseHandler()
        self.commitment = CommitmentTracker()

        # Local LLM wrapper for tool execution with Ollama models
        self.local_llm_wrapper = LocalLLMWrapper()

        # MCP tool registry for accessing available tools
        self.mcp_registry = MCPToolRegistry()
        self._tools = get_tools()
        logger.info(f"BrainPipeline: initialized with {len(self._tools)} MCP tools")

        # Tool wrapper for local models (optional integration)
        self.tool_wrapper = None
        if use_local_wrapper:
            try:
                from tools.learning_tool_wrapper import LearningToolWrapper

                # Lazy init - will be configured when first used
                self.tool_wrapper = None  # Created on first use
                self._local_model_name = "qwen2.5-coder:7b"
                logger.info("BrainPipeline: local tool wrapper available")
            except Exception as e:
                logger.warning(f"Could not init tool wrapper: {e}")

        # Circuit breakers for each agent
        self.breakers = {
            "hephaestus": CircuitBreaker(failure_threshold=5, reset_timeout=120),
            "sisyphus junior": CircuitBreaker(failure_threshold=5, reset_timeout=120),
            "oracle": CircuitBreaker(failure_threshold=5, reset_timeout=120),
            "momus": CircuitBreaker(failure_threshold=5, reset_timeout=120),
            "librarian": CircuitBreaker(failure_threshold=5, reset_timeout=120),
        }

        # Pattern: Result Cache (Cloud CDN)
        self.cache = {}
        self.cache_hits = 0
        self.cache_misses = 0

        # Pattern: Intent Prediction (CPU branch prediction)
        self.intent_history = deque(maxlen=64)
        self.intent_patterns = {}

        # Pattern: Agent Health (Bulkhead isolation)
        self.agent_load = defaultdict(int)
        self.agent_limits = {
            "hephaestus": 2,
            "sisyphus junior": 4,
            "oracle": 1,
            "momus": 2,
            "librarian": 3,
        }

        # Pattern: Attention Memory (NN attention)
        self.memory_weights = defaultdict(float)

        # Pattern: Delta Memory (NN correction)
        self.memory_corrections = {}

    def pre_execute(self, task, intent="UNKNOWN", complexity="MED", risk="LOW"):
        # Pattern: CDN cache - check cache first (verify breaker)
        cached = self._cache_get(task, intent)
        if cached:
            cached_agent = cached.get("agent", "")
            breaker = self.breakers.get(cached_agent)
            if not breaker or breaker.get_state()["state"] != "open":
                return {**cached, "from_cache": True}

        # Pattern: CPU branch prediction — predict intent
        predicted = self._predict_intent(task)
        if predicted != "UNKNOWN":
            intent = predicted

        # Route
        plan = self.router.route(intent, complexity, risk, has_fact_claims=True)
        loop = self.dual_loop.select_loop(task, intent, risk)

        # Pattern: NN attention — relevance-weighted memory recall
        context = self._recall_with_attention(task, top_k=3)

        # Pattern: MoE routing — select agent
        agent = self._select_agent(plan.target, loop.loop_type)

        # Pattern: Cloud bulkhead — check load limit
        if not self._check_bulkhead(agent):
            candidates = self._get_fallback_candidates(plan.target)
            agent = self._select_least_loaded(candidates)

        # Pattern: Circuit breaker — check health
        breaker = self.breakers.get(agent)
        if breaker and breaker.get_state()["state"] == "open":
            agent = self._get_fallback_agent(plan.target)
            context = "[FALLBACK] Using fallback: " + agent

        # Update load tracking
        self.agent_load[agent] += 1

        # Update intent prediction
        self._update_intent_prediction(task, intent)

        result = {
            "agent": agent,
            "plan": plan,
            "loop": loop,
            "context": context,
            "task": task,
        }

        # Check if local model with tool wrapper should be used
        # Detect if task requires tool use (implementation, investigation, research intents)
        tool_intents = {"IMPLEMENTATION", "INVESTIGATION", "RESEARCH", "EXPLORATION"}
        use_local_wrapper = intent in tool_intents and self._tools

        if use_local_wrapper:
            result["use_local_wrapper"] = True
            result["local_tools"] = self._tools
            result["local_model"] = self.local_llm_wrapper.model
            logger.info(
                f"BrainPipeline: local wrapper enabled for task with intent={intent}, tools={len(self._tools)}"
            )

        # Cache the routing decision
        self._cache_set(task, intent, result)

        return result

    def post_execute(self, result, pre_result, max_revisions=2):
        plan = pre_result.get("plan")
        revision_count = 0

        if plan and plan.use_evidence:
            claims = self._classify_result(result)
            if plan.use_critic:
                claim_dicts = self._claims_to_dicts(claims)
                verdict = self.critic.evaluate(claim_dicts)
                while verdict.verdict == "REVISE" and revision_count < max_revisions:
                    revision_count += 1
                    result = self._revise_with_feedback(result, verdict.reasons)
                    claims = self._classify_result(result)
                    claim_dicts = self._claims_to_dicts(claims)
                    verdict = self.critic.evaluate(claim_dicts)
                if verdict.verdict == "BLOCK":
                    # Circuit breaker tracks failure via call() wrapper
                    return {
                        "status": "blocked",
                        "reasons": verdict.reasons,
                        "revisions": revision_count,
                    }

        # Pattern: Delta memory — correct specific memories
        task_key = pre_result.get("task", "")
        if task_key:
            self._delta_update_memory(task_key[:50], result[:200])

        # Decrease load tracking
        agent = pre_result.get("agent", "")
        if agent in self.agent_load:
            self.agent_load[agent] = max(0, self.agent_load[agent] - 1)
        self._track_commitment(pre_result.get("task", ""), success=True)

        # Circuit breaker tracks success/failure via call() wrapper

        return {"status": "success", "result": result, "revisions": revision_count}

    def _select_agent(self, target, loop_type):
        agent = AGENT_MAPPING.get(target, {}).get(loop_type, "sisyphus junior")
        # Check circuit breaker
        breaker = self.breakers.get(agent)
        if breaker and not breaker.get_state()["state"] != "open":
            return self._get_fallback_agent(target)
        return agent

    def _get_fallback_agent(self, target):
        """Get fallback agent when primary is unavailable"""
        fallbacks = {
            "GPU_WORKER": ["oracle", "sisyphus junior", "librarian"],
            "SMALL_UTILITY": ["sisyphus junior", "librarian"],
            "CRITIC_ONLY": ["momus", "oracle"],
        }
        for candidate in fallbacks.get(target, ["sisyphus junior"]):
            breaker = self.breakers.get(candidate)
            if not breaker or breaker.get_state()["state"] != "open":
                return candidate
        return "sisyphus junior"

    def _get_fallback_candidates(self, target):
        """Get all fallback candidates for load balancing"""
        fallbacks = {
            "GPU_WORKER": ["hephaestus", "oracle", "sisyphus junior", "librarian"],
            "SMALL_UTILITY": ["sisyphus junior", "librarian"],
            "CRITIC_ONLY": ["momus", "oracle"],
        }
        return fallbacks.get(target, ["sisyphus junior"])

    def _recall_memory(self, query):
        results = []
        for item in self.working_memory.get_all():
            if query.lower() in item.key.lower() or query.lower() in item.value.lower():
                results.append(item.value)
        concepts = self.semantic_memory.search(query)
        for c in concepts[:2]:
            results.append(c.description)
        if results:
            return NL.join(results[:3])
        return ""

    def _classify_result(self, result):
        sentences = [
            s.strip() for s in result.split(".") if s.strip() and len(s.strip()) > 10
        ]
        return [self.evidence.classify(s) for s in sentences[:10]]

    def _claims_to_dicts(self, claims):
        return [
            {
                "claim_type": c.claim_type,
                "support_status": c.support_status,
                "text": c.text,
            }
            for c in claims
        ]

    def _revise_with_feedback(self, result, reasons):
        return result + NL + NL + "[Revised: " + ", ".join(reasons[:2]) + "]"

    def _store_memory(self, task, result):
        if task:
            self.working_memory.store(task[:50], result[:200])

    def _track_commitment(self, task, success):
        if task:
            cmt = self.commitment.commit(task, "auto")
            self.commitment.record_attempt(cmt.commitment_id, success)

    # ===== PATTERNS FROM HARDWARE/CLOUD =====

    def _cache_key(self, task, intent):
        """Pattern: CDN cache key"""
        return hashlib.md5(f"{task}:{intent}".encode()).hexdigest()

    def _cache_get(self, task, intent):
        """Pattern: Cloud CDN — check cache first"""
        key = self._cache_key(task, intent)
        if key in self.cache:
            self.cache_hits += 1
            return self.cache[key]
        self.cache_misses += 1
        return None

    def _cache_set(self, task, intent, result):
        """Pattern: Cloud CDN — cache result"""
        key = self._cache_key(task, intent)
        self.cache[key] = result
        if len(self.cache) > 200:
            oldest = next(iter(self.cache))
            del self.cache[oldest]

    def _predict_intent(self, task):
        """Pattern: CPU branch prediction — predict intent from history"""
        task_sig = task[:30].lower()
        for length in [8, 4, 2]:
            pattern = tuple(list(self.intent_history)[-length:])
            key = (pattern, task_sig)
            if key in self.intent_patterns:
                return self.intent_patterns[key]
        return "UNKNOWN"

    def _update_intent_prediction(self, task, actual_intent):
        """Pattern: CPU branch prediction — update predictor"""
        task_sig = task[:30].lower()
        pattern = tuple(list(self.intent_history)[-8:])
        self.intent_patterns[(pattern, task_sig)] = actual_intent
        self.intent_history.append(actual_intent)

    def _check_bulkhead(self, agent):
        """Pattern: Cloud bulkhead — check agent load limit"""
        limit = self.agent_limits.get(agent, 2)
        return self.agent_load[agent] < limit

    def _select_least_loaded(self, candidates):
        """Pattern: Cloud load balancing — pick least loaded agent"""
        healthy = [a for a in candidates if self._check_bulkhead(a)]
        if not healthy:
            healthy = ["sisyphus junior"]
        return min(healthy, key=lambda a: self.agent_load[a])

    def _recall_with_attention(self, query, top_k=3):
        """Pattern: NN attention — relevance-weighted memory recall"""
        results = []
        query_words = set(query.lower().split())

        for item in self.working_memory.get_all():
            item_words = set(item.value.lower().split())
            relevance = len(query_words & item_words) / max(len(query_words), 1)
            recency = item.activation
            score = 0.7 * relevance + 0.3 * recency
            results.append((score, item.value, "working"))

        for concept in self.semantic_memory.search(query):
            concept_words = set(concept.description.lower().split())
            relevance = len(query_words & concept_words) / max(len(query_words), 1)
            score = 0.7 * relevance + 0.3 * concept.activation
            results.append((score, concept.description, "semantic"))

        results.sort(reverse=True)
        return chr(10).join([f"[{r[2]}] {r[1]}" for r in results[:top_k]])

    def _delta_update_memory(self, key, new_value, confidence=0.8):
        """Pattern: NN delta rule — correct specific memories"""
        existing = self.working_memory.retrieve(key)
        if existing:
            if existing.value != new_value:
                corrected = existing.value + " [UPDATED: " + new_value + "]"
                self.working_memory.store(key, corrected)
                self.memory_corrections[key] = confidence
        else:
            self.working_memory.store(key, new_value)

    def get_pattern_stats(self):
        """Get statistics for all patterns"""
        return {
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "size": len(self.cache),
            },
            "intent": {
                "history_size": len(self.intent_history),
                "patterns": len(self.intent_patterns),
            },
            "bulkhead": {
                a: f"{self.agent_load[a]}/{self.agent_limits.get(a, 2)}"
                for a in self.agent_limits
            },
            "attention": {"weights": len(self.memory_weights)},
            "delta": {"corrections": len(self.memory_corrections)},
        }
