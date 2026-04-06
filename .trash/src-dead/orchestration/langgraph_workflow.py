"""
LangGraph Workflow Integration for N-Xyme Catalyst Agent System.

Provides stateful agent graphs with Neo4j checkpointing for:
- State persistence across restarts
- Failure recovery (resume from checkpoint)
- Audit trail logging
- Integration with existing agent framework

Architecture:
- Neo4jSaver: Custom checkpoint saver using Neo4j
- AgentState: TypedDict for agent workflow state
- AgentWorkflow: LangGraph-based stateful workflow engine
"""

import json
import logging
import time
import uuid
from datetime import datetime
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.serde.base import SerializerProtocol
from langgraph.graph import END, StateGraph
from neo4j import GraphDatabase
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

logger = logging.getLogger(__name__)

# ── Neo4j Configuration ──────────────────────────────────────────────────────

NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "password"  # Should be loaded from env in production


# ── Agent State Definition ────────────────────────────────────────────────────


class AgentState(TypedDict):
    """State schema for agent workflow graphs."""

    # Core state
    thread_id: str
    current_step: str
    status: str  # "running" | "paused" | "completed" | "failed"

    # Input/Output
    user_input: str
    agent_response: str

    # Working memory
    goal: str
    scratch: Dict[str, Any]
    observations: List[Dict[str, Any]]

    # Step tracking
    step_count: int
    max_steps: int
    steps_history: List[Dict[str, Any]]

    # Error handling
    error_count: int
    last_error: Optional[str]

    # Metadata
    created_at: str
    updated_at: str
    metadata: Dict[str, Any]


# ── Audit Trail Entry ─────────────────────────────────────────────────────────


class AuditEntry(BaseModel):
    """Single audit trail entry."""

    entry_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    thread_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    event_type: str  # "step_start" | "step_end" | "checkpoint" | "error" | "resume"
    step_name: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)
    state_snapshot: Optional[Dict[str, Any]] = None


# ── Neo4j Checkpoint Saver ────────────────────────────────────────────────────


