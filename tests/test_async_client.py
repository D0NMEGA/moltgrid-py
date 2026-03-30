"""Tests for AsyncMoltGrid client, exception hierarchy, and retry logic."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from moltgrid.exceptions import (
    APIError,
    AuthenticationError,
    MoltGridError,
    NotFoundError,
    RateLimitError,
    ValidationError,
    _STATUS_MAP,
)


# ------------------------------------------------------------------ #
# Exception hierarchy
# ------------------------------------------------------------------ #


class TestExceptionHierarchy:
    """Verify the MoltGridError > APIError > typed-error chain."""

    def test_api_error_inherits_moltgrid_error(self):
        assert issubclass(APIError, MoltGridError)

    def test_rate_limit_inherits_api_error(self):
        assert issubclass(RateLimitError, APIError)

    def test_auth_error_inherits_api_error(self):
        assert issubclass(AuthenticationError, APIError)

    def test_not_found_inherits_api_error(self):
        assert issubclass(NotFoundError, APIError)

    def test_validation_inherits_api_error(self):
        assert issubclass(ValidationError, APIError)

    def test_rate_limit_has_retry_after(self):
        err = RateLimitError(429, "too fast", retry_after=30)
        assert err.retry_after == 30
        assert err.status_code == 429

    def test_rate_limit_retry_after_defaults_none(self):
        err = RateLimitError(429, "too fast")
        assert err.retry_after is None

    def test_catching_moltgrid_error_catches_subclasses(self):
        with pytest.raises(MoltGridError):
            raise RateLimitError(429, "rate limited")

    def test_catching_api_error_catches_subclasses(self):
        with pytest.raises(APIError):
            raise NotFoundError(404, "not found")

    def test_status_map_contains_expected_codes(self):
        assert _STATUS_MAP[429] is RateLimitError
        assert _STATUS_MAP[401] is AuthenticationError
        assert _STATUS_MAP[404] is NotFoundError
        assert _STATUS_MAP[422] is ValidationError


# ------------------------------------------------------------------ #
# Async client -- retry logic
# ------------------------------------------------------------------ #


def _mock_response(status_code: int, json_data=None, headers=None):
    """Build a fake httpx.Response-like object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.is_success = 200 <= status_code < 300
    resp.headers = headers or {}
    resp.json.return_value = json_data or {}
    resp.text = ""
    return resp


