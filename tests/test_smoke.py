"""Smoke tests for the MoltGrid Python SDK against the live API.

These tests require the ``MOLTGRID_API_KEY`` environment variable to be set.
When the key is absent every test is skipped with a clear message.
"""

import os
import uuid

import pytest

from moltgrid import MoltGrid, MoltGridError

SKIP_NO_KEY = pytest.mark.skipif(
    not os.environ.get("MOLTGRID_API_KEY"),
    reason="MOLTGRID_API_KEY not set -- skip live API tests",
)


@SKIP_NO_KEY
class TestMemory:
    """Memory CRUD operations."""

    def test_memory_write_read_delete(self, client: MoltGrid):
        key = f"smoke_test_{uuid.uuid4().hex[:8]}"
        value = {"hello": "world", "ts": key}

        # Write
        result = client.memory_set(key, value)
        assert result is not None

        # Read back
        fetched = client.memory_get(key)
        assert fetched is not None
        # The value may be nested under a "value" key depending on API shape
        stored = fetched.get("value", fetched)
        if isinstance(stored, dict):
            assert stored.get("hello") == "world"

        # Cleanup
        client.memory_delete(key)

    def test_memory_list(self, client: MoltGrid):
        result = client.memory_list()
        assert isinstance(result, dict)


@SKIP_NO_KEY
class TestQueue:
    """Queue submit and status operations."""

    def test_queue_submit_and_status(self, client: MoltGrid):
        payload = {"smoke": "test", "id": uuid.uuid4().hex[:8]}
        submitted = client.queue_submit(payload)
        assert isinstance(submitted, dict)
        job_id = submitted.get("id") or submitted.get("job_id")
        assert job_id is not None, f"No job id in response: {submitted}"

        # Check status
        status = client.queue_status(str(job_id))
        assert isinstance(status, dict)


@SKIP_NO_KEY
class TestStats:
    """Stats endpoint connectivity."""

    def test_stats(self, client: MoltGrid):
        result = client.stats()
        assert isinstance(result, dict)


@SKIP_NO_KEY
class TestHeartbeat:
    """Heartbeat endpoint."""

    def test_heartbeat(self, client: MoltGrid):
        result = client.heartbeat()
        assert isinstance(result, dict)


@SKIP_NO_KEY
class TestDirectory:
    """Directory listing."""

    def test_directory(self, client: MoltGrid):
        result = client.directory()
        assert isinstance(result, (dict, list))
