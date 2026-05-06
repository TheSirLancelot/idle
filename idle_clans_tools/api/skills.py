"""Skill identifiers used by Idle Clans static game data."""

from __future__ import annotations

SKILL_ID_TO_NAME: dict[int, str] = {
    1: "Rigour",
    2: "Strength",
    3: "Defence",
    4: "Archery",
    5: "Magic",
    6: "Health",
    7: "Crafting",
    8: "Woodcutting",
    9: "Carpentry",
    10: "Fishing",
    11: "Cooking",
    12: "Mining",
    13: "Smithing",
    14: "Foraging",
    15: "Farming",
    16: "Agility",
    17: "Plundering",
    18: "Enchanting",
    19: "Brewing",
    21: "Invocation",
}

SKILL_NAME_TO_ID: dict[str, int] = {
    name.casefold(): skill_id for skill_id, name in SKILL_ID_TO_NAME.items()
}