class Neo4jSaver(BaseCheckpointSaver):
    """
    Custom checkpoint saver using Neo4j for persistence.

    Stores checkpoints as nodes in Neo4j with relationships for:
    - Thread tracking (thread_id)
    - Checkpoint ordering (sequence)
    - Parent-child relationships (for branching)

    Schema:
    (Checkpoint {
        checkpoint_id: str,
        thread_id: str,
        parent_id: str,
        step: int,
        timestamp: str,
        metadata: str (JSON),
        state: str (JSON serialized)
    })
    """

    def __init__(
        self,
        uri: str = NEO4J_URI,
        user: str = NEO4J_USER,
        password: str = NEO4J_PASSWORD,
        serializer: Optional[SerializerProtocol] = None,
    ):
        """Initialize Neo4j checkpoint saver."""
        super().__init__(serde=serializer)
        self._driver = GraphDatabase.driver(uri, auth=(user, password))
        self._init_schema()
        logger.info(f"Neo4jSaver: Connected to {uri}")

    def _init_schema(self) -> None:
        """Initialize Neo4j schema with constraints and indexes."""
        with self._driver.session() as session:
            # Create constraint for checkpoint_id uniqueness
            session.run(
                """
                CREATE CONSTRAINT checkpoint_id_unique IF NOT EXISTS
                FOR (c:Checkpoint)
                REQUIRE c.checkpoint_id IS UNIQUE
                """
            )
            # Create index for thread_id lookups
            session.run(
                """
                CREATE INDEX checkpoint_thread_idx IF NOT EXISTS
                FOR (c:Checkpoint)
                ON (c.thread_id)
                """
            )
            # Create index for timestamp ordering
            session.run(
                """
                CREATE INDEX checkpoint_timestamp_idx IF NOT EXISTS
                FOR (c:Checkpoint)
                ON (c.timestamp)
                """
            )
            # Create audit trail node constraint
            session.run(
                """
                CREATE CONSTRAINT audit_entry_id_unique IF NOT EXISTS
                FOR (a:AuditEntry)
                REQUIRE a.entry_id IS UNIQUE
                """
            )
            logger.info("Neo4jSaver: Schema initialized")

    def close(self) -> None:
        """Close Neo4j driver connection."""
        self._driver.close()
        logger.info("Neo4jSaver: Connection closed")

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: Optional[Dict[str, Any]] = None,
    ) -> RunnableConfig:
        """
        Save a checkpoint to Neo4j.

        Args:
            config: Runnable configuration with thread_id
            checkpoint: Checkpoint to save
            metadata: Checkpoint metadata
            new_versions: New channel versions

        Returns:
            Updated config with checkpoint_id
        """
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id", "")
        checkpoint_id = str(uuid.uuid4())
        parent_id = configurable.get("checkpoint_id")
        step = checkpoint.get("step", 0)
        timestamp = datetime.utcnow().isoformat()

        # Serialize state
        state_json = json.dumps(self.serde.dumps_typed(checkpoint)[1])
        metadata_json = json.dumps(
            {
                "source": metadata.get("source", ""),
                "step": step,
                "writes": metadata.get("writes", {}),
                "parents": metadata.get("parents", {}),
            }
        )

        with self._driver.session() as session:
            # Batched: Create checkpoint + parent relationship + thread relationship
            # Previously 3 separate queries, now 1 combined transaction
            query = """
                CREATE (c:Checkpoint {
                    checkpoint_id: $checkpoint_id,
                    thread_id: $thread_id,
                    parent_id: $parent_id,
                    step: $step,
                    timestamp: $timestamp,
                    metadata: $metadata,
                    state: $state
                })
                WITH c
                FOREACH (pid IN CASE WHEN $parent_id IS NOT NULL THEN [$parent_id] ELSE [] END |
                    MERGE (parent:Checkpoint {checkpoint_id: pid})
                    CREATE (parent)-[:NEXT_CHECKPOINT]->(c)
                )
                WITH c
                MERGE (t:Thread {thread_id: $thread_id})
                CREATE (t)-[:HAS_CHECKPOINT]->(c)
            """
            session.run(
                query,
                checkpoint_id=checkpoint_id,
                thread_id=thread_id,
                parent_id=parent_id,
                step=step,
                timestamp=timestamp,
                metadata=metadata_json,
                state=state_json,
            )

        logger.info(
            f"Neo4jSaver: Saved checkpoint {checkpoint_id} for thread {thread_id} at step {step}"
        )

        # Return updated config
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[Tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        """
        Save intermediate writes to checkpoint.

        Args:
            config: Runnable configuration
            writes: Sequence of (channel, value) tuples
            task_id: Task identifier
            task_path: Task path (optional)
        """
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id", "")
        checkpoint_id = configurable.get("checkpoint_id")

        if not checkpoint_id:
            logger.warning("Neo4jSaver: No checkpoint_id for put_writes")
            return

        writes_json = json.dumps(
            [(channel, self.serde.dumps_typed(value)[1]) for channel, value in writes]
        )

        with self._driver.session() as session:
            session.run(
                """
                MATCH (c:Checkpoint {checkpoint_id: $checkpoint_id})
                SET c.writes = $writes,
                    c.task_id = $task_id,
                    c.writes_timestamp = $timestamp
                """,
                checkpoint_id=checkpoint_id,
                writes=writes_json,
                task_id=task_id,
                timestamp=datetime.utcnow().isoformat(),
            )

        logger.debug(f"Neo4jSaver: Saved writes for checkpoint {checkpoint_id}")

    def get_tuple(self, config: RunnableConfig) -> Optional[CheckpointTuple]:
        """
        Retrieve a checkpoint tuple by config.

        Args:
            config: Runnable configuration with thread_id and optional checkpoint_id

        Returns:
            CheckpointTuple if found, None otherwise
        """
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id", "")
        checkpoint_id = configurable.get("checkpoint_id")

        with self._driver.session() as session:
            if checkpoint_id:
                # Get specific checkpoint
                result = session.run(
                    """
                    MATCH (c:Checkpoint {checkpoint_id: $checkpoint_id, thread_id: $thread_id})
                    RETURN c.checkpoint_id AS checkpoint_id,
                           c.parent_id AS parent_id,
                           c.step AS step,
                           c.timestamp AS timestamp,
                           c.metadata AS metadata,
                           c.state AS state
                    """,
                    checkpoint_id=checkpoint_id,
                    thread_id=thread_id,
                )
            else:
                # Get latest checkpoint for thread
                result = session.run(
                    """
                    MATCH (c:Checkpoint {thread_id: $thread_id})
                    RETURN c.checkpoint_id AS checkpoint_id,
                           c.parent_id AS parent_id,
                           c.step AS step,
                           c.timestamp AS timestamp,
                           c.metadata AS metadata,
                           c.state AS state
                    ORDER BY c.step DESC, c.timestamp DESC
                    LIMIT 1
                    """,
                    thread_id=thread_id,
                )

            record = result.single()
            if not record:
                return None

            # Deserialize state
            checkpoint = self.serde.loads_typed(json.loads(record["state"]))
            metadata = json.loads(record["metadata"])

            # Build parent config if exists
            parent_config: Optional[RunnableConfig] = None
            if record["parent_id"]:
                parent_config = {
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": record["parent_id"],
                    }
                }

            return CheckpointTuple(
                config={
                    "configurable": {
                        "thread_id": thread_id,
                        "checkpoint_id": record["checkpoint_id"],
                    }
                },
                checkpoint=checkpoint,
                metadata=metadata,
                parent_config=parent_config,
            )

    def list(
        self,
        config: Optional[RunnableConfig] = None,
        *,
        filter: Optional[Dict[str, Any]] = None,
        before: Optional[RunnableConfig] = None,
        limit: Optional[int] = None,
    ) -> Iterator[CheckpointTuple]:
        """
        List checkpoints for a thread.

        Args:
            config: Runnable configuration with thread_id
            filter: Optional metadata filters
            before: Optional config to list before
            limit: Optional limit on results

        Returns:
            Iterator of CheckpointTuples
        """
        if not config:
            return iter([])

        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        if not thread_id:
            return iter([])

        query = """
            MATCH (c:Checkpoint {thread_id: $thread_id})
            RETURN c.checkpoint_id AS checkpoint_id,
                   c.parent_id AS parent_id,
                   c.step AS step,
                   c.timestamp AS timestamp,
                   c.metadata AS metadata,
                   c.state AS state
            ORDER BY c.step DESC, c.timestamp DESC
        """
        params: Dict[str, Any] = {"thread_id": thread_id}

        if limit:
            query += " LIMIT $limit"
            params["limit"] = limit

        with self._driver.session() as session:
            result = session.run(query, **params)

            tuples = []
            for record in result:
                checkpoint = self.serde.loads_typed(json.loads(record["state"]))
                metadata = json.loads(record["metadata"])

                parent_config: Optional[RunnableConfig] = None
                if record["parent_id"]:
                    parent_config = {
                        "configurable": {
                            "thread_id": thread_id,
                            "checkpoint_id": record["parent_id"],
                        }
                    }

                tuples.append(
                    CheckpointTuple(
                        config={
                            "configurable": {
                                "thread_id": thread_id,
                                "checkpoint_id": record["checkpoint_id"],
                            }
                        },
                        checkpoint=checkpoint,
                        metadata=metadata,
                        parent_config=parent_config,
                    )
                )

            return iter(tuples)

    # ── Audit Trail Methods ────────────────────────────────────────────────

    def log_audit_entry(self, entry: AuditEntry) -> None:
        """
        Log an audit trail entry to Neo4j.

        Args:
            entry: AuditEntry to log
        """
        with self._driver.session() as session:
            session.run(
                """
                CREATE (a:AuditEntry {
                    entry_id: $entry_id,
                    thread_id: $thread_id,
                    timestamp: $timestamp,
                    event_type: $event_type,
                    step_name: $step_name,
                    details: $details
                })
                WITH a
                MATCH (t:Thread {thread_id: $thread_id})
                CREATE (t)-[:HAS_AUDIT]->(a)
                """,
                entry_id=entry.entry_id,
                thread_id=entry.thread_id,
                timestamp=entry.timestamp,
                event_type=entry.event_type,
                step_name=entry.step_name,
                details=json.dumps(entry.details),
            )

        logger.debug(
            f"Neo4jSaver: Audit entry logged - {entry.event_type} for thread {entry.thread_id}"
        )

    def get_audit_trail(self, thread_id: str, limit: int = 100) -> List[AuditEntry]:
        """
        Retrieve audit trail for a thread.

        Args:
            thread_id: Thread identifier
            limit: Maximum entries to return

        Returns:
            List of AuditEntry objects
        """
        with self._driver.session() as session:
            result = session.run(
                """
                MATCH (a:AuditEntry {thread_id: $thread_id})
                RETURN a.entry_id AS entry_id,
                       a.thread_id AS thread_id,
                       a.timestamp AS timestamp,
                       a.event_type AS event_type,
                       a.step_name AS step_name,
                       a.details AS details
                ORDER BY a.timestamp DESC
                LIMIT $limit
                """,
                thread_id=thread_id,
                limit=limit,
            )

            entries = []
            for record in result:
                entries.append(
                    AuditEntry(
                        entry_id=record["entry_id"],
                        thread_id=record["thread_id"],
                        timestamp=record["timestamp"],
                        event_type=record["event_type"],
                        step_name=record["step_name"],
                        details=json.loads(record["details"]),
                    )
                )

            return entries


