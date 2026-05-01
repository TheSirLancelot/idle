"""Data models for Idle Clans API responses.

All models use dataclasses with type hints so they're easy to extend and
introspect.  The ``from_dict`` class-methods accept the raw JSON dicts
returned by the API and pull out only the fields we care about; unknown keys
are ignored so the models stay forward-compatible.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Player models
# ---------------------------------------------------------------------------


@dataclass
class PlayerProfile:
    """Profile information for a single player."""

    username: str
    clan_name: str | None
    total_experience: int
    combat_level: int
    skills: dict[str, int] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlayerProfile":
        return cls(
            username=data.get("username", ""),
            clan_name=data.get("clanName"),
            total_experience=data.get("totalExperience", 0),
            combat_level=data.get("combatLevel", 0),
            skills=data.get("skills", {}),
        )


# ---------------------------------------------------------------------------
# Clan models
# ---------------------------------------------------------------------------


@dataclass
class ClanInfo:
    """Basic information about a clan."""

    name: str
    leader: str
    member_count: int
    total_experience: int
    description: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClanInfo":
        return cls(
            name=data.get("name", ""),
            leader=data.get("leader", ""),
            member_count=data.get("memberCount", 0),
            total_experience=data.get("totalExperience", 0),
            description=data.get("description"),
        )


@dataclass
class ClanMember:
    """A single member entry inside a clan's member list."""

    username: str
    rank: str
    total_experience: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ClanMember":
        return cls(
            username=data.get("username", ""),
            rank=data.get("rank", ""),
            total_experience=data.get("totalExperience", 0),
        )


# ---------------------------------------------------------------------------
# Leaderboard models
# ---------------------------------------------------------------------------


@dataclass
class LeaderboardEntry:
    """A single entry on a leaderboard."""

    rank: int
    username: str
    value: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LeaderboardEntry":
        return cls(
            rank=data.get("rank", 0),
            username=data.get("username", ""),
            value=data.get("value", 0),
        )


# ---------------------------------------------------------------------------
# Market / item models
# ---------------------------------------------------------------------------


@dataclass
class MarketItem:
    """A single item listing on the player market."""

    item_id: int
    item_name: str
    price: int
    quantity: int
    seller: str | None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MarketItem":
        return cls(
            item_id=data.get("itemId", 0),
            item_name=data.get("itemName", ""),
            price=data.get("price", 0),
            quantity=data.get("quantity", 0),
            seller=data.get("seller"),
        )
