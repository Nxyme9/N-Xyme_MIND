"""Unified Delegation Router — Orchestrates all routing strategies with fallback chains.

Integrates all intelligence components:
- Trigger-based routing
- Memory-augmented routing
- ML-based predictions
- Skill-based agent matching
- Health-aware routing
- Context sharing
- Task decomposition
- Prompt templates
- A/B testing
- Learning-based optimization (NOW WITH Q-LEARNING + BANDITS!)
- Keyword fallback
"""

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("unified-router")


@dataclass
class RoutingDecision:
    """Final routing decision with provenance."""

    task_description: str
    level: int
    agent: str
    confidence: float
    strategy_used: (
        str  # "trigger", "memory", "ml", "skill", "learning", "q_learning", "keyword"
    )
    reason: str
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    latency_ms: float = 0.0
    subtasks: Optional[List[Dict[str, Any]]] = None
    prompt: Optional[str] = None


class UnifiedDelegationRouter:
    """Orchestrates all routing strategies with proper fallback chains."""

    def __init__(self):
        # Core routing components
        self._memory_router = None
        self._trigger_router = None
        self._local_analyzer = None
        self._routing_optimizer = None
        self._outcome_logger = None
        self._complexity_scorer = None

        # Advanced components
        self._ml_router = None
        self._skill_registry = None
        self._health_monitor = None
        self._context_sharing = None
        self._task_decomposer = None
        self._prompt_templates = None
        self._ab_testing = None
        self._agent_communication = None

        # NEW: Advanced Learning Engine (Q-Learning, Bandits, Meta, EWC, etc.)
        self._advanced_learning = None
        self._ActionType = None

        # NEW: Multi-Reward Router (Thompson Sampling + composite rewards)
        self._multi_reward_router = None

        # NEW: Semantic Task Classifier (Strategy 2.5)
        self._semantic_classifier = None

    def _init_components(self):
        """Lazy initialization of all routing components."""
        # Core components
        if self._memory_router is None:
            try:
                from packages.intelligence.router.memory import get_memory_router

                self._memory_router = get_memory_router()
            except Exception as e:
                logger.warning(f"Memory router unavailable: {e}")

        if self._trigger_router is None:
            try:
                from packages.intelligence.router.trigger import get_trigger_router

                project_root = Path(__file__).parent.parent.parent.parent
                trigger_config = str(
                    project_root / ".sisyphus" / "routing-triggers.json"
                )
                self._trigger_router = get_trigger_router(trigger_config)
            except Exception as e:
                logger.warning(f"Trigger router unavailable: {e}")

        if self._local_analyzer is None:
            try:
                from packages.intelligence.router.local_model import (
                    get_local_analyzer,
                )

                self._local_analyzer = get_local_analyzer()
            except Exception as e:
                logger.warning(f"Local analyzer unavailable: {e}")

        if self._routing_optimizer is None:
            try:
                from packages.learning_engine.routing.optimizer import (
                    get_routing_optimizer,
                )

                self._routing_optimizer = get_routing_optimizer()
            except Exception as e:
                logger.warning(f"Routing optimizer unavailable: {e}")

        if self._outcome_logger is None:
            try:
                from packages.intelligence.delegation.logger import get_outcome_logger

                self._outcome_logger = get_outcome_logger()
            except Exception as e:
                logger.warning(f"Outcome logger unavailable: {e}")

        if self._complexity_scorer is None:
            try:
                from packages.intelligence.scoring.dynamic import DynamicComplexityScorer

                self._complexity_scorer = DynamicComplexityScorer()
            except Exception as e:
                logger.warning(f"Complexity scorer unavailable: {e}")

        # Advanced components
        if self._ml_router is None:
            try:
                from packages.intelligence.router.ml import get_ml_router

                self._ml_router = get_ml_router()
            except Exception as e:
                logger.warning(f"ML router unavailable: {e}")

        if self._skill_registry is None:
            try:
                from packages.intelligence.skill_registry import get_skill_registry

                self._skill_registry = get_skill_registry()
            except Exception as e:
                logger.warning(f"Skill registry unavailable: {e}")

        if self._health_monitor is None:
            try:
                from packages.intelligence.health_monitor import get_health_monitor

                self._health_monitor = get_health_monitor()
            except Exception as e:
                logger.warning(f"Health monitor unavailable: {e}")

        if self._context_sharing is None:
            try:
                from packages.intelligence.delegation.context_sharing import get_context_sharing

                self._context_sharing = get_context_sharing()
            except Exception as e:
                logger.warning(f"Context sharing unavailable: {e}")

        if self._task_decomposer is None:
            try:
                from packages.intelligence.delegation.decomposer import get_task_decomposer

                self._task_decomposer = get_task_decomposer()
            except Exception as e:
                logger.warning(f"Task decomposer unavailable: {e}")

        if self._prompt_templates is None:
            try:
                from packages.intelligence.templates.prompts import (
                    get_prompt_template_library,
                )

                self._prompt_templates = get_prompt_template_library()
            except Exception as e:
                logger.warning(f"Prompt templates unavailable: {e}")

        if self._ab_testing is None:
            try:
                from packages.learning_engine.routing.ab_testing import get_ab_testing

                self._ab_testing = get_ab_testing()
            except Exception as e:
                logger.warning(f"A/B testing unavailable: {e}")

        if self._agent_communication is None:
            try:
                from packages.intelligence.delegation.communication import (
                    get_agent_communication,
                )

                self._agent_communication = get_agent_communication()
            except Exception as e:
                logger.warning(f"Agent communication unavailable: {e}")

        # NEW: Initialize Advanced Learning Engine
        if self._advanced_learning is None:
            try:
                from packages.learning_engine.advanced_learning import AdvancedLearningEngine, ActionType

                self._advanced_learning = AdvancedLearningEngine(
                    db_path="context/memory/learning.db"
                )
                self._ActionType = ActionType
                logger.info("AdvancedLearningEngine connected to UnifiedRouter")
            except Exception as e:
                logger.warning(f"Advanced Learning Engine unavailable: {e}")

        # NEW: Initialize Semantic Task Classifier (Strategy 2.5)
        if self._semantic_classifier is None:
            try:
                from packages.intelligence.router.semantic_classifier import SemanticTaskClassifier

                self._semantic_classifier = SemanticTaskClassifier(db_path=".sisyphus/routing.db")
                logger.info("SemanticTaskClassifier connected to UnifiedRouter")
            except Exception as e:
                logger.warning(f"Semantic Task Classifier unavailable: {e}")

        if self._multi_reward_router is None:
            try:
                from packages.learning_engine.routing.multi_reward_router import MultiRewardRouter
                self._multi_reward_router = MultiRewardRouter(strategy="thompson")
                logger.info("MultiRewardRouter connected to UnifiedRouter")
            except Exception as e:
                logger.warning(f"MultiRewardRouter unavailable: {e}")

    async def route_task(self, task_description: str) -> RoutingDecision:
        """Route a task using all available strategies with fallback chain."""
        start_time = time.time()
        self._init_components()

        alternatives = []
        subtasks = None
        prompt = None

        # Strategy 0: Load shared context
        if self._context_sharing:
            try:
                shared_context = self._context_sharing.get_shared_context()
                if shared_context:
                    logger.debug(
                        f"Loaded shared context: {len(shared_context)} entries"
                    )
            except Exception as e:
                logger.warning(f"Context sharing failed: {e}")

        # Strategy 1: Trigger-based routing (fastest, highest priority)
        if self._trigger_router:
            try:
                trigger_match = self._trigger_router.match_trigger(task_description)
                if trigger_match:
                    routing = self._trigger_router.get_routing_from_trigger(
                        trigger_match
                    )
                    decision = RoutingDecision(
                        task_description=task_description,
                        level=routing.get("recommended_level", 2),
                        agent=routing.get("recommended_agent", "hephaestus"),
                        confidence=trigger_match.confidence,
                        strategy_used="trigger",
                        reason=trigger_match.reason,
                        latency_ms=(time.time() - start_time) * 1000,
                    )
                    logger.info(
                        f"Trigger routing: {decision.agent} (L{decision.level})"
                    )
                    return self._enhance_decision(decision, task_description)
            except Exception as e:
                logger.warning(f"Trigger routing failed: {e}")

        # Strategy 2: ML-based routing
        if self._ml_router:
            try:
                ml_prediction = self._ml_router.predict(task_description)
                if ml_prediction.get("confidence", 0) > 0.6:
                    alternatives.append(
                        {
                            "strategy": "ml",
                            "level": 2,
                            "agent": ml_prediction.get("predicted_agent", "hephaestus"),
                            "confidence": ml_prediction.get("confidence", 0),
                        }
                    )
            except Exception as e:
                logger.warning(f"ML routing failed: {e}")

        # Strategy 2.5: Semantic Classifier (NEW - between ML and Memory)
        if self._semantic_classifier:
            try:
                semantic_result = self._semantic_classifier.classify(task_description)
                if semantic_result.confidence > 0.75:
                    # High confidence - return immediately as PRIMARY strategy
                    decision = RoutingDecision(
                        task_description=task_description,
                        level=semantic_result.predicted_level,
                        agent=semantic_result.predicted_agent,
                        confidence=semantic_result.confidence,
                        strategy_used="semantic_classifier",
                        reason=f"Semantic classifier: {semantic_result.method}, top agents: {semantic_result.top_features}",
                        alternatives=alternatives,
                        latency_ms=(time.time() - start_time) * 1000,
                    )
                    logger.info(
                        f"Semantic classifier routing: {decision.agent} (L{decision.level}, conf={semantic_result.confidence:.2f})"
                    )
                    return self._enhance_decision(decision, task_description)
                else:
                    # Lower confidence - add to alternatives with lower priority
                    alternatives.append(
                        {
                            "strategy": "semantic_classifier",
                            "level": semantic_result.predicted_level,
                            "agent": semantic_result.predicted_agent,
                            "confidence": semantic_result.confidence,
                            "method": semantic_result.method,
                        }
                    )
            except Exception as e:
                logger.warning(f"Semantic classifier routing failed: {e}")

        # Strategy 3: Memory-augmented routing
        if self._memory_router:
            try:
                keyword_level = 2
                if self._complexity_scorer:
                    keyword_level = self._complexity_scorer.score(task_description).level

                recommendation = await self._memory_router.get_routing_recommendation(
                    task_description, keyword_level
                )
                if (
                    not recommendation.fallback_to_keyword
                    and recommendation.confidence > 0.5
                ):
                    alternatives.append(
                        {
                            "strategy": "memory",
                            "level": recommendation.recommended_level,
                            "confidence": recommendation.confidence,
                        }
                    )

                    if recommendation.confidence > 0.7:
                        decision = RoutingDecision(
                            task_description=task_description,
                            level=recommendation.recommended_level,
                            agent="hephaestus",
                            confidence=recommendation.confidence,
                            strategy_used="memory",
                            reason=recommendation.reason,
                            alternatives=alternatives,
                            latency_ms=(time.time() - start_time) * 1000,
                        )
                        logger.info(f"Memory routing: L{decision.level}")
                        return self._enhance_decision(decision, task_description)
            except Exception as e:
                logger.warning(f"Memory routing failed: {e}")

        # Strategy 4: Local model analysis (for L3+ tasks)
        if self._local_analyzer and self._complexity_scorer:
            try:
                keyword_result = self._complexity_scorer.score(task_description)
                if keyword_result.level >= 3:
                    analysis = await self._local_analyzer.analyze_complexity(
                        task_description, keyword_result.level
                    )
                    if not analysis.fallback_to_keyword and analysis.confidence > 0.5:
                        alternatives.append(
                            {
                                "strategy": "local_model",
                                "level": analysis.level,
                                "confidence": analysis.confidence,
                            }
                        )

                        if analysis.confidence > 0.7:
                            decision = RoutingDecision(
                                task_description=task_description,
                                level=analysis.level,
                                agent="hephaestus",
                                confidence=analysis.confidence,
                                strategy_used="local_model",
                                reason=analysis.reason,
                                alternatives=alternatives,
                                latency_ms=(time.time() - start_time) * 1000,
                            )
                            logger.info(f"Local model routing: L{decision.level}")
                            return self._enhance_decision(decision, task_description)
            except Exception as e:
                logger.warning(f"Local model routing failed: {e}")

        # Strategy 5: Advanced Learning (Q-Learning + Bandits) - NEW!
        if self._advanced_learning and self._ActionType:
            try:
                keyword_level = 2
                if self._complexity_scorer:
                    keyword_level = self._complexity_scorer.score(task_description).level

                # Use Q-Learning for action selection
                context = {"level": keyword_level, "strategy": "q_learning"}
                available_actions = list(self._ActionType)

                selected_action, ml_metadata = self._advanced_learning.select_action(
                    task=task_description[:50],
                    context=context,
                    available_actions=available_actions,
                )

                # Map ActionType to agent
                agent = self._map_action_to_agent(selected_action.value)
                uncertainty = ml_metadata.get("uncertainty", 1.0)
                confidence = max(0.3, 1.0 - uncertainty)

                alternatives.append(
                    {
                        "strategy": "q_learning",
                        "level": keyword_level,
                        "agent": agent,
                        "confidence": confidence,
                        "action": selected_action.value,
                        "q_values": ml_metadata.get("q_values", {}),
                    }
                )

                if confidence > 0.6:
                    decision = RoutingDecision(
                        task_description=task_description,
                        level=keyword_level,
                        agent=agent,
                        confidence=confidence,
                        strategy_used="q_learning",
                        reason=f"Q-Learning selected {selected_action.value}, uncertainty={uncertainty:.2f}",
                        alternatives=alternatives,
                        latency_ms=(time.time() - start_time) * 1000,
                    )
                    logger.info(
                        f"Q-Learning routing: {agent} (L{keyword_level}, uncertainty={uncertainty:.2f})"
                    )
                    return self._enhance_decision(decision, task_description)
            except Exception as e:
                logger.warning(f"Q-Learning routing failed: {e}")

        # Strategy 5b: Fallback to simple learning optimizer
        if self._routing_optimizer:
            try:
                keyword_level = 2
                if self._complexity_scorer:
                    keyword_level = self._complexity_scorer.score(task_description).level

                recommendation = self._routing_optimizer.get_optimal_agent(
                    task_description, keyword_level
                )
                if recommendation.confidence > 0.5:
                    alternatives.append(
                        {
                            "strategy": "learning",
                            "agent": recommendation.recommended_agent,
                            "confidence": recommendation.confidence,
                        }
                    )

                    if recommendation.confidence > 0.7:
                        decision = RoutingDecision(
                            task_description=task_description,
                            level=keyword_level,
                            agent=recommendation.recommended_agent,
                            confidence=recommendation.confidence,
                            strategy_used="learning",
                            reason=recommendation.reason,
                            alternatives=alternatives,
                            latency_ms=(time.time() - start_time) * 1000,
                        )
                        logger.info(f"Learning routing: {decision.agent}")
                        return self._enhance_decision(decision, task_description)
            except Exception as e:
                logger.warning(f"Learning routing failed: {e}")

        # Strategy 5c: Multi-Reward Router (Thompson Sampling + composite rewards)
        if self._multi_reward_router:
            try:
                keyword_level = 2
                if self._complexity_scorer:
                    keyword_level = self._complexity_scorer.score(task_description).level

                mr_decision = self._multi_reward_router.route(
                    task_description=task_description,
                    level=keyword_level,
                    context={"strategy": "multi_reward"},
                )

                alternatives.append({
                    "strategy": "multi_reward",
                    "agent": mr_decision.selected_agent,
                    "confidence": mr_decision.confidence,
                    "all_scores": mr_decision.all_scores,
                })

                if mr_decision.confidence > 0.5:
                    decision = RoutingDecision(
                        task_description=task_description,
                        level=keyword_level,
                        agent=mr_decision.selected_agent,
                        confidence=mr_decision.confidence,
                        strategy_used="multi_reward",
                        reason=f"Thompson Sampling: {mr_decision.strategy}, best={mr_decision.selected_agent}",
                        alternatives=alternatives,
                        latency_ms=(time.time() - start_time) * 1000,
                    )
                    logger.info(f"MultiReward routing: {decision.agent}")
                    return self._enhance_decision(decision, task_description)
            except Exception as e:
                logger.warning(f"MultiReward routing failed: {e}")

        # Strategy 6: Keyword-based fallback (always available)
        if self._complexity_scorer:
            try:
                keyword_result = self._complexity_scorer.score(task_description)
                decision = RoutingDecision(
                    task_description=task_description,
                    level=keyword_result.level,
                    agent="hephaestus",
                    confidence=keyword_result.confidence,
                    strategy_used="keyword",
                    reason=keyword_result.reason,
                    alternatives=alternatives,
                    latency_ms=(time.time() - start_time) * 1000,
                )
                logger.info(f"Keyword routing: L{decision.level}")
                return self._enhance_decision(decision, task_description)
            except Exception as e:
                logger.warning(f"Keyword routing failed: {e}")

        # Ultimate fallback
        return RoutingDecision(
            task_description=task_description,
            level=2,
            agent="hephaestus",
            confidence=0.3,
            strategy_used="fallback",
            reason="All routing strategies failed, using default",
            alternatives=alternatives,
            latency_ms=(time.time() - start_time) * 1000,
        )

    def _map_action_to_agent(self, action_value: str) -> str:
        """Map AdvancedLearning ActionType to agent name."""
        mapping = {
            "explore": "explore",
            "delegate": "hephaestus",
            "oracle": "oracle",
            "librarian": "librarian",
            "hephaestus": "hephaestus",
            "multimodal": "multimodal-looker",
        }
        return mapping.get(action_value, "hephaestus")

    def _enhance_decision(
        self, decision: RoutingDecision, task_description: str
    ) -> RoutingDecision:
        """Enhance routing decision with skill matching, health checks, task decomposition, and prompts."""

        # Health check: avoid unhealthy agents
        if self._health_monitor:
            try:
                if not self._health_monitor.is_healthy(decision.agent):
                    healthy_agents = self._health_monitor.get_healthy_agents()
                    if healthy_agents:
                        decision.agent = healthy_agents[0]
                        decision.reason += f" (health fallback to {decision.agent})"
                        logger.info(f"Health fallback: {decision.agent}")
            except Exception as e:
                logger.warning(f"Health check failed: {e}")

        # Skill-based agent matching
        if self._skill_registry:
            try:
                required_skills = self._extract_required_skills(task_description)
                if required_skills:
                    best_agent = self._skill_registry.find_best_agent(required_skills)
                    if best_agent and best_agent != decision.agent:
                        decision.agent = best_agent
                        decision.reason += (
                            f" (skill match: {', '.join(required_skills)})"
                        )
                        logger.info(f"Skill match: {decision.agent}")
            except Exception as e:
                logger.warning(f"Skill matching failed: {e}")

        # Task decomposition for complex tasks
        if self._task_decomposer and decision.level >= 3:
            try:
                plan = self._task_decomposer.decompose_task(task_description)
                if len(plan.subtasks) > 1:
                    decision.subtasks = [
                        {
                            "id": st.id,
                            "description": st.description,
                            "agent": st.agent,
                            "level": st.level,
                        }
                        for st in plan.subtasks
                    ]
                    decision.reason += (
                        f" (decomposed into {len(plan.subtasks)} subtasks)"
                    )
                    logger.info(f"Task decomposed: {len(plan.subtasks)} subtasks")
            except Exception as e:
                logger.warning(f"Task decomposition failed: {e}")

        # Prompt template rendering
        if self._prompt_templates:
            try:
                category = self._get_task_category(task_description)
                template = self._prompt_templates.get_best_template(category)
                if template:
                    decision.prompt = template.render(
                        task_description=task_description,
                        expected_outcome=f"Successful completion of: {task_description}",
                        required_tools="read, edit, bash",
                        must_do="Follow existing patterns, add tests if applicable",
                        must_not_do="Do not break existing functionality",
                        working_directory=str(Path(__file__).parent.parent.parent),
                        existing_patterns="See project codebase",
                        test_location="tests/",
                    )
            except Exception as e:
                logger.warning(f"Prompt template rendering failed: {e}")

        return decision

    def _extract_required_skills(self, task_description: str) -> List[str]:
        """Extract required skills from task description."""
        desc = task_description.lower()
        skills = []

        skill_keywords = {
            "python": ["python", "py"],
            "javascript": ["javascript", "js"],
            "typescript": ["typescript", "ts"],
            "sql": ["sql", "database", "query"],
            "api_design": ["api", "endpoint", "route"],
            "testing": ["test", "unit test", "integration test"],
            "debugging": ["debug", "fix bug", "troubleshoot"],
            "refactoring": ["refactor", "restructure", "reorganize"],
            "system_design": ["architecture", "system design", "design system"],
            "security": ["security", "auth", "authentication", "secur"],
            "performance": ["performance", "optimize", "slow"],
            "documentation": ["document", "docs", "readme"],
        }

        for skill, keywords in skill_keywords.items():
            if any(kw in desc for kw in keywords):
                skills.append(skill)

        return skills

    def _get_task_category(self, task_description: str) -> str:
        """Get task category for prompt template selection."""
        desc = task_description.lower()

        if any(kw in desc for kw in ["fix", "bug", "error", "crash"]):
            return "fix"
        elif any(kw in desc for kw in ["review", "audit", "analyze"]):
            return "review"
        elif any(kw in desc for kw in ["test", "coverage"]):
            return "testing"
        elif any(kw in desc for kw in ["document", "docs", "readme"]):
            return "documentation"
        elif any(kw in desc for kw in ["research", "find", "explore"]):
            return "research"
        else:
            return "implementation"

    async def record_outcome(
        self,
        task_id: str,
        task_description: str,
        level: int,
        agent: str,
        success: bool,
        error: Optional[str] = None,
        latency_ms: float = 0,
        tokens_used: int = 0,
    ) -> None:
        """Record delegation outcome for learning."""
        self._init_components()

        # Log to outcome logger
        if self._outcome_logger:
            try:
                await self._outcome_logger.log_outcome(
                    task_id=task_id,
                    task_description=task_description,
                    level=level,
                    agent=agent,
                    success=success,
                    error=error,
                    latency_ms=latency_ms,
                    tokens_used=tokens_used,
                )
            except Exception as e:
                logger.warning(f"Outcome logging failed: {e}")

        # Update routing weights
        if self._routing_optimizer:
            try:
                self._routing_optimizer.update_weights(
                    agent, level, success, latency_ms
                )
            except Exception as e:
                logger.warning(f"Weight update failed: {e}")

        if self._multi_reward_router:
            try:
                import uuid
                self._multi_reward_router._outcome_logger.log_outcome(
                    task_id=str(uuid.uuid4())[:8],
                    task_description=task_description,
                    level=level,
                    agent=agent,
                    success=success,
                    latency_ms=latency_ms,
                    tokens_used=tokens_used,
                    strategy="multi_reward",
                    confidence=0.7,
                )
            except Exception as e:
                logger.warning(f"MultiReward update failed: {e}")

        # Update Advanced Learning Engine (Q-Learning + Bandits)
        if self._advanced_learning and self._ActionType:
            try:
                action_type = self._map_agent_to_action(agent)
                self._advanced_learning.record_outcome(
                    task=task_description[:50],
                    action=action_type,
                    success=success,
                    latency_ms=latency_ms,
                    cost=0.01,
                    context={"level": level, "strategy": "routing"},
                )
            except Exception as e:
                logger.warning(f"Advanced learning update failed: {e}")

        # NEW: Update Semantic Classifier with online learning
        if self._semantic_classifier:
            try:
                self._semantic_classifier.partial_fit(task_description, agent, success)
                logger.debug(f"Semantic classifier updated with outcome: {agent}")
            except Exception as e:
                logger.warning(f"Semantic classifier update failed: {e}")

        # Record to memory router
        if self._memory_router:
            try:
                await self._memory_router.record_delegation_outcome(
                    task_id=task_id,
                    task_description=task_description,
                    level=level,
                    agent=agent,
                    success=success,
                    error=error,
                    latency_ms=latency_ms,
                    tokens_used=tokens_used,
                )
            except Exception as e:
                logger.warning(f"Memory recording failed: {e}")

        # Update skill registry
        if self._skill_registry:
            try:
                skills = self._extract_required_skills(task_description)
                for skill in skills:
                    self._skill_registry.update_agent_skill(agent, skill, success)
            except Exception as e:
                logger.warning(f"Skill update failed: {e}")

        # Update health monitor
        if self._health_monitor:
            try:
                self._health_monitor.record_check(agent, success, latency_ms, error)
            except Exception as e:
                logger.warning(f"Health recording failed: {e}")

        # Save session context
        if self._context_sharing:
            try:
                self._context_sharing.save_context(
                    session_id="current",
                    context_type="outcome",
                    context_key=f"task_{task_id}",
                    context_value=json.dumps(
                        {
                            "task": task_description,
                            "agent": agent,
                            "success": success,
                            "level": level,
                        }
                    ),
                    priority=1,
                )
            except Exception as e:
                logger.warning(f"Context saving failed: {e}")

    def _map_agent_to_action(self, agent: str):
        """Map agent name to ActionType for ML engine."""
        agent_lower = agent.lower() if agent else ""
        mapping = {
            "explore": self._ActionType.EXPLORE,
            "librarian": self._ActionType.LIBRARIAN,
            "oracle": self._ActionType.ORACLE,
            "hephaestus": self._ActionType.HEPHAESTUS,
            "multimodal-looker": self._ActionType.MULTIMODAL,
            "prometheus": self._ActionType.DELEGATE,
            "metis": self._ActionType.DELEGATE,
            "momus": self._ActionType.DELEGATE,
            "atlas": self._ActionType.DELEGATE,
            "sisyphus-junior": self._ActionType.DELEGATE,
            "sisyphus": self._ActionType.DELEGATE,
        }
        return mapping.get(agent_lower, self._ActionType.DELEGATE)


# Global instance
_unified_router: Optional[UnifiedDelegationRouter] = None


def get_unified_router() -> UnifiedDelegationRouter:
    """Get or create the global unified router."""
    global _unified_router
    if _unified_router is None:
        _unified_router = UnifiedDelegationRouter()
    return _unified_router