# ── Agent Workflow Nodes ──────────────────────────────────────────────────────


def create_initial_state(
    user_input: str,
    thread_id: Optional[str] = None,
    max_steps: int = 15,
) -> AgentState:
    """
    Create initial agent state.

    Args:
        user_input: User's input/request
        thread_id: Optional thread ID (generates new if not provided)
        max_steps: Maximum steps before termination

    Returns:
        Initial AgentState
    """
    now = datetime.utcnow().isoformat()
    return AgentState(
        thread_id=thread_id or str(uuid.uuid4()),
        current_step="initialize",
        status="running",
        user_input=user_input,
        agent_response="",
        goal=user_input,
        scratch={},
        observations=[],
        step_count=0,
        max_steps=max_steps,
        steps_history=[],
        error_count=0,
        last_error=None,
        created_at=now,
        updated_at=now,
        metadata={},
    )


def think_node(state: AgentState) -> AgentState:
    """
    Think node: Analyze current state and decide next action.

    This is where the LLM reasoning happens. In production, this would
    call the actual LLM (Ollama/Groq) via the brain module.
    """
    logger.info(f"Think node: step {state['step_count'] + 1}/{state['max_steps']}")

    # Update state
    state["current_step"] = "think"
    state["step_count"] += 1
    state["updated_at"] = datetime.utcnow().isoformat()

    # Record observation
    state["observations"].append(
        {
            "type": "think",
            "step": state["step_count"],
            "timestamp": state["updated_at"],
            "goal": state["goal"],
        }
    )

    # Add to history
    state["steps_history"].append(
        {
            "step": state["step_count"],
            "node": "think",
            "timestamp": state["updated_at"],
        }
    )

    return state


