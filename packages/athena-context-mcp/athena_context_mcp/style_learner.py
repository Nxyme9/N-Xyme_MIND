"""
Style Learner — Tracks user interaction patterns for personalization.

Learns:
- Task types: implementation, research, review, fix
- Delegation patterns: which agents are used most
- Communication style: concise vs verbose, direct vs exploratory
- Time-of-day patterns: when user is most active
- Success patterns: what approaches work best

Usage:
    learner = StyleLearner()
    learner.record_task(task_type="implementation", task_description="add JWT auth")
    learner.record_delegation(agent="hephaestus", success=True, latency_ms=1500)
    learner.record_style(is_verbose=False, is_direct=True)
    style_context = learner.get_style_context()
"""

import logging
import sqlite3
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Default DB path (reuse existing routing.db in project root)
DEFAULT_DB_PATH = ".sisyphus/routing.db"


def _get_project_root() -> Path:
    """Get project root directory."""
    # This file is in packages/athena-context-mcp/athena_context_mcp/
    return Path(__file__).resolve().parent.parent.parent.parent


def _get_db_path(db_path: Optional[str] = None) -> str:
    """Get absolute path to database."""
    if db_path is None:
        project_root = _get_project_root()
        db_path = str(project_root / DEFAULT_DB_PATH)
    elif not Path(db_path).is_absolute():
        # Relative path - make relative to project root
        project_root = _get_project_root()
        db_path = str(project_root / db_path)
    return db_path


@dataclass
class TaskRecord:
    """A recorded user task."""

    task_type: str  # implementation, research, review, fix
    task_description: str
    timestamp: float = field(default_factory=time.time)
    level: int = 0


@dataclass
class DelegationRecord:
    """A recorded delegation event."""

    agent: str
    task_type: str
    success: bool
    latency_ms: float
    tokens_used: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class StyleRecord:
    """A recorded communication style."""

    is_verbose: bool
    is_direct: bool
    message_length: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class UserStyle:
    """Learned user style profile."""

    preferred_task_types: List[str] = field(default_factory=list)
    preferred_agents: List[str] = field(default_factory=list)
    communication_style: str = "balanced"  # concise, verbose, balanced
    communication_directness: str = "balanced"  # direct, exploratory, balanced
    peak_hours: List[int] = field(default_factory=list)  # 0-23 hours
    success_rate: float = 0.5
    avg_latency_ms: float = 0.0


