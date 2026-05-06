"""Data models for Idle Clans API responses.

All models use dataclasses with type hints so they're easy to extend and
introspect.  The ``from_dict`` class-methods accept the raw JSON dicts
returned by the API and pull out only the fields we care about; unknown keys
are ignored so the models stay forward-compatible.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from idle_clans_tools.api.levels import level_for_experience
from idle_clans_tools.api.skills import SKILL_ID_TO_NAME, SKILL_NAME_TO_ID

# ---------------------------------------------------------------------------
# Activity models
# ---------------------------------------------------------------------------


#: Maps the integer ``taskType`` field from the activities endpoint to a
#: human-readable skill label.  Values derived empirically from live API data.
_TASK_TYPE_LABELS: dict[int, str] = {
    1: "Woodcutting",
    2: "Fishing",
    3: "Mining",
    4: "Carpentry",
    6: "Smithing",
    7: "Combat",
    8: "Cooking",
    9: "Foraging",
    13: "Plundering",
    18: "Invocation",
}


@dataclass
class PlayerActivity:
    """Current (or most recent) activity for a single player."""

    activity_type: int
    task_type: int
    activity_identifier_id: int
    start_time: str | None

    @property
    def skill_label(self) -> str:
        """Human-readable label for the activity, derived from activity and task type."""
        if self.activity_type == 0:
            return "Offline"
        if self.task_type == 0:
            return "In Clan Event"
        label = _TASK_TYPE_LABELS.get(self.task_type)
        if label:
            return label
        return f"Activity {self.task_type}"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlayerActivity:
        return cls(
            activity_type=int(data.get("type", 0) or 0),
            task_type=int(data.get("taskType", 0) or 0),
            activity_identifier_id=int(data.get("activityIdentifierId", 0) or 0),
            start_time=data.get("startTime"),
        )


def _optional_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    return None


def _get_first(data: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in data:
            return data[key]
    return None


# ---------------------------------------------------------------------------
# Player models
# ---------------------------------------------------------------------------


@dataclass
class PlayerProfile:
    """Profile information for a single player."""

    username: str
    game_mode: str | None
    clan_name: str | None
    total_experience: int
    combat_level: int
    skills: dict[str, int] = field(default_factory=dict)
    equipment: dict[str, int] = field(default_factory=dict)
    enchantment_boosts: dict[str, int] = field(default_factory=dict)
    upgrades: dict[str, int] = field(default_factory=dict)
    pvm_stats: dict[str, int] = field(default_factory=dict)
    hours_offline: int | float | None = None
    task_type_on_logout: int | None = None
    task_name_on_logout: str | None = None
    active_server_id: str | int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlayerProfile:
        # The API currently exposes player skill xp under "skillExperiences".
        skills = _numeric_map(data.get("skills") or data.get("skillExperiences"))

        total_experience = data.get("totalExperience")
        if not isinstance(total_experience, (int, float)):
            total_experience = sum(skills.values())

        return cls(
            username=data.get("username", ""),
            game_mode=data.get("gameMode"),
            clan_name=data.get("clanName") or data.get("guildName"),
            total_experience=int(total_experience),
            combat_level=int(data.get("combatLevel", 0) or 0),
            skills=skills,
            equipment=_numeric_map(data.get("equipment")),
            enchantment_boosts=_numeric_map(data.get("enchantmentBoosts")),
            upgrades=_numeric_map(data.get("upgrades")),
            pvm_stats=_numeric_map(data.get("pvmStats")),
            hours_offline=_optional_number(data.get("hoursOffline")),
            task_type_on_logout=_optional_int(data.get("taskTypeOnLogout")),
            task_name_on_logout=data.get("taskNameOnLogout"),
            active_server_id=data.get("activeServerId"),
        )


def _numeric_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {
        str(name): int(raw_value)
        for name, raw_value in value.items()
        if isinstance(raw_value, (int, float))
    }


def _skill_level_map(value: Any, *, values_are_experience: bool = False) -> dict[int, int]:
    if not isinstance(value, dict):
        return {}

    result: dict[int, int] = {}
    for name, raw_value in value.items():
        if not isinstance(raw_value, (int, float)):
            continue
        try:
            key = int(name)
        except (TypeError, ValueError):
            key = SKILL_NAME_TO_ID.get(str(name).casefold())
        if key is not None:
            result[key] = (
                level_for_experience(raw_value) if values_are_experience else int(raw_value)
            )
    return result


def _json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str):
        return {}
    try:
        data = json.loads(value)
    except (json.JSONDecodeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _optional_int(value: Any) -> int | None:
    if isinstance(value, (int, float)):
        return int(value)
    return None


def _optional_number(value: Any) -> int | float | None:
    if not isinstance(value, (int, float)):
        return None
    if isinstance(value, float) and not value.is_integer():
        return value
    return int(value)


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
    activity_score: float | None = None
    upgrade_ids: list[int] = field(default_factory=list)
    repeatable_upgrade_counts: dict[str, int] = field(default_factory=dict)
    skill_levels: dict[int, int] = field(default_factory=dict)
    house_level: int | None = None
    clan_credits: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClanInfo:
        description = data.get("description") or data.get("recruitmentMessage")
        member_count = data.get("memberCount") or len(data.get("memberlist") or [])
        total_experience = data.get("totalExperience")

        raw_upgrades = data.get("serializedUpgrades") or []
        if isinstance(raw_upgrades, str):
            try:
                raw_upgrades = json.loads(raw_upgrades)
            except (json.JSONDecodeError, ValueError):
                raw_upgrades = []
        upgrade_ids = [int(v) for v in raw_upgrades if isinstance(v, (int, float))]

        raw_repeatable = data.get("repeatableUpgradeCounts") or {}
        repeatable_upgrade_counts = {
            str(k): int(v) for k, v in raw_repeatable.items() if isinstance(v, (int, float))
        }

        raw_skill_levels = data.get("skillLevels") or data.get("clanSkillLevels")
        skill_levels = _skill_level_map(raw_skill_levels)
        if not skill_levels:
            raw_serialized_skill_levels = data.get("serializedSkillLevels")
            skill_levels = _skill_level_map(
                _json_object(raw_serialized_skill_levels) or raw_serialized_skill_levels
            )
        if not skill_levels:
            raw_serialized_skills = data.get("serializedSkills") or data.get("skills")
            skill_levels = _skill_level_map(
                _json_object(raw_serialized_skills) or raw_serialized_skills,
                values_are_experience=True,
            )

        raw_house_id = _optional_int(data.get("houseId"))
        house_level = (
            raw_house_id + 1
            if raw_house_id is not None
            else _optional_int(_get_first(data, "houseLevel", "guildHouseLevel", "guildHouse"))
        )

        return cls(
            name=data.get("name") or data.get("clanName", ""),
            leader=data.get("leader") or "",
            member_count=int(member_count or 0),
            total_experience=int(total_experience or 0),
            description=description,
            is_recruiting=data.get("isRecruiting"),
            language=data.get("language"),
            category=data.get("category"),
            tag=data.get("tag"),
            activity_score=data.get("activityScore"),
            upgrade_ids=upgrade_ids,
            repeatable_upgrade_counts=repeatable_upgrade_counts,
            skill_levels=skill_levels,
            house_level=house_level,
            clan_credits=_optional_int(_get_first(data, "clanCredits", "credits")),
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


@dataclass
class SkillExperienceSnapshot:
    """A skill's experience and level snapshot within a clan summary."""

    experience: float
    level: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillExperienceSnapshot:
        experience = data.get("experience")
        if not isinstance(experience, (int, float)):
            experience = 0

        return cls(
            experience=float(experience),
            level=int(data.get("level", 0) or 0),
        )


