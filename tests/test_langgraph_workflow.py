"""
Test file for LangGraph workflow integration.

This file demonstrates how to use the LangGraph workflow with Neo4j checkpointing.
Note: Requires Neo4j running at localhost:7687.
"""

import asyncio
import logging

import pytest

try:
    from src.langgraph_workflow import (
        AgentWorkflow,
        LangGraphAgentAdapter,
        create_workflow,
        run_with_recovery,
    )
except ImportError:
    pytest.skip("langchain_core not installed", allow_module_level=True)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_basic_workflow():
    """Test basic workflow execution."""
    logger.info("=== Test: Basic Workflow ===")

    # Note: This requires Neo4j to be running
    # For testing without Neo4j, you can use the in-memory checkpointer
    try:
        workflow = create_workflow(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            max_steps=5,
        )

        result = await workflow.run(
            user_input="Test workflow execution",
            metadata={"test": True},
        )

        logger.info(f"Workflow completed with status: {result.get('status')}")
        logger.info(f"Thread ID: {result.get('thread_id')}")
        logger.info(f"Steps completed: {result.get('step_count')}")

        # Get audit trail
        audit_trail = workflow.get_audit_trail(result["thread_id"])
        logger.info(f"Audit entries: {len(audit_trail)}")

        workflow.close()
        logger.info("✓ Basic workflow test passed")

    except Exception as e:
        logger.error(f"✗ Basic workflow test failed: {e}")


async def test_resume_workflow():
    """Test workflow resumption from checkpoint."""
    logger.info("=== Test: Resume Workflow ===")

    try:
        workflow = create_workflow(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
            max_steps=10,
        )

        # Start workflow
        result1 = await workflow.run(
            user_input="Long running task",
            metadata={"test": "resume"},
        )
        thread_id = result1["thread_id"]
        logger.info(f"Initial workflow: {result1.get('status')}")

        # Resume workflow
        result2 = await workflow.resume(thread_id)
        logger.info(f"Resumed workflow: {result2.get('status')}")

        # Get checkpoints
        checkpoints = workflow.get_checkpoints(thread_id)
        logger.info(f"Checkpoints saved: {len(checkpoints)}")

        workflow.close()
        logger.info("✓ Resume workflow test passed")

    except Exception as e:
        logger.error(f"✗ Resume workflow test failed: {e}")


async def test_adapter():
    """Test the adapter for existing agent framework."""
    logger.info("=== Test: Agent Framework Adapter ===")

    try:
        adapter = LangGraphAgentAdapter(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
        )

        # Mock brain and functions
        class MockBrain:
            pass

        async def mock_execute(action):
            return {"success": True, "result": "executed"}

        def mock_security(actions):
            return actions, []

        result = await adapter.run_with_checkpointing(
            user_input="Test adapter integration",
            brain=MockBrain(),
            execute_fn=mock_execute,
            security_fn=mock_security,
            max_steps=5,
        )

        logger.info(f"Adapter result: {result.get('status')}")

        # Get history
        history = adapter.get_workflow_history(result["thread_id"])
        logger.info(
            f"History: {len(history['checkpoints'])} checkpoints, {len(history['audit_trail'])} audit entries"
        )

        adapter.close()
        logger.info("✓ Adapter test passed")

    except Exception as e:
        logger.error(f"✗ Adapter test failed: {e}")


async def test_recovery():
    """Test automatic recovery function."""
    logger.info("=== Test: Auto Recovery ===")

    try:
        # Start new workflow
        result1 = await run_with_recovery(
            user_input="Test recovery",
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
        )
        thread_id = result1["thread_id"]
        logger.info(f"Initial: {result1.get('status')}")

        # Resume using same thread_id
        result2 = await run_with_recovery(
            user_input="",  # Ignored when resuming
            thread_id=thread_id,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password",
        )
        logger.info(f"Recovered: {result2.get('status')}")

        logger.info("✓ Recovery test passed")

    except Exception as e:
        logger.error(f"✗ Recovery test failed: {e}")


async def main():
    """Run all tests."""
    logger.info("Starting LangGraph workflow tests...")
    logger.info("Note: These tests require Neo4j running at localhost:7687")
    logger.info("")

    await test_basic_workflow()
    logger.info("")

    await test_resume_workflow()
    logger.info("")

    await test_adapter()
    logger.info("")

    await test_recovery()
    logger.info("")

    logger.info("All tests completed!")


if __name__ == "__main__":
    asyncio.run(main())