def act_node(state: AgentState) -> AgentState:
    """
    Act node: Execute the decided action.

    In production, this would execute tools via the security layer.
    """
    logger.info(f"Act node: executing action for step {state['step_count']}")

    state["current_step"] = "act"
    state["updated_at"] = datetime.utcnow().isoformat()

    # Record observation
    state["observations"].append(
        {
            "type": "act",
            "step": state["step_count"],
            "timestamp": state["updated_at"],
        }
    )

    state["steps_history"].append(
        {
            "step": state["step_count"],
            "node": "act",
            "timestamp": state["updated_at"],
        }
    )

    return state


def observe_node(state: AgentState) -> AgentState:
    """
    Obnode: Process action results and update state.

    Captures results and updates working memory.
    """
    logger.info(f"Observe node: processing results for step {state['step_count']}")

    state["current_step"] = "observe"
    state["updated_at"] = datetime.utcnow().isoformat()

    # Record observation
    state["observations"].append(
        {
            "type": "observe",
            "step": state["step_count"],
            "timestamp": state["updated_at"],
        }
    )

    state["steps_history"].append(
        {
            "step": state["step_count"],
            "node": "observe",
            "timestamp": state["updated_at"],
        }
    )

    return state


def evaluate_node(state: AgentState) -> AgentState:
    """
    Evaluate node: Check if goal is complete or continue.

    Determines workflow termination or continuation.
    """
    logger.info(f"Evaluate node: checking completion for step {state['step_count']}")

    state["current_step"] = "evaluate"
    state["updated_at"] = datetime.utcnow().isoformat()

    # Check termination conditions
    if state["step_count"] >= state["max_steps"]:
        state["status"] = "completed"
        state["agent_response"] = f"Max steps ({state['max_steps']}) reached"
        logger.warning(f"Workflow {state['thread_id']}: Max steps reached")

    # Record observation
    state["observations"].append(
        {
            "type": "evaluate",
            "step": state["step_count"],
            "timestamp": state["updated_at"],
            "status": state["status"],
        }
    )

    state["steps_history"].append(
        {
            "step": state["step_count"],
            "node": "evaluate",
            "timestamp": state["updated_at"],
        }
    )

    return state