@dataclass
class ClanPlayerContribution:
    """A player's contribution inside a clan experience summary."""

    username: str
    total_experience: float
    skills: dict[str, SkillExperienceSnapshot] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClanPlayerContribution:
        _SKILL_NAME_ALIASES = {"Rigour": "Attack"}
        raw_skills = data.get("skills") or {}
        skills = {
            _SKILL_NAME_ALIASES.get(str(name), str(name)): SkillExperienceSnapshot.from_dict(value)
            for name, value in raw_skills.items()
            if isinstance(value, dict)
        }

        total_experience = data.get("totalExperience")
        if not isinstance(total_experience, (int, float)):
            total_experience = sum(skill.experience for skill in skills.values())

        return cls(
            username=str(data.get("username") or ""),
            total_experience=float(total_experience),
            skills=skills,
        )


@dataclass
class ClanExperienceSummary:
    """Experience totals and per-player contributions for a clan."""

    clan_name: str
    period_hours: int
    total_experience: float
    skill_totals: dict[str, float] = field(default_factory=dict)
    player_contributions: list[ClanPlayerContribution] = field(default_factory=list)
    interval_count: int = 0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClanExperienceSummary:
        _SKILL_NAME_ALIASES = {"Rigour": "Attack"}
        raw_skill_totals = data.get("skillTotals") or {}
        skill_totals = {
            _SKILL_NAME_ALIASES.get(str(name), str(name)): float(value)
            for name, value in raw_skill_totals.items()
            if isinstance(value, (int, float))
        }

        raw_player_contributions = data.get("playerContributions") or []
        player_contributions = [
            ClanPlayerContribution.from_dict(entry)
            for entry in raw_player_contributions
            if isinstance(entry, dict)
        ]

        total_experience = data.get("totalExperience")
        if not isinstance(total_experience, (int, float)):
            total_experience = sum(skill_totals.values())

        return cls(
            clan_name=str(data.get("clanName") or ""),
            period_hours=int(data.get("periodHours", 0) or 0),
            total_experience=float(total_experience),
            skill_totals=skill_totals,
            player_contributions=player_contributions,
            interval_count=int(data.get("intervalCount", 0) or 0),
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
# Clan Cup models
# ---------------------------------------------------------------------------


@dataclass
class ClanCupStanding:
    """A clan's standing in a single Clan Cup objective category."""

    objective: str
    rank: int
    score: int | None = None
    best_time: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClanCupStanding:
        best_time_info = data.get("bestTime")
        best_time: int | None = None
        if isinstance(best_time_info, dict):
            best_time = _optional_int(best_time_info.get("time"))

        score = _optional_int(data.get("score"))

        return cls(
            objective=data.get("objective", ""),
            rank=int(data.get("rank", 0) or 0),
            score=score,
            best_time=best_time,
        )


# ---------------------------------------------------------------------------
# House models
# ---------------------------------------------------------------------------


@dataclass
class HouseCost:
    """An item quantity required for a clan house upgrade."""

    item_id: int
    amount: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HouseCost:
        return cls(
            item_id=_optional_int(_get_first(data, "Item", "item")) or 0,
            amount=_optional_int(_get_first(data, "Amount", "amount")) or 0,
        )


@dataclass
class HouseSkillRequirement:
    """A clan skill level requirement for a clan house upgrade."""

    skill_id: int
    level: int

    @property
    def skill_name(self) -> str:
        return SKILL_ID_TO_NAME.get(self.skill_id, f"Skill {self.skill_id}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HouseSkillRequirement:
        return cls(
            skill_id=_optional_int(_get_first(data, "Skill", "skill")) or 0,
            level=_optional_int(_get_first(data, "Level", "level")) or 0,
        )


@dataclass
class HouseUpgrade:
    """Static metadata for one clan house tier."""

    level: int
    name: str
    clan_credit_cost: int
    inventory_space: int
    global_skilling_boost: int
    costs: list[HouseCost] = field(default_factory=list)
    skill_requirements: list[HouseSkillRequirement] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        property_names = {
            1: "Tent",
            2: "Barn",
            3: "Windmill",
            4: "House",
            5: "Manor",
            6: "Castle",
        }
        if self.level in property_names:
            return property_names[self.level]
        return self.name.replace("_", " ").title()

    @classmethod
    def from_dict(cls, data: dict[str, Any], level: int) -> HouseUpgrade:
        raw_costs = data.get("Costs") or data.get("costs") or []
        raw_skill_requirements = (
            data.get("SkillRequirements") or data.get("skillRequirements") or []
        )
        return cls(
            level=level,
            name=str(_get_first(data, "Name", "name") or f"guild_house_{level}"),
            clan_credit_cost=_optional_int(
                _get_first(data, "ClanCreditCost", "clanCreditCost")
            )
            or 0,
            inventory_space=_optional_int(_get_first(data, "InventorySpace", "inventorySpace"))
            or 0,
            global_skilling_boost=_optional_int(
                _get_first(data, "GlobalSkillingBoost", "globalSkillingBoost")
            )
            or 0,
            costs=[
                HouseCost.from_dict(entry) for entry in raw_costs if isinstance(entry, dict)
            ],
            skill_requirements=[
                HouseSkillRequirement.from_dict(entry)
                for entry in raw_skill_requirements
                if isinstance(entry, dict)
            ],
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


@dataclass
class GameItem:
    """Static item metadata from the game-data endpoint."""

    item_id: int
    name: str
    base_value: int
    category: int | None = None
    equipment_slot: int | None = None
    associated_skill: int | None = None
    is_tool: bool | None = None
    discontinued: bool | None = None
    unobtainable: bool | None = None

    @property
    def display_name(self) -> str:
        return self.name.replace("_", " ").title()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameItem:
        return cls(
            item_id=_optional_int(_get_first(data, "ItemId", "itemId")) or 0,
            name=str(_get_first(data, "Name", "itemName", "name") or ""),
            base_value=_optional_int(_get_first(data, "BaseValue", "baseValue")) or 0,
            category=_optional_int(_get_first(data, "Category", "category")),
            equipment_slot=_optional_int(_get_first(data, "EquipmentSlot", "equipmentSlot")),
            associated_skill=_optional_int(_get_first(data, "AssociatedSkill", "associatedSkill")),
            is_tool=_optional_bool(_get_first(data, "IsTool", "isTool")),
            discontinued=_optional_bool(_get_first(data, "Discontinued", "discontinued")),
            unobtainable=_optional_bool(_get_first(data, "Unobtainable", "unobtainable")),
        )
