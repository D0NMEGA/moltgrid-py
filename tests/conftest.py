"""Shared fixtures for MoltGrid SDK smoke tests."""

import os

import pytest

from moltgrid import MoltGrid

SKIP_REASON = "MOLTGRID_API_KEY not set -- skip live API tests"


@pytest.fixture(scope="session")
def client():
    """Shared MoltGrid client for the test session."""
    api_key = os.environ.get("MOLTGRID_API_KEY")
    if not api_key:
        pytest.skip(SKIP_REASON)
    return MoltGrid(api_key=api_key)
