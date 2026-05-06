"""Clan lookup page."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import TypeVar, cast

import streamlit as st

from idle_clans_tools.api import IdleClansClient
from idle_clans_tools.api.exceptions import IdleClansAPIError
from idle_clans_tools.api.models import (
    GameItem,
    HouseUpgrade,
    PlayerActivity,
)
from idle_clans_tools.ui.errors import render_api_error
from idle_clans_tools.ui.formatting import format_bool, format_number

_T = TypeVar("_T")


def _open_player_lookup(username: str) -> None:
    st.session_state.pending_player_lookup_username = username
    st.session_state.pending_page = "Player Lookup"


def _format_experience(value: float) -> str:
    return f"{value:,.0f}"


def _format_milliseconds_as_minutes_seconds(value: int) -> str:
    total_seconds = max(0, value) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


def _humanize_task_name(value: str) -> str:
    cleaned = value.strip().replace("_", " ")
    if not cleaned:
        return "—"
    return cleaned.title()


def _infer_house_level(info_skill_levels: dict[int, int], houses: list[HouseUpgrade]) -> int:
    current_level = 0
    for house in houses:
        if all(
            info_skill_levels.get(requirement.skill_id, 0) >= requirement.level
            for requirement in house.skill_requirements
        ):
            current_level = house.level
    return current_level


def _next_house(
    info_skill_levels: dict[int, int], houses: list[HouseUpgrade]
) -> HouseUpgrade | None:
    if not houses:
        return None
    current_level = _infer_house_level(info_skill_levels, houses)
    return next((house for house in houses if house.level == current_level + 1), None)


def _format_item_cost(cost_item_id: int, item_lookup: dict[int, GameItem]) -> str:
    item = item_lookup.get(cost_item_id)
    return item.display_name if item is not None else f"Item {cost_item_id}"


def _cache_key(prefix: str, name: str) -> str:
    return f"{prefix}::data::{name}"


def _get_cached_value(key: str, fetcher: Callable[[], _T]) -> _T:
    if key not in st.session_state:
        st.session_state[key] = fetcher()
    return cast(_T, st.session_state[key])


def _toggle_section(
    prefix: str, section_id: str, label: str, cache_keys: list[str] | None = None
) -> bool:
    state_key = f"{prefix}::show::{section_id}"
    if state_key not in st.session_state:
        st.session_state[state_key] = False
    button_label = f"Hide {label}" if st.session_state[state_key] else f"Show {label}"
    if st.button(button_label, key=f"{prefix}::toggle::{section_id}", width="stretch"):
        st.session_state[state_key] = not st.session_state[state_key]
        if cache_keys:
            data_prefix = f"{prefix}::data::"
            for k in list(st.session_state.keys()):
                if not isinstance(k, str) or not k.startswith(data_prefix):
                    continue
                suffix = k[len(data_prefix) :]
                if any(suffix == ck or suffix.startswith(f"{ck}::") for ck in cache_keys):
                    del st.session_state[k]
    return bool(st.session_state[state_key])


def render_clan_lookup(client: IdleClansClient) -> None:
    st.header("Clan Lookup")

    active_clan_name = st.session_state.get("active_clan_lookup_name")

    with st.form("clan-lookup-form"):
        clan_name = st.text_input(
            "Clan Name",
            key="clan_lookup_name",
            placeholder="Enter an exact Idle Clans clan name",
        )
        include_members = st.checkbox("Show member list", value=True)
        submitted = st.form_submit_button("Look Up Clan", type="primary")

    if submitted:
        clan_name = clan_name.strip()
        if clan_name:
            st.session_state.active_clan_lookup_name = clan_name
            active_clan_name = clan_name

    if not active_clan_name:
        return

    section_prefix = f"clan-lookup::{active_clan_name}"

    with st.spinner("Fetching clan information..."):
        try:
            info = _get_cached_value(
                _cache_key(section_prefix, "info"),
                lambda: client.get_clan_info(active_clan_name),
            )
        except IdleClansAPIError as exc:
            render_api_error(exc)
            return

    st.subheader(info.name or active_clan_name)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Members", format_number(info.member_count))
    metric_columns[1].metric(
        "Activity Score",
        info.activity_score if info.activity_score is not None else "N/A",
    )
    metric_columns[2].metric("Recruiting", format_bool(info.is_recruiting))
    metric_columns[3].metric("Tag", info.tag or "None")

    detail_rows = [
        ("Leader", info.leader),
        ("Language", info.language),
        ("Category", info.category),
        ("Message", info.description),
    ]
    for label, value in detail_rows:
        if value:
            st.write(f"**{label}:** {value}")

    if _toggle_section(section_prefix, "house", "House Upgrade", cache_keys=["houses", "items"]):
        st.subheader("House Upgrade")
        with st.spinner("Fetching house upgrade metadata..."):
            try:
                house_upgrades = _get_cached_value(
                    _cache_key(section_prefix, "houses"),
                    client.get_house_upgrades,
                )
                item_lookup = _get_cached_value(
                    _cache_key(section_prefix, "items"),
                    client.get_item_lookup,
                )
            except IdleClansAPIError as exc:
                render_api_error(exc)
                house_upgrades = []
                item_lookup = {}

        if not house_upgrades:
            st.info("No house upgrade metadata was returned.")
        elif not info.skill_levels:
            st.info(
                "No clan skill levels were found in the clan payload, "
                "so house gaps cannot be calculated."
            )
        else:
            current_house_level = info.house_level or _infer_house_level(
                info.skill_levels, house_upgrades
            )
            next_house = next(
                (house for house in house_upgrades if house.level == current_house_level + 1),
                _next_house(info.skill_levels, house_upgrades),
            )

            current_house = next(
                (house for house in house_upgrades if house.level == current_house_level),
                None,
            )

            metric_columns = st.columns(2)
            metric_columns[0].metric(
                "Current Property",
                current_house.display_name if current_house is not None else "Unknown",
            )
            metric_columns[1].metric(
                "Next Property",
                next_house.display_name if next_house is not None else "Maxed",
            )

            if next_house is None:
                st.success("This clan meets the known skill requirements for the highest house.")
            else:
                st.write(
                    f"**{next_house.display_name}:** "
                    f"{next_house.global_skilling_boost}% global skilling boost, "
                    f"{next_house.inventory_space} inventory spaces"
                )
                requirement_rows = []
                for requirement in sorted(
                    next_house.skill_requirements,
                    key=lambda req: req.skill_name,
                ):
                    current_level = info.skill_levels.get(requirement.skill_id, 0)
                    missing = max(0, requirement.level - current_level)
                    requirement_rows.append(
                        {
                            "Skill": requirement.skill_name,
                            "Current": current_level,
                            "Required": requirement.level,
                            "Missing": missing,
                        }
                    )
                st.dataframe(requirement_rows, hide_index=True, width="stretch")

                cost_rows = [
                    {
                        "Cost": _format_item_cost(cost.item_id, item_lookup),
                        "Amount": format_number(cost.amount),
                    }
                    for cost in next_house.costs
                ]
                cost_rows.insert(
                    0,
                    {
                        "Cost": "Clan Credits",
                        "Amount": format_number(next_house.clan_credit_cost),
                    },
                )
                st.dataframe(cost_rows, hide_index=True, width="stretch")

    if _toggle_section(section_prefix, "cup", "Clan Cup Standings", cache_keys=["cup_standings"]):
        st.subheader("Clan Cup Standings")
        with st.spinner("Fetching Clan Cup standings..."):
            try:
                cup_standings = _get_cached_value(
                    _cache_key(section_prefix, "cup_standings"),
                    lambda: client.get_clan_cup_standings(active_clan_name),
                )
            except IdleClansAPIError as exc:
                render_api_error(exc)
                cup_standings = []

        if cup_standings:
            rows = []
            for standing in cup_standings:
                score_display: str
                if standing.score is not None:
                    score_display = format_number(standing.score)
                elif standing.best_time is not None:
                    score_display = _format_milliseconds_as_minutes_seconds(standing.best_time)
                else:
                    score_display = "—"
                rows.append(
                    {
                        "Category": standing.objective,
                        "Rank": standing.rank if standing.rank else "—",
                        "Score / Time": score_display,
                    }
                )
            st.dataframe(rows, hide_index=True, width="stretch")
        else:
            st.info("No Clan Cup standings found for this clan.")

    if _toggle_section(
        section_prefix, "contributions", "Clan Contributions", cache_keys=["experience_summary"]
    ):
        st.subheader("Clan Contributions")
        hours = st.selectbox(
            "Contribution Window",
            options=[24, 48, 72, 96, 120, 168],
            index=3,
            format_func=lambda value: f"Last {value} hours",
            key=f"{section_prefix}::contribution_hours",
        )
        with st.spinner("Fetching clan contribution data..."):
            try:
                experience_summary = _get_cached_value(
                    _cache_key(section_prefix, f"experience_summary::{hours}"),
                    lambda: client.get_clan_experience_summary(active_clan_name, hours=hours),
                )
            except IdleClansAPIError as exc:
                render_api_error(exc)
                experience_summary = None

        if experience_summary is not None:
            available_skills = sorted(experience_summary.skill_totals, key=str.casefold)
            if available_skills and experience_summary.player_contributions:
                default_skill = (
                    "Woodcutting" if "Woodcutting" in available_skills else available_skills[0]
                )
                skill = st.selectbox(
                    "Skill",
                    options=available_skills,
                    index=available_skills.index(default_skill),
                    key=f"{section_prefix}::contribution_skill",
                )
                contribution_rows = []
                for player in experience_summary.player_contributions:
                    skill_snapshot = player.skills.get(skill)
                    skill_experience = (
                        skill_snapshot.experience if skill_snapshot is not None else 0.0
                    )
                    if skill_experience <= 0:
                        continue
                    contribution_rows.append(
                        {
                            "Username": player.username,
                            f"{skill} XP": skill_experience,
                            f"{skill} Level": (
                                skill_snapshot.level if skill_snapshot is not None else 0
                            ),
                        }
                    )
                contribution_rows.sort(key=lambda row: row[f"{skill} XP"], reverse=True)
                if contribution_rows:
                    top_player = contribution_rows[0]
                    metric_columns = st.columns(2)
                    metric_columns[0].metric("Top Contributor", top_player["Username"])
                    metric_columns[1].metric(
                        f"Top {skill} XP",
                        _format_experience(top_player[f"{skill} XP"]),
                    )

                    formatted_rows = [
                        {
                            "Username": row["Username"],
                            f"{skill} XP": _format_experience(row[f"{skill} XP"]),
                            f"{skill} Level": row[f"{skill} Level"],
                        }
                        for row in contribution_rows
                    ]
                    st.dataframe(formatted_rows, hide_index=True, width="stretch")
                else:
                    st.info(f"No {skill} contributions were found in the selected time window.")
            else:
                st.info("No clan contribution data was returned for the selected time window.")

    members = []
    if include_members and _toggle_section(
        section_prefix, "members", "Members", cache_keys=["members"]
    ):
        st.subheader("Members")
        with st.spinner("Fetching clan members..."):
            try:
                members = _get_cached_value(
                    _cache_key(section_prefix, "members"),
                    lambda: client.get_clan_members(active_clan_name),
                )
            except IdleClansAPIError as exc:
                render_api_error(exc)
                members = []

        if members:
            member_rows = [{"Rank": member.rank, "Username": member.username} for member in members]
            st.dataframe(member_rows, hide_index=True, width="stretch")
            with st.expander("Open member in Player Lookup"):
                cols = st.columns(4)
                for index, member in enumerate(members):
                    cols[index % 4].button(
                        member.username,
                        key=f"clan-member-{index}-{member.username}",
                        on_click=_open_player_lookup,
                        args=(member.username,),
                        width="stretch",
                    )
        else:
            st.info("No members were returned for this clan.")

    if include_members and _toggle_section(
        section_prefix,
        "activity",
        "Current Clan Activity",
        cache_keys=["activities", "simple_profiles", "activity_details", "members"],
    ):
        st.subheader("Current Clan Activity")
        if not members:
            with st.spinner("Fetching clan members..."):
                try:
                    members = _get_cached_value(
                        _cache_key(section_prefix, "members"),
                        lambda: client.get_clan_members(active_clan_name),
                    )
                except IdleClansAPIError as exc:
                    render_api_error(exc)
                    members = []

        if members:
            with st.spinner("Fetching member activities..."):
                try:
                    member_names = [m.username for m in members]
                    activities = _get_cached_value(
                        _cache_key(section_prefix, "activities"),
                        lambda: client.get_player_activities(member_names),
                    )
                    simple_profiles = _get_cached_value(
                        _cache_key(section_prefix, "simple_profiles"),
                        lambda: client.get_player_simple_profiles(member_names),
                    )
                    activity_details = _get_cached_value(
                        _cache_key(section_prefix, "activity_details"),
                        lambda: client.get_player_activity_details(activities),
                    )
                except IdleClansAPIError as exc:
                    render_api_error(exc)
                    activities = {}
                    simple_profiles = {}
                    activity_details = {}

            if activities:
                activity_rows = []
                for member in members:
                    act = activities.get(member.username)
                    profile = simple_profiles.get(member.username)
                    raw_detail = activity_details.get(member.username, "")
                    detail = _humanize_task_name(raw_detail) if raw_detail else "—"

                    if act is not None:
                        activity_label = act.skill_label
                    elif profile and profile.task_type_on_logout is not None:
                        activity_label = PlayerActivity(
                            activity_type=1,
                            task_type=profile.task_type_on_logout,
                            activity_identifier_id=0,
                            start_time=None,
                        ).skill_label
                    else:
                        activity_label = "—"

                    if activity_label != "—" and detail != "—":
                        activity_label = f"{activity_label} ({detail})"
                    activity_rows.append(
                        {
                            "Member": member.username,
                            "Activity": activity_label,
                        }
                    )
                activity_rows.sort(key=lambda r: r["Activity"])
                st.dataframe(activity_rows, hide_index=True, width="stretch")
            else:
                st.info("No activity data returned for this clan's members.")
        else:
            st.info("No members were returned for this clan.")

    if _toggle_section(section_prefix, "upgrades", "Clan Upgrades", cache_keys=["upgrade_lookup"]):
        st.subheader("Clan Upgrades")
        with st.spinner("Fetching clan upgrade metadata..."):
            try:
                upgrade_lookup = _get_cached_value(
                    _cache_key(section_prefix, "upgrade_lookup"),
                    client.get_clan_upgrade_lookup,
                )
            except IdleClansAPIError as exc:
                render_api_error(exc)
                upgrade_lookup = {}

        if info.upgrade_ids or info.repeatable_upgrade_counts:
            upgrade_rows = [
                {"Upgrade": upgrade_lookup.get(uid, f"Upgrade {uid}"), "Count": 1}
                for uid in sorted(info.upgrade_ids, key=lambda i: upgrade_lookup.get(i, ""))
            ]
            for raw_key, count in sorted(info.repeatable_upgrade_counts.items()):
                name = (
                    raw_key.replace("clan_upgrade_", "")
                    .removesuffix("_description")
                    .removesuffix("_desc")
                    .replace("_", " ")
                    .title()
                )
                upgrade_rows.append({"Upgrade": name, "Count": count})
            st.dataframe(upgrade_rows, hide_index=True, width="stretch")
        else:
            st.info("No upgrade data found for this clan.")

    if _toggle_section(section_prefix, "raw", "Raw Clan Data"):
        with st.expander("Raw clan data", expanded=True):
            cached_members = cast(
                list,
                st.session_state.get(_cache_key(section_prefix, "members"), []),
            )
            cached_cup = cast(
                list,
                st.session_state.get(_cache_key(section_prefix, "cup_standings"), []),
            )
            experience_summary = st.session_state.get(
                _cache_key(section_prefix, "experience_summary::96")
            )
            st.json(
                {
                    "info": asdict(info),
                    "members": [asdict(member) for member in cached_members],
                    "cup_standings": [asdict(s) for s in cached_cup],
                    "experience_summary_96h": (
                        asdict(experience_summary) if experience_summary is not None else None
                    ),
                }
            )
