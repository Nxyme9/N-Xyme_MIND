"""
Catalyst — Central wiring layer for N-Xyme Catalyst modules.

Instantiates all modules and wires them together via event bus,
direct references, and shared state.

Usage:
    from catalyst import Catalyst
    app = Catalyst()
    report = app.get_health_report()
"""

import logging
from typing import Optional

from src.orchestration.event_bus import EventBus, get_event_bus
from src.health.health_core import HealthMonitor
from src.health.health_ai import HealthAIDiagnostics
from src.health.health_recovery import HealthRecovery
from src.orchestration.self_healer import SelfHealer, create_catalyst_healer
from src.infrastructure.anomaly_detection import AnomalyDetector, create_catalyst_detector
from src.orchestration.agent_coordinator import AgentCoordinator
from src.orchestration.athena_bridge import AthenaBridge
from src.orchestration.session_memory import SessionMemory, create_session_memory
from src.memory.knowledge_graph import KnowledgeGraph
from src.infrastructure.clipboard_handler import ClipboardHandler, ClipboardContent, ContentType

logger = logging.getLogger(__name__)


class Catalyst:
    """Central wiring layer for all Catalyst modules."""

    def __init__(self):
        # Core infrastructure
        self.event_bus = get_event_bus()

        # Health pipeline
        self.health_monitor = HealthMonitor()
        self.health_ai = HealthAIDiagnostics()
        self.health_recovery = HealthRecovery(self.health_monitor)
        self.health_recovery.set_ai_diagnostics(self.health_ai)

        # Self-healing and anomaly detection
        self.self_healer = create_catalyst_healer()
        self.anomaly_detector = create_catalyst_detector()

        # Wire anomaly -> event_bus -> self_healer
        self.anomaly_detector.wire_event_bus(self.event_bus)
        self.self_healer.wire_event_bus(self.event_bus)

        # Agent coordination
        self.agent_coordinator = AgentCoordinator()

        # Athena bridge (planning -> execution)
        self.athena_bridge = AthenaBridge()
        self.athena_bridge.set_coordinator(self.agent_coordinator)

        # Memory systems
        self.knowledge_graph = KnowledgeGraph()
        self.session_memory = create_session_memory()
        self.session_memory.set_knowledge_graph(self.knowledge_graph)

        # Clipboard handler (detect images, route to vision agent)
        self.clipboard = ClipboardHandler(
            ollama_url="http://localhost:11434",
            vision_model="llava:7b",
        )

        logger.info("Catalyst: All modules wired and ready")

    def get_health_report(self) -> dict:
        """Get full health report with AI diagnostics."""
        statuses = self.health_monitor.check_all()
        report = self.health_monitor.get_full_report()

        # Add AI diagnoses for unhealthy components
        diagnoses = self.health_ai.diagnose_all(statuses)
        report["ai_diagnoses"] = [
            {
                "component": d.component,
                "issue": d.issue,
                "severity": d.severity,
                "suggestion": d.suggestion,
                "auto_fixable": d.auto_fixable,
            }
            for d in diagnoses
        ]

        return report

    def heal_unhealthy(self) -> dict:
        """Heal all unhealthy components."""
        return self.health_recovery.heal_all()

    def get_status(self) -> dict:
        """Get overall system status."""
        return {
            "health": self.health_monitor.get_stats(),
            "anomalies": self.anomaly_detector.get_summary(),
            "self_healer": self.self_healer.get_health_summary(),
            "agents": self.agent_coordinator.get_status(),
            "knowledge_graph": self.knowledge_graph.get_stats(),
            "event_bus": self.event_bus.get_stats(),
        }

    def shutdown(self):
        """Cleanup all modules."""
        self.session_memory.close()
        logger.info("Catalyst: Shutdown complete")
