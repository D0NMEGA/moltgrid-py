"""MoltGrid SDK exception hierarchy.

Hierarchy::

    MoltGridError (base)
      +-- APIError (HTTP errors)
            +-- RateLimitError (429)
            +-- AuthenticationError (401)
            +-- NotFoundError (404)
            +-- ValidationError (422)
"""

from __future__ import annotations

from typing import Any, Dict, Optional


class MoltGridError(Exception):
    """Raised when the MoltGrid API returns a 4xx/5xx response."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        response: Any = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.response = response
        super().__init__(f"MoltGrid API error {status_code}: {detail}")


class APIError(MoltGridError):
    """Base class for typed HTTP API errors."""


class RateLimitError(APIError):
    """Raised on HTTP 429 -- Too Many Requests."""

    def __init__(
        self,
        status_code: int,
        detail: str,
        response: Any = None,
        retry_after: Optional[float] = None,
    ) -> None:
        super().__init__(status_code, detail, response)
        self.retry_after = retry_after


class AuthenticationError(APIError):
    """Raised on HTTP 401 -- Unauthorized."""


class NotFoundError(APIError):
    """Raised on HTTP 404 -- Not Found."""


class ValidationError(APIError):
    """Raised on HTTP 422 -- Unprocessable Entity."""


# Maps HTTP status codes to the appropriate exception class.
_STATUS_MAP: Dict[int, type] = {
    429: RateLimitError,
    401: AuthenticationError,
    404: NotFoundError,
    422: ValidationError,
}
