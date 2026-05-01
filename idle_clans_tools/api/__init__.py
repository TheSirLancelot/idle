"""Idle Clans API package."""

from .client import IdleClansClient
from .exceptions import (
    IdleClansAPIError,
    NotFoundError,
    RateLimitError,
    NetworkError,
)

__all__ = [
    "IdleClansClient",
    "IdleClansAPIError",
    "NotFoundError",
    "RateLimitError",
    "NetworkError",
]
