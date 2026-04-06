"""Smoke tests — verify core imports work."""

import pytest


def test_dotenv_import():
    import dotenv

    assert dotenv is not None


def test_requests_import():
    import requests

    assert requests is not None


def test_pydantic_import():
    import pydantic

    assert pydantic is not None


def test_diskcache_import():
    import diskcache

    assert diskcache is not None


def test_rich_import():
    import rich

    assert rich is not None