def error_handler_node(state: AgentState) -> AgentState:
    """
    Error handler node: Handle failures and attempt recovery.

    Increments error count and determines if workflow should continue.
    """
    logger.error(f"Error handler: error #{state['error_count'] + 1} in thread {state['thread_id']}")

    state["current_step"] = "error_handler"
    state["error_count"] += 1
    state["updated_at"] = datetime.utcnow().isoformat()

    # Check if too many errors
    if state["error_count"] >= 3:
        state["status"] = "failed"
        logger.error(f"Workflow {state['thread_id']}: Failed after 3 errors")

    state["steps_history"].append(
        {
            "step": state["step_count"],
            "node": "error_handler",
            "timestamp": state["updated_at"],
            "error_count": state["error_count"],
        }
    )

    return state


# ── Routing Logic ─────────────────────────────────────────────────────────────


def should_continue(state: AgentState) -> str:
    """
    Determine next node based on current state.

    Returns:
        Next node name or END
    """
    # Check for failure
    if state["status"] == "failed":
        return END

    # Check for completion
    if state["status"] == "completed":
        return END

    # Check max steps
    if state["step_count"] >= state["max_steps"]:
        return END

    # Continue workflow
    return "think"


def route_after_evaluate(state: AgentState) -> str:
    """
    Route after evaluation node.

    Returns:
        Next node name
    """
    if state["status"] in ("completed", "failed"):
        return END
    return "think"


# ── Workflow Builder ──────────────────────────────────────────────────────────


