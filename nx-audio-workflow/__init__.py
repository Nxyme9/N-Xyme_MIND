"""
N-Xyme Audio Workflow Engine
AI-powered music production workflow system
"""

from .workflow_engine import AudioWorkflowEngine
from .production_templates import ProductionTemplates
from .ai_context import AudioContextSystem

__version__ = "1.0.0"
__author__ = "N-Xyme Team"

__all__ = [
    "AudioWorkflowEngine",
    "ProductionTemplates", 
    "AudioContextSystem"
]


def create_engine(config_path=None):
    """Factory function to create a workflow engine"""
    return AudioWorkflowEngine(config_path)


def quick_start():
    """Quick start helper"""
    engine = AudioWorkflowEngine()
    context = AudioContextSystem()
    templates = ProductionTemplates()
    
    return {
        "engine": engine,
        "context": context,
        "templates": templates
    }
