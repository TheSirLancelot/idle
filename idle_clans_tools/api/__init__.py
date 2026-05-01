"""Idle Clans API package."""

from .client import IdleClansClient
from .exceptions import (
    IdleClansAPIError,
    NetworkError,
    NotFoundError,
    RateLimitError,
)

__all__ = [
    "IdleClansClient",
    "IdleClansAPIError",
    "NotFoundError",
    "RateLimitError",
    "NetworkError",
]
