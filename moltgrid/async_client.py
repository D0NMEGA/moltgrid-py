"""Async MoltGrid client -- mirrors the sync MoltGrid class using httpx."""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None  # type: ignore[assignment]

from .exceptions import (
    APIError,
    RateLimitError,
    _STATUS_MAP,
)

__all__ = ["AsyncMoltGrid"]

# Status codes that trigger automatic retry.
_RETRYABLE_STATUSES = frozenset({429, 503})


class AsyncMoltGrid:
    """Asynchronous client for the MoltGrid agent infrastructure API.

    Uses ``httpx.AsyncClient`` under the hood. Supports ``async with``
    context-manager usage for automatic resource cleanup.

    Parameters
    ----------
    api_key : str, optional
        API key for authentication.  Falls back to the ``MOLTGRID_API_KEY``
        environment variable when not provided.
    base_url : str
        Root URL of the MoltGrid API (no trailing slash).
    timeout : float
        Default request timeout in seconds.
    max_retries : int
        Maximum number of retries on 429/503 responses (default 2).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.moltgrid.net",
        timeout: float = 30.0,
        max_retries: int = 2,
    ) -> None:
        if httpx is None:
            raise ImportError(
                "Install httpx for async support: pip install moltgrid[async]"
            )

        self.api_key: str = api_key or os.environ.get("MOLTGRID_API_KEY", "")
        self.base_url: str = base_url.rstrip("/")
        self.timeout: float = timeout
        self.max_retries: int = max_retries

        self._headers: Dict[str, str] = {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Lazily created in __aenter__ or on first _request call.
        self._client: Optional[httpx.AsyncClient] = None

        # Populated after every request from response headers.
        self._rate_limit_remaining: Optional[int] = None

    # ------------------------------------------------------------------ #
    # Context manager
    # ------------------------------------------------------------------ #

    async def __aenter__(self) -> "AsyncMoltGrid":
        self._client = httpx.AsyncClient(
            headers=self._headers,
            timeout=self.timeout,
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying httpx client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------ #
    # Properties
    # ------------------------------------------------------------------ #

    @property
    def rate_limit_remaining(self) -> Optional[int]:
        """Number of API calls remaining in the current rate-limit window."""
        return self._rate_limit_remaining

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _ensure_client(self) -> httpx.AsyncClient:
        """Return the httpx client, creating one if needed."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                headers=self._headers,
                timeout=self.timeout,
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """Send an HTTP request with automatic retry on transient errors.

        Retries up to ``self.max_retries`` times on 429 and 503 responses,
        using exponential backoff or the server's ``Retry-After`` header.

        Raises a typed exception from :mod:`moltgrid.exceptions` on failure.
        """
        url = f"{self.base_url}{path}"
        client = self._ensure_client()

        # Strip None values from query params.
        if params:
            params = {k: v for k, v in params.items() if v is not None}

        last_resp = None
        for attempt in range(self.max_retries + 1):
            resp = await client.request(
                method, url, params=params, json=json, **kwargs
            )
            last_resp = resp

            # Capture rate-limit header.
            rl = resp.headers.get("X-RateLimit-Remaining")
            if rl is not None:
                try:
                    self._rate_limit_remaining = int(rl)
                except ValueError:
                    pass

            if resp.is_success:
                if resp.status_code == 204 or not resp.content:
                    return None
                return resp.json()

            # Retry only on retryable status codes and if attempts remain.
            if resp.status_code in _RETRYABLE_STATUSES and attempt < self.max_retries:
                retry_after = resp.headers.get("Retry-After")
                if retry_after is not None:
                    delay = float(retry_after)
                else:
                    delay = float(2 ** attempt)  # 1s, 2s
                await asyncio.sleep(delay)
                continue

            # Non-retryable or retries exhausted -- raise typed exception.
            break

        # Extract error detail from response body.
        assert last_resp is not None
        try:
            body = last_resp.json()
            detail = body.get("detail") or body.get("message") or last_resp.text
        except Exception:
            detail = last_resp.text

        exc_cls = _STATUS_MAP.get(last_resp.status_code, APIError)

        if exc_cls is RateLimitError:
            retry_after_hdr = last_resp.headers.get("Retry-After")
            ra_val = float(retry_after_hdr) if retry_after_hdr else None
            raise RateLimitError(
                last_resp.status_code, detail, response=last_resp, retry_after=ra_val
            )

        raise exc_cls(last_resp.status_code, detail, response=last_resp)

    # ================================================================== #
    # MEMORY (key-value store)
    # ================================================================== #

    async def memory_set(
        self,
        key: str,
        value: Any,
        namespace: str = "default",
        ttl_seconds: Optional[int] = None,
        visibility: str = "private",
        shared_agents: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Store a key-value pair.  POST /v1/memory"""
        body: Dict[str, Any] = {
            "key": key,
            "value": value,
            "namespace": namespace,
            "visibility": visibility,
        }
        if ttl_seconds is not None:
            body["ttl_seconds"] = ttl_seconds
        if shared_agents is not None:
            body["shared_agents"] = shared_agents
        return await self._request("POST", "/v1/memory", json=body)

    async def memory_get(
        self, key: str, namespace: str = "default"
    ) -> Dict[str, Any]:
        """Retrieve a memory value.  GET /v1/memory/{key}"""
        return await self._request(
            "GET", f"/v1/memory/{key}", params={"namespace": namespace}
        )

    async def memory_delete(
        self, key: str, namespace: str = "default"
    ) -> Any:
        """Delete a memory key.  DELETE /v1/memory/{key}"""
        return await self._request(
            "DELETE", f"/v1/memory/{key}", params={"namespace": namespace}
        )

    async def memory_list(
        self,
        namespace: str = "default",
        prefix: Optional[str] = None,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """List memory keys.  GET /v1/memory"""
        return await self._request(
            "GET",
            "/v1/memory",
            params={"namespace": namespace, "prefix": prefix, "limit": limit},
        )

    # ================================================================== #
    # QUEUE (task queue)
    # ================================================================== #

    async def queue_submit(
        self,
        payload: Any,
        queue_name: str = "default",
        priority: int = 0,
        max_attempts: int = 1,
        retry_delay_seconds: int = 0,
    ) -> Dict[str, Any]:
        """Submit a job to a queue.  POST /v1/queue/submit"""
        return await self._request(
            "POST",
            "/v1/queue/submit",
            json={
                "payload": payload,
                "queue_name": queue_name,
                "priority": priority,
                "max_attempts": max_attempts,
                "retry_delay_seconds": retry_delay_seconds,
            },
        )

    async def queue_claim(
        self, queue_name: str = "default"
    ) -> Dict[str, Any]:
        """Claim the next job from a queue.  POST /v1/queue/claim"""
        return await self._request(
            "POST", "/v1/queue/claim", params={"queue_name": queue_name}
        )

    async def queue_status(self, job_id: str) -> Dict[str, Any]:
        """Get job status.  GET /v1/queue/{job_id}"""
        return await self._request("GET", f"/v1/queue/{job_id}")

    async def queue_complete(
        self, job_id: str, result: Optional[Any] = None
    ) -> Dict[str, Any]:
        """Mark a job as completed.  POST /v1/queue/{job_id}/complete"""
        params: Dict[str, Any] = {}
        if result is not None:
            params["result"] = result
        return await self._request(
            "POST", f"/v1/queue/{job_id}/complete", params=params
        )

    async def queue_fail(
        self, job_id: str, reason: str = ""
    ) -> Dict[str, Any]:
        """Mark a job as failed.  POST /v1/queue/{job_id}/fail"""
        return await self._request(
            "POST", f"/v1/queue/{job_id}/fail", json={"reason": reason}
        )
