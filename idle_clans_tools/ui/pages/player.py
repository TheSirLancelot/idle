"""Player lookup page."""

from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from idle_clans_tools.api import IdleClansClient
from idle_clans_tools.api.exceptions import IdleClansAPIError
from idle_clans_tools.api.levels import level_for_experience, level_progress_percent
from idle_clans_tools.api.models import GameItem, PlayerProfile
from idle_clans_tools.ui.errors import render_api_error
from idle_clans_tools.ui.formatting import format_number


def _format_optional(value: object) -> str:
    return str(value) if value is not None and value != "" else "None"


def _skill_level(skills: dict[str, int], skill: str) -> int | None:
    xp = skills.get(skill)
    if xp is None:
        return None
    return level_for_experience(xp)


def _format_level(level: int | None) -> str:
    return str(level) if level is not None else "Unknown"


def _total_level(skills: dict[str, int]) -> int:
    return sum(level_for_experience(xp) for xp in skills.values())


def _max_total_level(skills: dict[str, int]) -> int:
    return len(skills) * 120


def render_player_lookup(client: IdleClansClient) -> None:
    st.header("Player Lookup")

    pending_username = st.session_state.pop("pending_player_lookup_username", None)
    if pending_username:
        st.session_state.player_lookup_username = pending_username

    with st.form("player-lookup-form"):
        username = st.text_input(
            "Username",
            key="player_lookup_username",
            placeholder="Enter an Idle Clans username",
        )
        submitted = st.form_submit_button("Look Up Player", type="primary")

    if not submitted and not pending_username:
        return

    username = username.strip()
    if not username:
        st.warning("Enter a username to look up a player.")
        return

    with st.spinner("Fetching player profile..."):
        try:
            profile = client.get_player_profile(username)
        except IdleClansAPIError as exc:
            render_api_error(exc)
            return

    item_lookup = _get_item_lookup(client)
    _render_player_profile(profile, item_lookup)

    with st.expander("Raw profile data"):
        st.json(asdict(profile))


def _get_item_lookup(client: IdleClansClient) -> dict[int, GameItem]:
    try:
        return client.get_item_lookup()
    except IdleClansAPIError:
        st.warning("Could not load item names from game-data. Showing equipment IDs only.")
        return {}


def _render_player_profile(profile: PlayerProfile, item_lookup: dict[int, GameItem]) -> None:
    st.subheader(profile.username or "Unknown player")

    metric_columns = st.columns(4)
    metric_columns[0].metric("Clan", profile.clan_name or "None")
    metric_columns[1].metric("Game Mode", profile.game_mode or "Unknown")
    metric_columns[2].metric(
        "Total Level",
        f"{format_number(_total_level(profile.skills))}/{format_number(_max_total_level(profile.skills))}",
    )
    metric_columns[3].metric("Total XP", format_number(profile.total_experience))

    combat_columns = st.columns(6)
    combat_columns[0].metric("Attack", _format_level(_skill_level(profile.skills, "attack")))
    combat_columns[1].metric("Strength", _format_level(_skill_level(profile.skills, "strength")))
    combat_columns[2].metric("Archery", _format_level(_skill_level(profile.skills, "archery")))
    combat_columns[3].metric("Magic", _format_level(_skill_level(profile.skills, "magic")))
    combat_columns[4].metric("Defense", _format_level(_skill_level(profile.skills, "defence")))
    combat_columns[5].metric("Health", _format_level(_skill_level(profile.skills, "health")))

    detail_rows = [
        {"Field": "Hours Offline", "Value": _format_optional(profile.hours_offline)},
        {"Field": "Logout Task Type", "Value": _format_optional(profile.task_type_on_logout)},
        {"Field": "Logout Task Name", "Value": _format_optional(profile.task_name_on_logout)},
        {"Field": "Active Server ID", "Value": _format_optional(profile.active_server_id)},
    ]
    st.dataframe(detail_rows, hide_index=True, use_container_width=True)

    tabs = st.tabs(["Skills", "Equipment", "Enchantments", "Upgrades", "PvM Stats"])
    with tabs[0]:
        _render_skill_table(profile.skills)
    with tabs[1]:
        _render_equipment_table(profile.equipment, item_lookup)
    with tabs[2]:
        _render_mapping_table(
            profile.enchantment_boosts,
            "Skill",
            "Boost",
            empty_message="No enchantment boost data returned.",
        )
    with tabs[3]:
        _render_mapping_table(
            profile.upgrades,
            "Upgrade",
            "Level",
            empty_message="No upgrade data returned.",
        )
    with tabs[4]:
        _render_mapping_table(
            profile.pvm_stats,
            "Enemy",
            "Kills",
            empty_message="No PvM stat data returned.",
        )


def _render_mapping_table(
    values: dict[str, int],
    key_label: str,
    value_label: str,
    *,
    empty_message: str,
) -> None:
    if not values:
        st.info(empty_message)
        return

    rows = [
        {key_label: key, value_label: value}
        for key, value in sorted(values.items(), key=lambda item: item[0].casefold())
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)


def _render_skill_table(skills: dict[str, int]) -> None:
    if not skills:
        st.info("No skill data returned.")
        return

    rows = [
        {
            "Skill": skill,
            "Level": level_for_experience(xp),
            "Next Level": f"{level_progress_percent(xp):.2f}%",
            "XP": xp,
        }
        for skill, xp in sorted(skills.items(), key=lambda item: item[0].casefold())
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)


def _render_equipment_table(equipment: dict[str, int], item_lookup: dict[int, GameItem]) -> None:
    if not equipment:
        st.info("No equipment data returned.")
        return

    rows = []
    for slot, item_id in sorted(equipment.items(), key=lambda item: item[0].casefold()):
        item = item_lookup.get(item_id)
        if item_id < 0:
            item_name = "Empty"
        elif item is None:
            item_name = "Unknown"
        else:
            item_name = item.display_name
        rows.append({"Slot": slot, "Item": item_name})

    st.dataframe(rows, hide_index=True, use_container_width=True)
