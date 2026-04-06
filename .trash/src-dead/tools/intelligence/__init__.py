"""Intelligence module — Python equivalents of bash delegation scripts + Phase 3 intelligence features."""

from src.tools.intelligence.complexity_scorer import ComplexityScorer, score_complexity
from src.tools.intelligence.result_checker import ResultChecker, check_results
from src.tools.intelligence.review_triage import ReviewTriage, triage_review
from src.tools.intelligence.delegation_logger import DelegationLogger, log_delegation
from src.tools.intelligence.security_gate import SecurityGate, check_security
from src.tools.intelligence.benchmark import run_benchmark

from src.tools.intelligence.learning import (
    DelegationLearner,
    PatternInsight,
    LearningReport,
    learn_from_delegations,
    get_routing_recommendations,
    generate_learning_report,
)

from src.tools.intelligence.dynamic_scorer import (
    DynamicComplexityScorer,
    DynamicScoreResult,
    MisclassificationRecord,
    score_dynamic,
    create_scorer,
)

from src.tools.intelligence.agent_optimizer import (
    AgentOptimizer,
    AgentScore,
    SelectionResult,
    optimize_agent_selection,
    create_optimizer,
)

from src.tools.intelligence.load_balancer import (
    PredictiveLoadBalancer,
    QueueMetrics,
    LoadPrediction,
    ScalingDecision,
    SheddingDecision,
    create_load_balancer,
)

__all__ = [
    "ComplexityScorer",
    "score_complexity",
    "ResultChecker",
    "check_results",
    "ReviewTriage",
    "triage_review",
    "DelegationLogger",
    "log_delegation",
    "SecurityGate",
    "check_security",
    "run_benchmark",
    "DelegationLearner",
    "PatternInsight",
    "LearningReport",
    "learn_from_delegations",
    "get_routing_recommendations",
    "generate_learning_report",
    "DynamicComplexityScorer",
    "DynamicScoreResult",
    "MisclassificationRecord",
    "score_dynamic",
    "create_scorer",
    "AgentOptimizer",
    "AgentScore",
    "SelectionResult",
    "optimize_agent_selection",
    "create_optimizer",
    "PredictiveLoadBalancer",
    "QueueMetrics",
    "LoadPrediction",
    "ScalingDecision",
    "SheddingDecision",
    "create_load_balancer",
]
