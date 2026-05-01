"""Custom exceptions for the Idle Clans API client."""


class IdleClansAPIError(Exception):
    """Base exception for all Idle Clans API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class NotFoundError(IdleClansAPIError):
    """Raised when the requested resource does not exist (HTTP 404)."""


class RateLimitError(IdleClansAPIError):
    """Raised when the API rate limit has been exceeded (HTTP 429)."""


class NetworkError(IdleClansAPIError):
    """Raised when a network-level failure occurs (timeout, connection error)."""
