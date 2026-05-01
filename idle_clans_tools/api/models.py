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
    def from_dict(cls, data: dict[str, Any]) -> PlayerProfile:
        # The API currently exposes player skill xp under "skillExperiences".
        raw_skills = data.get("skills") or data.get("skillExperiences") or {}
        if isinstance(raw_skills, dict):
            skills = {
                str(name): int(value)
                for name, value in raw_skills.items()
                if isinstance(value, (int, float))
            }
        else:
            skills = {}

        total_experience = data.get("totalExperience")
        if not isinstance(total_experience, (int, float)):
            total_experience = sum(skills.values())

        return cls(
            username=data.get("username", ""),
            clan_name=data.get("clanName") or data.get("guildName"),
            total_experience=int(total_experience),
            combat_level=int(data.get("combatLevel", 0) or 0),
            skills=skills,
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
    is_recruiting: bool | None = None
    language: str | None = None
    category: str | None = None
    tag: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClanInfo:
        description = data.get("description") or data.get("recruitmentMessage")
        return cls(
            name=data.get("name") or data.get("clanName", ""),
            leader=data.get("leader", ""),
            member_count=data.get("memberCount", 0),
            total_experience=data.get("totalExperience", 0),
            description=description,
            is_recruiting=data.get("isRecruiting"),
            language=data.get("language"),
            category=data.get("category"),
            tag=data.get("tag"),
        )


@dataclass
class ClanMember:
    """A single member entry inside a clan's member list."""

    username: str
    rank: str
    total_experience: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClanMember:
        rank = data.get("rank")
        if rank is None:
            rank = data.get("memberRank", "")
        return cls(
            username=data.get("username") or data.get("memberName", ""),
            rank=str(rank or ""),
            total_experience=int(data.get("totalExperience", 0) or 0),
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
    def from_dict(cls, data: dict[str, Any]) -> LeaderboardEntry:
        username = data.get("username") or data.get("name") or data.get("clanName", "")
        value = data.get("value")
        if not isinstance(value, (int, float)):
            value = data.get("totalExperience")
        if not isinstance(value, (int, float)):
            fields = data.get("fields")
            if isinstance(fields, dict):
                field_value = next(iter(fields.values()), 0)
                if isinstance(field_value, (int, float)):
                    value = field_value
        if not isinstance(value, (int, float)):
            value = 0

        return cls(
            rank=data.get("rank", 0),
            username=str(username),
            value=int(value),
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
    def from_dict(cls, data: dict[str, Any]) -> MarketItem:
        price = data.get("price")
        if not isinstance(price, (int, float)):
            price = data.get("lowestPrice")
        if not isinstance(price, (int, float)):
            price = data.get("avgPrice24h")
        if not isinstance(price, (int, float)):
            price = 0

        quantity = data.get("quantity")
        if not isinstance(quantity, (int, float)):
            quantity = data.get("volume")
        if not isinstance(quantity, (int, float)):
            quantity = data.get("tradeVolume1d")
        if not isinstance(quantity, (int, float)):
            quantity = 0

        return cls(
            item_id=data.get("itemId", 0),
            item_name=data.get("itemName") or data.get("name", ""),
            price=int(price),
            quantity=int(quantity),
            seller=data.get("seller"),
        )