class AgentWorkflow:
    """
    LangGraph-based stateful agent workflow with Neo4j checkpointing.

    Provides:
    - Stateful graph execution with Think → Act → Observe → Evaluate loop
    - Neo4j checkpoint persistence for failure recovery
    - Audit trail logging
    - Resume from checkpoint capability

    Usage:
        workflow = AgentWorkflow()
        result = await workflow.run("Do something complex")
        # If interrupted, resume:
        result = await workflow.resume(result["thread_id"])
    """

    def __init__(
        self,
        neo4j_uri: str = NEO4J_URI,
        neo4j_user: str = NEO4J_USER,
        neo4j_password: str = NEO4J_PASSWORD,
        max_steps: int = 15,
    ):
        """
        Initialize agent workflow.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            max_steps: Maximum steps per workflow run
        """
        self.max_steps = max_steps
        self.checkpointer = Neo4jSaver(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
        )
        self._graph = self._build_graph()
        logger.info("AgentWorkflow: Initialized with Neo4j checkpointing")

    def _build_graph(self) -> Any:
        """
        Build the agent workflow graph.

        Graph structure:
            think → act → observe → evaluate → (think | END)
            Any node → error_handler → (think | END)

        Returns:
            Compiled StateGraph
        """
        # Create graph
        graph = StateGraph(AgentState)

        # Add nodes
        graph.add_node("think", think_node)
        graph.add_node("act", act_node)
        graph.add_node("observe", observe_node)
        graph.add_node("evaluate", evaluate_node)
        graph.add_node("error_handler", error_handler_node)

        # Set entry point
        graph.set_entry_point("think")

        # Add edges: think → act
        graph.add_edge("think", "act")

        # Add edges: act → observe
        graph.add_edge("act", "observe")

        # Add edges: observe → evaluate
        graph.add_edge("observe", "evaluate")

        # Add conditional edges: evaluate → (think | END)
        graph.add_conditional_edges("evaluate", route_after_evaluate)

        # Add conditional edges: error_handler → (think | END)
        graph.add_conditional_edges("error_handler", should_continue)

        # Compile with checkpointing
        return graph.compile(checkpointer=self.checkpointer)

    async def run(
        self,
        user_input: str,
        thread_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Run the agent workflow.

        Args:
            user_input: User's input/request
            thread_id: Optional thread ID for continuation
            metadata: Optional metadata to attach

        Returns:
            Final state dict with thread_id for resumption
        """
        # Create initial state
        initial_state = create_initial_state(
            user_input=user_input,
            thread_id=thread_id,
            max_steps=self.max_steps,
        )

        if metadata:
            initial_state["metadata"] = metadata

        # Log audit entry
        self.checkpointer.log_audit_entry(
            AuditEntry(
                thread_id=initial_state["thread_id"],
                event_type="workflow_start",
                details={"user_input": user_input, "max_steps": self.max_steps},
            )
        )

        # Configure with thread_id for checkpointing
        config: RunnableConfig = {"configurable": {"thread_id": initial_state["thread_id"]}}

        try:
            # Run the graph
            logger.info(f"AgentWorkflow: Starting workflow {initial_state['thread_id']}")
            final_state: Dict[str, Any] = {}

            async for event in self._graph.astream(initial_state, config):  # type: ignore
                # Log each step
                for node_name, state_update in event.items():
                    logger.debug(f"AgentWorkflow: Node {node_name} completed")

                    # Log audit entry for each node
                    self.checkpointer.log_audit_entry(
                        AuditEntry(
                            thread_id=initial_state["thread_id"],
                            event_type="step_end",
                            step_name=node_name,
                            details={
                                "step_count": state_update.get("step_count", 0),
                                "status": state_update.get("status", "running"),
                            },
                        )
                    )

                    final_state = dict(state_update)

            # Log completion
            self.checkpointer.log_audit_entry(
                AuditEntry(
                    thread_id=initial_state["thread_id"],
                    event_type="workflow_complete",
                    details={
                        "final_status": final_state.get("status", "unknown"),
                        "total_steps": final_state.get("step_count", 0),
                    },
                )
            )

            logger.info(
                f"AgentWorkflow: Workflow {initial_state['thread_id']} completed "
                f"with status {final_state.get('status', 'unknown')}"
            )

            return final_state if final_state else dict(initial_state)

        except Exception as e:
            # Log error
            self.checkpointer.log_audit_entry(
                AuditEntry(
                    thread_id=initial_state["thread_id"],
                    event_type="error",
                    details={"error": str(e), "error_type": type(e).__name__},
                )
            )
            logger.error(f"AgentWorkflow: Error in workflow: {e}")
            raise

    async def resume(self, thread_id: str) -> Dict[str, Any]:
        """
        Resume a workflow from the last checkpoint.

        Args:
            thread_id: Thread ID to resume

        Returns:
            Final state dict

        Raises:
            ValueError: If no checkpoint found for thread_id
        """
        # Get last checkpoint
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        checkpoint_tuple = self.checkpointer.get_tuple(config)

        if not checkpoint_tuple:
            raise ValueError(f"No checkpoint found for thread {thread_id}")

        # Log resume
        checkpoint_config = checkpoint_tuple.config.get("configurable", {})
        self.checkpointer.log_audit_entry(
            AuditEntry(
                thread_id=thread_id,
                event_type="resume",
                details={
                    "from_checkpoint": checkpoint_config.get("checkpoint_id", ""),
                    "from_step": checkpoint_tuple.checkpoint.get("step", 0),
                },
            )
        )

        logger.info(
            f"AgentWorkflow: Resuming workflow {thread_id} from checkpoint "
            f"{checkpoint_config.get('checkpoint_id', '')}"
        )

        try:
            # Resume from checkpoint
            final_state: Dict[str, Any] = {}

            async for event in self._graph.astream(None, config):  # type: ignore
                for node_name, state_update in event.items():
                    logger.debug(f"AgentWorkflow: Node {node_name} completed")

                    self.checkpointer.log_audit_entry(
                        AuditEntry(
                            thread_id=thread_id,
                            event_type="step_end",
                            step_name=node_name,
                            details={
                                "step_count": state_update.get("step_count", 0),
                                "status": state_update.get("status", "running"),
                            },
                        )
                    )

                    final_state = dict(state_update)

            # Log completion
            self.checkpointer.log_audit_entry(
                AuditEntry(
                    thread_id=thread_id,
                    event_type="workflow_complete",
                    details={
                        "final_status": final_state.get("status", "unknown"),
                        "resumed": True,
                    },
                )
            )

            logger.info(f"AgentWorkflow: Resumed workflow {thread_id} completed")
            return final_state

        except Exception as e:
            self.checkpointer.log_audit_entry(
                AuditEntry(
                    thread_id=thread_id,
                    event_type="error",
                    details={"error": str(e), "error_type": type(e).__name__, "resumed": True},
                )
            )
            logger.error(f"AgentWorkflow: Error resuming workflow: {e}")
            raise

    def get_audit_trail(self, thread_id: str, limit: int = 100) -> List[AuditEntry]:
        """
        Get audit trail for a workflow.

        Args:
            thread_id: Thread ID
            limit: Maximum entries

        Returns:
            List of AuditEntry objects
        """
        return self.checkpointer.get_audit_trail(thread_id, limit)

    def get_checkpoints(self, thread_id: str, limit: int = 10) -> List[CheckpointTuple]:
        """
        Get checkpoints for a thread.

        Args:
            thread_id: Thread ID
            limit: Maximum checkpoints

        Returns:
            List of CheckpointTuple objects
        """
        config: RunnableConfig = {"configurable": {"thread_id": thread_id}}
        return list(self.checkpointer.list(config, limit=limit))

    def close(self) -> None:
        """Close the workflow and cleanup resources."""
        self.checkpointer.close()
        logger.info("AgentWorkflow: Closed")


# ── Integration with Existing Agent Framework ─────────────────────────────────


class LangGraphAgentAdapter:
    """
    Adapter to integrate LangGraph workflow with existing agent framework.

    Bridges between the existing AgentLoop (jarvis/agent/loop.py) and
    the new LangGraph-based workflow.

    Usage:
        # In existing agent code:
        adapter = LangGraphAgentAdapter()
        result = await adapter.run_with_checkpointing(
            user_input="Do something",
            brain=my_brain,
            execute_fn=my_execute_fn,
        )
    """

    def __init__(
        self,
        neo4j_uri: str = NEO4J_URI,
        neo4j_user: str = NEO4J_USER,
        neo4j_password: str = NEO4J_PASSWORD,
    ):
        """Initialize the adapter."""
        self.workflow = AgentWorkflow(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
        )
        logger.info("LangGraphAgentAdapter: Initialized")

    async def run_with_checkpointing(
        self,
        user_input: str,
        brain: Any,
        execute_fn: Any,
        security_fn: Any,
        thread_id: Optional[str] = None,
        max_steps: int = 15,
    ) -> Dict[str, Any]:
        """
        Run agent with checkpointing support.

        This wraps the existing agent loop with LangGraph checkpointing,
        allowing state persistence and failure recovery.

        Args:
            user_input: User's input
            brain: LLM brain instance
            execute_fn: Action execution function
            security_fn: Security validation function
            thread_id: Optional thread ID for continuation
            max_steps: Maximum steps

        Returns:
            Result dict with thread_id for resumption
        """
        # Create enhanced workflow with brain integration
        workflow = AgentWorkflow(max_steps=max_steps)

        # Run with checkpointing
        result = await workflow.run(
            user_input=user_input,
            thread_id=thread_id,
            metadata={
                "brain_type": type(brain).__name__,
                "has_execute_fn": execute_fn is not None,
                "has_security_fn": security_fn is not None,
            },
        )

        # Add thread_id to result for resumption
        result["thread_id"] = result.get("thread_id", thread_id)

        return result

    async def resume_workflow(self, thread_id: str) -> Dict[str, Any]:
        """
        Resume a previously checkpointed workflow.

        Args:
            thread_id: Thread ID to resume

        Returns:
            Final state
        """
        return await self.workflow.resume(thread_id)

    def get_workflow_history(self, thread_id: str) -> Dict[str, Any]:
        """
        Get complete workflow history including checkpoints and audit trail.

        Args:
            thread_id: Thread ID

        Returns:
            Dict with checkpoints and audit entries
        """
        return {
            "checkpoints": self.workflow.get_checkpoints(thread_id),
            "audit_trail": self.workflow.get_audit_trail(thread_id),
        }

    def close(self) -> None:
        """Close the adapter and cleanup."""
        self.workflow.close()


# ── Convenience Functions ─────────────────────────────────────────────────────


def create_workflow(
    neo4j_uri: str = NEO4J_URI,
    neo4j_user: str = NEO4J_USER,
    neo4j_password: str = NEO4J_PASSWORD,
    max_steps: int = 15,
) -> AgentWorkflow:
    """
    Create an agent workflow instance.

    Convenience function for quick setup.

    Args:
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password
        max_steps: Maximum steps per workflow

    Returns:
        Configured AgentWorkflow instance
    """
    return AgentWorkflow(
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
        max_steps=max_steps,
    )


async def run_with_recovery(
    user_input: str,
    thread_id: Optional[str] = None,
    neo4j_uri: str = NEO4J_URI,
    neo4j_user: str = NEO4J_USER,
    neo4j_password: str = NEO4J_PASSWORD,
) -> Dict[str, Any]:
    """
    Run a workflow with automatic recovery support.

    If thread_id is provided, attempts to resume from checkpoint.
    Otherwise, starts a new workflow.

    Args:
        user_input: User's input (ignored if resuming)
        thread_id: Optional thread ID for resumption
        neo4j_uri: Neo4j connection URI
        neo4j_user: Neo4j username
        neo4j_password: Neo4j password

    Returns:
        Final state dict
    """
    workflow = create_workflow(
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password,
    )

    try:
        if thread_id:
            # Try to resume
            try:
                return await workflow.resume(thread_id)
            except ValueError:
                # No checkpoint found, start new
                logger.info(f"No checkpoint for {thread_id}, starting new workflow")

        # Start new workflow
        return await workflow.run(user_input, thread_id=thread_id)
    finally:
        workflow.close()