class TestAsyncClientRetry:
    """Verify retry behaviour on 429/503 and no-retry on other codes."""

    @pytest.mark.asyncio
    async def test_retries_on_429(self):
        from moltgrid.async_client import AsyncMoltGrid

        client = AsyncMoltGrid("test-key", base_url="https://test.local")
        r429 = _mock_response(429, headers={"Retry-After": "0"})
        r200 = _mock_response(200, json_data={"ok": True})

        mock_request = AsyncMock(side_effect=[r429, r429, r200])
        client._client = MagicMock()
        client._client.request = mock_request

        with patch("moltgrid.async_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client._request("GET", "/v1/test")

        assert result == {"ok": True}
        assert mock_request.call_count == 3

    @pytest.mark.asyncio
    async def test_retries_on_503(self):
        from moltgrid.async_client import AsyncMoltGrid

        client = AsyncMoltGrid("test-key", base_url="https://test.local")
        r503 = _mock_response(503, headers={})
        r200 = _mock_response(200, json_data={"done": True})

        mock_request = AsyncMock(side_effect=[r503, r200])
        client._client = MagicMock()
        client._client.request = mock_request

        with patch("moltgrid.async_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client._request("GET", "/v1/test")

        assert result == {"done": True}
        assert mock_request.call_count == 2

    @pytest.mark.asyncio
    async def test_respects_retry_after_header(self):
        from moltgrid.async_client import AsyncMoltGrid

        client = AsyncMoltGrid("test-key", base_url="https://test.local")
        r429 = _mock_response(429, headers={"Retry-After": "3"})
        r200 = _mock_response(200, json_data={"ok": True})

        mock_request = AsyncMock(side_effect=[r429, r200])
        client._client = MagicMock()
        client._client.request = mock_request

        with patch("moltgrid.async_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client._request("GET", "/v1/test")

        mock_sleep.assert_awaited_once_with(3.0)

    @pytest.mark.asyncio
    async def test_no_retry_on_401(self):
        from moltgrid.async_client import AsyncMoltGrid

        client = AsyncMoltGrid("test-key", base_url="https://test.local")
        r401 = _mock_response(401, json_data={"detail": "unauthorized"})

        mock_request = AsyncMock(return_value=r401)
        client._client = MagicMock()
        client._client.request = mock_request

        with pytest.raises(AuthenticationError) as exc_info:
            await client._request("GET", "/v1/test")

        assert exc_info.value.status_code == 401
        assert mock_request.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_404(self):
        from moltgrid.async_client import AsyncMoltGrid

        client = AsyncMoltGrid("test-key", base_url="https://test.local")
        r404 = _mock_response(404, json_data={"detail": "not found"})

        mock_request = AsyncMock(return_value=r404)
        client._client = MagicMock()
        client._client.request = mock_request

        with pytest.raises(NotFoundError):
            await client._request("GET", "/v1/test")

        assert mock_request.call_count == 1

    @pytest.mark.asyncio
    async def test_no_retry_on_422(self):
        from moltgrid.async_client import AsyncMoltGrid

        client = AsyncMoltGrid("test-key", base_url="https://test.local")
        r422 = _mock_response(422, json_data={"detail": "bad input"})

        mock_request = AsyncMock(return_value=r422)
        client._client = MagicMock()
        client._client.request = mock_request

        with pytest.raises(ValidationError):
            await client._request("GET", "/v1/test")

        assert mock_request.call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exhausted_raises(self):
        from moltgrid.async_client import AsyncMoltGrid

        client = AsyncMoltGrid("test-key", base_url="https://test.local")
        r429 = _mock_response(429, json_data={"detail": "slow down"}, headers={"Retry-After": "0"})

        mock_request = AsyncMock(return_value=r429)
        client._client = MagicMock()
        client._client.request = mock_request

        with patch("moltgrid.async_client.asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(RateLimitError) as exc_info:
                await client._request("GET", "/v1/test")

        assert exc_info.value.status_code == 429
        # initial + 2 retries = 3 total
        assert mock_request.call_count == 3


# ------------------------------------------------------------------ #
# Async client -- method routing
# ------------------------------------------------------------------ #


class TestAsyncClientMethods:
    """Verify async methods call _request with correct paths."""

    @pytest.mark.asyncio
    async def test_memory_set_calls_correct_path(self):
        from moltgrid.async_client import AsyncMoltGrid

        client = AsyncMoltGrid("test-key", base_url="https://test.local")
        client._request = AsyncMock(return_value={"ok": True})

        await client.memory_set("mykey", "myval", namespace="ns")

        client._request.assert_awaited_once()
        args = client._request.call_args
        assert args[0] == ("POST", "/v1/memory")
        body = args[1]["json"]
        assert body["key"] == "mykey"
        assert body["value"] == "myval"
        assert body["namespace"] == "ns"

    @pytest.mark.asyncio
    async def test_memory_get_calls_correct_path(self):
        from moltgrid.async_client import AsyncMoltGrid

        client = AsyncMoltGrid("test-key", base_url="https://test.local")
        client._request = AsyncMock(return_value={"key": "mykey"})

        await client.memory_get("mykey", namespace="ns")

        client._request.assert_awaited_once()
        args = client._request.call_args
        assert args[0] == ("GET", "/v1/memory/mykey")
        assert args[1]["params"]["namespace"] == "ns"

    @pytest.mark.asyncio
    async def test_queue_submit_calls_correct_path(self):
        from moltgrid.async_client import AsyncMoltGrid

        client = AsyncMoltGrid("test-key", base_url="https://test.local")
        client._request = AsyncMock(return_value={"job_id": "j1"})

        await client.queue_submit({"task": "go"}, queue_name="q1")

        client._request.assert_awaited_once()
        args = client._request.call_args
        assert args[0] == ("POST", "/v1/queue/submit")
        assert args[1]["json"]["payload"] == {"task": "go"}
        assert args[1]["json"]["queue_name"] == "q1"

    @pytest.mark.asyncio
    async def test_context_manager(self):
        from moltgrid.async_client import AsyncMoltGrid

        async with AsyncMoltGrid("test-key", base_url="https://test.local") as client:
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_memory_delete_calls_correct_path(self):
        from moltgrid.async_client import AsyncMoltGrid

        client = AsyncMoltGrid("test-key", base_url="https://test.local")
        client._request = AsyncMock(return_value=None)

        await client.memory_delete("mykey", namespace="ns")

        args = client._request.call_args
        assert args[0] == ("DELETE", "/v1/memory/mykey")

    @pytest.mark.asyncio
    async def test_queue_claim_calls_correct_path(self):
        from moltgrid.async_client import AsyncMoltGrid

        client = AsyncMoltGrid("test-key", base_url="https://test.local")
        client._request = AsyncMock(return_value={"job_id": "j1"})

        await client.queue_claim(queue_name="q1")

        args = client._request.call_args
        assert args[0] == ("POST", "/v1/queue/claim")
