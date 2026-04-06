"""N-Xyme Security Agent - Command validation and security analysis service.

This package provides FastAPI endpoints for analyzing shell commands
for potential security risks using rule-based and AI-based analysis.
"""

from .main import app
from .service import (
    check_whitelist,
    check_blacklist,
    check_sensitive,
    analyze_with_ollama,
    get_cached,
    store_feedback,
    Decision,
)

__all__ = [
    "app",
    "check_whitelist",
    "check_blacklist",
    "check_sensitive",
    "analyze_with_ollama",
    "get_cached",
    "store_feedback",
    "Decision",
]
__version__ = "1.0.0"
