"""Shared pytest fixtures for all tests."""

import pytest
import tempfile
import os
from pathlib import Path


@pytest.fixture
def temp_db():
    """Create temporary SQLite database."""
    with tempfile.TemporaryDirectory() as td:
        db_path = os.path.join(td, "test.db")
        yield db_path


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def mock_env():
    """Set up test environment variables."""
    original = os.environ.copy()
    os.environ["TEST_MODE"] = "true"
    yield os.environ
    os.environ.clear()
    os.environ.update(original)