class StyleLearner:
    """Learns user interaction patterns for personalization."""

    def __init__(
        self,
        min_occurrences: int = 3,
        db_path: Optional[str] = None,
    ):
        self.min_occurrences = min_occurrences
        self.db_path = _get_db_path(db_path)
        self._task_history: List[TaskRecord] = []
        self._delegation_history: List[DelegationRecord] = []
        self._style_history: List[StyleRecord] = []
        
        # In-memory aggregations
        self._task_type_counts: Counter = Counter()
        self._agent_counts: Counter = Counter()
        self._hour_counts: Counter = Counter()
        
        # Initialize DB and load existing data
        self._init_db()
        self._load_data()
        
        logger.info(f"StyleLearner: Initialized (db={self.db_path})")

    def _get_connection(self) -> sqlite3.Connection:
        """Get SQLite connection with proper settings."""
        # Ensure db directory exists
        db_path = Path(self.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_db(self) -> None:
        """Initialize SQLite database with style tracking tables."""
        try:
            conn = self._get_connection()
            
            # Task type tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS style_task_types (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_type TEXT NOT NULL,
                    task_description TEXT,
                    level INTEGER,
                    timestamp REAL NOT NULL,
                    day_of_week INTEGER,
                    hour_of_day INTEGER
                )
            """)
            
            # Delegation tracking table (extends outcomes)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS style_delegations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    latency_ms REAL NOT NULL,
                    tokens_used INTEGER DEFAULT 0,
                    timestamp REAL NOT NULL,
                    day_of_week INTEGER,
                    hour_of_day INTEGER
                )
            """)
            
            # Communication style tracking table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS style_communication (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    is_verbose BOOLEAN NOT NULL,
                    is_direct BOOLEAN NOT NULL,
                    message_length INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    day_of_week INTEGER,
                    hour_of_day INTEGER
                )
            """)
            
            # User style profile (aggregated)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_style_profile (
                    id INTEGER PRIMARY KEY,
                    preferred_task_types TEXT,
                    preferred_agents TEXT,
                    communication_style TEXT DEFAULT 'balanced',
                    communication_directness TEXT DEFAULT 'balanced',
                    peak_hours TEXT,
                    success_rate REAL DEFAULT 0.5,
                    avg_latency_ms REAL DEFAULT 0.0,
                    last_updated REAL NOT NULL
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_style_task_types_timestamp ON style_task_types(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_style_delegations_agent ON style_delegations(agent)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_style_delegations_timestamp ON style_delegations(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_style_communication_timestamp ON style_communication(timestamp)")
            
            conn.commit()
            conn.close()
            logger.debug("Initialized style tracking tables")
        except Exception as e:
            logger.error(f"Failed to init style database: {e}")

    def _load_data(self) -> None:
        """Load aggregated data from SQLite."""
        try:
            conn = self._get_connection()
            
            # Load task type counts
            cursor = conn.execute("""
                SELECT task_type, COUNT(*) as cnt 
                FROM style_task_types 
                GROUP BY task_type
            """)
            for row in cursor.fetchall():
                self._task_type_counts[row[0]] = row[1]
            
            # Load agent counts
            cursor = conn.execute("""
                SELECT agent, COUNT(*) as cnt 
                FROM style_delegations 
                GROUP BY agent
            """)
            for row in cursor.fetchall():
                self._agent_counts[row[0]] = row[1]
            
            # Load hour of day distribution
            cursor = conn.execute("""
                SELECT hour_of_day, COUNT(*) as cnt 
                FROM style_task_types 
                WHERE hour_of_day IS NOT NULL
                GROUP BY hour_of_day
            """)
            for row in cursor.fetchall():
                if row[0] is not None:
                    self._hour_counts[row[0]] = row[1]
            
            # Load user style profile
            cursor = conn.execute("SELECT * FROM user_style_profile WHERE id = 1")
            row = cursor.fetchone()
            if row:
                self._profile = {
                    "preferred_task_types": row[1].split("|") if row[1] else [],
                    "preferred_agents": row[2].split("|") if row[2] else [],
                    "communication_style": row[3] or "balanced",
                    "communication_directness": row[4] or "balanced",
                    "peak_hours": [int(h) for h in row[5].split("|")] if row[5] else [],
                    "success_rate": row[6] or 0.5,
                    "avg_latency_ms": row[7] or 0.0,
                }
            else:
                self._profile = None
            
            conn.close()
            logger.info(f"Loaded style data: {len(self._task_type_counts)} task types, {len(self._agent_counts)} agents")
        except Exception as e:
            logger.error(f"Failed to load style data: {e}")

    def record_task(
        self,
        task_type: str,
        task_description: str = "",
        level: int = 1,
    ) -> None:
        """Record a user task.

        Args:
            task_type: Type of task (implementation, research, review, fix)
            task_description: Description of the task
            level: Complexity level (1-5)
        """
        valid_types = {"implementation", "research", "review", "fix"}
        if task_type not in valid_types:
            logger.warning(f"Unknown task_type: {task_type}, skipping")
            return
        
        now = datetime.now()
        ts = time.time()
        
        record = TaskRecord(
            task_type=task_type,
            task_description=task_description,
            timestamp=ts,
            level=level,
        )
        self._task_history.append(record)
        self._task_type_counts[task_type] += 1
        self._hour_counts[now.hour] += 1
        
        # Persist to SQLite
        try:
            conn = self._get_connection()
            conn.execute("""
                INSERT INTO style_task_types 
                (task_type, task_description, level, timestamp, day_of_week, hour_of_day)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                task_type,
                task_description[:500],  # Truncate long descriptions
                level,
                ts,
                now.weekday(),
                now.hour,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to record task: {e}")
        
        # Keep history bounded
        if len(self._task_history) > 1000:
            self._task_history = self._task_history[-500:]
        
        # Update profile
        self._update_profile()

    def record_delegation(
        self,
        agent: str,
        task_type: str = "unknown",
        success: bool = True,
        latency_ms: float = 0.0,
        tokens_used: int = 0,
    ) -> None:
        """Record a delegation event.

        Args:
            agent: Agent name that handled the task
            task_type: Type of task delegated
            success: Whether the task succeeded
            latency_ms: Time taken to complete
            tokens_used: Tokens consumed
        """
        now = datetime.now()
        ts = time.time()
        
        record = DelegationRecord(
            agent=agent,
            task_type=task_type,
            success=success,
            latency_ms=latency_ms,
            tokens_used=tokens_used,
            timestamp=ts,
        )
        self._delegation_history.append(record)
        self._agent_counts[agent] += 1
        
        # Persist to SQLite
        try:
            conn = self._get_connection()
            conn.execute("""
                INSERT INTO style_delegations 
                (agent, task_type, success, latency_ms, tokens_used, timestamp, day_of_week, hour_of_day)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                agent,
                task_type,
                success,
                latency_ms,
                tokens_used,
                ts,
                now.weekday(),
                now.hour,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to record delegation: {e}")
        
        # Keep history bounded
        if len(self._delegation_history) > 1000:
            self._delegation_history = self._delegation_history[-500:]
        
        # Update profile
        self._update_profile()

    def record_style(
        self,
        is_verbose: bool,
        is_direct: bool,
        message_length: int = 0,
    ) -> None:
        """Record communication style.

        Args:
            is_verbose: Whether message is verbose (longer, more explanation)
            is_direct: Whether message is direct (short, action-oriented)
            message_length: Character count of message
        """
        now = datetime.now()
        ts = time.time()
        
        record = StyleRecord(
            is_verbose=is_verbose,
            is_direct=is_direct,
            message_length=message_length,
            timestamp=ts,
        )
        self._style_history.append(record)
        
        # Persist to SQLite
        try:
            conn = self._get_connection()
            conn.execute("""
                INSERT INTO style_communication 
                (is_verbose, is_direct, message_length, timestamp, day_of_week, hour_of_day)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                is_verbose,
                is_direct,
                message_length,
                ts,
                now.weekday(),
                now.hour,
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to record style: {e}")
        
        # Keep history bounded
        if len(self._style_history) > 500:
            self._style_history = self._style_history[-250:]
        
        # Update profile
        self._update_profile()

    def _update_profile(self) -> None:
        """Update aggregated user style profile."""
        ts = time.time()
        
        # Calculate preferred task types
        if self._task_type_counts:
            top_tasks = self._task_type_counts.most_common(5)
            preferred_task_types = [t[0] for t in top_tasks if t[1] >= self.min_occurrences]
        else:
            preferred_task_types = []
        
        # Calculate preferred agents
        if self._agent_counts:
            top_agents = self._agent_counts.most_common(5)
            preferred_agents = [a[0] for a in top_agents if a[1] >= self.min_occurrences]
        else:
            preferred_agents = []
        
        # Calculate peak hours
        if self._hour_counts:
            peak_hours = sorted(
                [h for h, c in self._hour_counts.items() if c >= self.min_occurrences],
                key=lambda h: self._hour_counts[h],
                reverse=True,
            )[:4]
        else:
            peak_hours = []
        
        # Calculate success rate
        success_count = sum(1 for d in self._delegation_history if d.success)
        success_rate = success_count / len(self._delegation_history) if self._delegation_history else 0.5
        
        # Calculate average latency
        if self._delegation_history:
            avg_latency = sum(d.latency_ms for d in self._delegation_history) / len(self._delegation_history)
        else:
            avg_latency = 0.0
        
        # Calculate communication style from recent history
        if len(self._style_history) >= 3:
            recent_styles = self._style_history[-10:]
            verbose_count = sum(1 for s in recent_styles if s.is_verbose)
            direct_count = sum(1 for s in recent_styles if s.is_direct)
            
            if verbose_count > len(recent_styles) * 0.6:
                comm_style = "verbose"
            elif verbose_count < len(recent_styles) * 0.4:
                comm_style = "concise"
            else:
                comm_style = "balanced"
            
            if direct_count > len(recent_styles) * 0.6:
                comm_directness = "direct"
            elif direct_count < len(recent_styles) * 0.4:
                comm_directness = "exploratory"
            else:
                comm_directness = "balanced"
        else:
            comm_style = "balanced"
            comm_directness = "balanced"
        
        # Build profile
        profile = {
            "preferred_task_types": preferred_task_types,
            "preferred_agents": preferred_agents,
            "communication_style": comm_style,
            "communication_directness": comm_directness,
            "peak_hours": peak_hours,
            "success_rate": success_rate,
            "avg_latency_ms": avg_latency,
        }
        
        # Persist to SQLite
        try:
            conn = self._get_connection()
            conn.execute("""
                INSERT OR REPLACE INTO user_style_profile 
                (id, preferred_task_types, preferred_agents, communication_style, 
                 communication_directness, peak_hours, success_rate, avg_latency_ms, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                1,  # Always use id=1 for the single profile
                "|".join(preferred_task_types),
                "|".join(preferred_agents),
                comm_style,
                comm_directness,
                "|".join(str(h) for h in peak_hours),
                success_rate,
                avg_latency,
                ts,
            ))
            conn.commit()
            conn.close()
            logger.debug(f"Updated style profile: {profile}")
        except Exception as e:
            logger.error(f"Failed to update profile: {e}")
        
        self._profile = profile

    def get_style_context(self) -> Dict[str, Any]:
        """Get learned style context for injection.

        Returns:
            Dict with style information for context injection
        """
        profile = self._get_or_build_profile()
        
        context = {
            "style_profile": {
                "preferred_task_types": profile.get("preferred_task_types", []),
                "preferred_agents": profile.get("preferred_agents", []),
                "communication_style": profile.get("communication_style", "balanced"),
                "communication_directness": profile.get("communication_directness", "balanced"),
                "peak_hours": profile.get("peak_hours", []),
                "success_rate": round(profile.get("success_rate", 0.5), 2),
                "avg_latency_ms": round(profile.get("avg_latency_ms", 0), 0),
            },
            "recommendations": self._get_recommendations(profile),
            "timestamp": datetime.now().isoformat(),
        }
        
        return context

    def _get_or_build_profile(self) -> Dict[str, Any]:
        """Get profile from DB or build from current data."""
        if self._profile:
            return self._profile
        
        # Rebuild from current data
        self._update_profile()
        return self._profile or {}

    def _get_recommendations(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Generate recommendations based on learned style."""
        recs = {}
        
        # Agent recommendation
        if profile.get("preferred_agents"):
            recs["suggested_agents"] = profile["preferred_agents"][:3]
        
        # Communication style adjustments
        comm_style = profile.get("communication_style", "balanced")
        if comm_style == "concise":
            recs["communication_tip"] = "Keep responses brief and direct"
        elif comm_style == "verbose":
            recs["communication_tip"] = "Provide detailed explanations and context"
        
        # Directness adjustments
        comm_direct = profile.get("communication_directness", "balanced")
        if comm_direct == "direct":
            recs["approach_tip"] = "Focus on actionable recommendations"
        elif comm_direct == "exploratory":
            recs["approach_tip"] = "Explore options and discuss tradeoffs"
        
        # Time-based tip
        current_hour = datetime.now().hour
        peak_hours = profile.get("peak_hours", [])
        if peak_hours and current_hour not in peak_hours:
            recs["time_tip"] = f"User is most active during hours: {peak_hours}"
        
        return recs

    def get_task_stats(self) -> Dict[str, Any]:
        """Get task type statistics.

        Returns:
            Dict with task type distribution and trends
        """
        total = sum(self._task_type_counts.values())
        
        return {
            "total_tasks": total,
            "by_type": dict(self._task_type_counts),
            "top_task_type": self._task_type_counts.most_common(1)[0][0] if self._task_type_counts else None,
            "hour_distribution": dict(self._hour_counts),
        }

    def get_delegation_stats(self) -> Dict[str, Any]:
        """Get delegation pattern statistics.

        Returns:
            Dict with agent usage and success rates
        """
        total = sum(self._agent_counts.values())
        
        # Calculate success rates per agent
        agent_success: Dict[str, List[bool]] = defaultdict(list)
        for d in self._delegation_history:
            agent_success[d.agent].append(d.success)
        
        success_rates = {
            agent: sum(successes) / len(successes) if successes else 0.5
            for agent, successes in agent_success.items()
        }
        
        return {
            "total_delegations": total,
            "by_agent": dict(self._agent_counts),
            "top_agent": self._agent_counts.most_common(1)[0][0] if self._agent_counts else None,
            "success_rates": {k: round(v, 2) for k, v in success_rates.items()},
            "avg_latency_ms": round(
                sum(d.latency_ms for d in self._delegation_history) / len(self._delegation_history)
                if self._delegation_history else 0, 0
            ),
        }

    def get_style_stats(self) -> Dict[str, Any]:
        """Get communication style statistics.

        Returns:
            Dict with communication pattern analysis
        """
        if not self._style_history:
            return {"total_samples": 0}
        
        verbose_count = sum(1 for s in self._style_history if s.is_verbose)
        direct_count = sum(1 for s in self._style_history if s.is_direct)
        total = len(self._style_history)
        
        avg_length = sum(s.message_length for s in self._style_history) / total
        
        return {
            "total_samples": total,
            "verbose_ratio": round(verbose_count / total, 2),
            "direct_ratio": round(direct_count / total, 2),
            "avg_message_length": round(avg_length, 0),
            "current_style": self._profile.get("communication_style", "unknown") if self._profile else "unknown",
            "current_directness": self._profile.get("communication_directness", "unknown") if self._profile else "unknown",
        }

    def get_all_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics.

        Returns:
            Dict with all learning statistics
        """
        return {
            "task_stats": self.get_task_stats(),
            "delegation_stats": self.get_delegation_stats(),
            "style_stats": self.get_style_stats(),
            "profile": self._profile or {},
        }


# Convenience function for quick access
_learner_instance: Optional[StyleLearner] = None


def get_learner(db_path: Optional[str] = None) -> StyleLearner:
    """Get singleton StyleLearner instance.
    
    Args:
        db_path: Optional path to SQLite database
    
    Returns:
        StyleLearner instance
    """
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = StyleLearner(db_path=db_path)
    return _learner_instance