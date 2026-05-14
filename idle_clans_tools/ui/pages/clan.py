"""Clan lookup page."""

from __future__ import annotations

import datetime
import json
from collections.abc import Callable
from dataclasses import asdict
from typing import TypeVar, cast

import streamlit as st

from idle_clans_tools.api import IdleClansClient
from idle_clans_tools.api.exceptions import IdleClansAPIError, NotFoundError
from idle_clans_tools.api.models import (
    ClanInfo,
    GameItem,
    HouseUpgrade,
    PlayerActivity,
)
from idle_clans_tools.ui.errors import render_api_error
from idle_clans_tools.ui.formatting import format_bool, format_number

_T = TypeVar("_T")

_PVM_BOSS_FILTERS: list[str] = [
    "BloodmoonMassacre",
    "Chimera",
    "Devil",
    "Griffin",
    "GuardiansOfTheCitadel",
    "Hades",
    "Kronos",
    "MalignantSpider",
    "Medusa",
    "Mesines",
    "OtherworldlyGolem",
    "ReckoningOfTheGods",
    "SkeletonWarrior",
    "Sobek",
    "Zeus",
]


def _open_player_lookup(username: str) -> None:
    st.session_state.pending_player_lookup_username = username
    st.session_state.pending_page = "Player Lookup"


def _format_experience(value: float) -> str:
    return f"{value:,.0f}"


def _fetch_giveaway_profiles(
    client: IdleClansClient,
    usernames: list[str],
    cache_prefix: str,
) -> dict[str, dict[str, int]]:
    """Fetch skill XP maps for each username, using session-state caching."""
    result: dict[str, dict[str, int]] = {}
    for username in usernames:
        cache_key = f"{cache_prefix}::giveaway_profile::{username}"
        if cache_key not in st.session_state:
            try:
                profile = client.get_player_profile(username)
                # Normalize keys to casefold so lookups are case-insensitive.
                st.session_state[cache_key] = {
                    k.casefold(): v for k, v in profile.skills.items()
                }
            except (IdleClansAPIError, NotFoundError):
                st.session_state[cache_key] = {}
        skills = st.session_state[cache_key]
        if skills:
            result[username] = skills
    return result


def _get_pvm_stat(pvm_stats: dict[str, int], boss: str) -> int:
    """Case-insensitive lookup for a PvM kill count by boss name."""
    needle = boss.casefold()
    for key, value in pvm_stats.items():
        if key.casefold() == needle:
            return value
    return 0


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


def _load_guard(loaded_key: str, button_key: str, label: str, section_prefix: str) -> bool:
    """Show a load button if data hasn't been loaded yet, or a refresh button if already loaded.

    Returns True when the tab should render its content.
    """
    if loaded_key not in st.session_state:
        st.info(f"Click below to load {label}.")
        if st.button(f"Load {label}", key=button_key, type="primary"):
            st.session_state[loaded_key] = True
            st.rerun()
        return False

    # Already loaded — show a small refresh button in the top-right corner.
    if st.button(
        "🔄 Refresh",
        key=f"{button_key}::refresh",
        help=f"Re-fetch {label} data from the API",
    ):
        # Clear the loaded flag and all cached data for this section so everything
        # is re-fetched on the next render.
        keys_to_delete = [
            k for k in st.session_state if k.startswith(f"{section_prefix}::") and (
                k == loaded_key or k.startswith(f"{section_prefix}::data::")
            )
        ]
        for k in keys_to_delete:
            del st.session_state[k]
        st.rerun()
    return True


def _render_overview_tab(
    client: IdleClansClient,
    info: ClanInfo,
    section_prefix: str,
) -> None:
    if not _load_guard(
        f"{section_prefix}::loaded::overview",
        f"{section_prefix}::load_overview",
        "Overview",
        section_prefix,
    ):
        return

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
                next_house.skill_requirements, key=lambda req: req.skill_name
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

    st.divider()
    st.subheader("Clan Cup Standings")
    with st.spinner("Fetching Clan Cup standings..."):
        try:
            cup_standings = _get_cached_value(
                _cache_key(section_prefix, "cup_standings"),
                lambda: client.get_clan_cup_standings(info.name or ""),
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

    st.divider()
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

    with st.expander("🔧 Raw Clan Data"):
        cached_members = cast(
            list,
            st.session_state.get(_cache_key(section_prefix, "members"), []),
        )
        cached_cup = cast(
            list,
            st.session_state.get(_cache_key(section_prefix, "cup_standings"), []),
        )
        raw_exp_summary = st.session_state.get(
            _cache_key(section_prefix, "experience_summary::96")
        )
        st.json(
            {
                "info": asdict(info),
                "members": [asdict(member) for member in cached_members],
                "cup_standings": [asdict(s) for s in cached_cup],
                "experience_summary_96h": (
                    asdict(raw_exp_summary) if raw_exp_summary is not None else None
                ),
            }
        )


def _render_contributions_tab(
    client: IdleClansClient,
    section_prefix: str,
    active_clan_name: str,
) -> None:
    if not _load_guard(
        f"{section_prefix}::loaded::contributions",
        f"{section_prefix}::load_contributions",
        "Contributions",
        section_prefix,
    ):
        return

    st.subheader("Clan Contributions")
    hours = st.selectbox(
        "Contribution Window",
        options=[24, 48, 72, 96, 120, 168],
        index=3,
        format_func=lambda h: f"Last {h} hours ({h // 24} day{'s' if h // 24 != 1 else ''})",
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


def _render_giveaway_tab(
    client: IdleClansClient,
    section_prefix: str,
    active_clan_name: str,
) -> None:
    if not _load_guard(
        f"{section_prefix}::loaded::giveaway",
        f"{section_prefix}::load_giveaway",
        "Giveaway",
        section_prefix,
    ):
        return

    st.subheader("Skill Giveaway")
    st.caption(
        "Ranks members by the % increase in a chosen skill's XP over a time window. "
        "Useful for running a fair giveaway that rewards relative effort."
    )
    giveaway_hours = st.selectbox(
        "Giveaway Window",
        options=[24, 48, 72, 96, 120, 168],
        index=2,
        format_func=lambda h: f"Last {h} hours ({h // 24} day{'s' if h // 24 != 1 else ''})",
        key=f"{section_prefix}::giveaway_hours",
    )
    with st.spinner("Fetching clan contribution data..."):
        try:
            giveaway_summary = _get_cached_value(
                _cache_key(section_prefix, f"experience_summary::{giveaway_hours}"),
                lambda: client.get_clan_experience_summary(
                    active_clan_name, hours=giveaway_hours
                ),
            )
        except IdleClansAPIError as exc:
            render_api_error(exc)
            giveaway_summary = None

    if giveaway_summary is None:
        return

    available_giveaway_skills = sorted(giveaway_summary.skill_totals, key=str.casefold)
    if not available_giveaway_skills or not giveaway_summary.player_contributions:
        st.info("No clan contribution data was returned for the selected time window.")
        return

    default_giveaway_skill = (
        "Woodcutting"
        if "Woodcutting" in available_giveaway_skills
        else available_giveaway_skills[0]
    )
    giveaway_skill = st.selectbox(
        "Skill",
        options=available_giveaway_skills,
        index=available_giveaway_skills.index(default_giveaway_skill),
        key=f"{section_prefix}::giveaway_skill",
    )
    candidates = [
        (player.username, player.skills[giveaway_skill].experience)
        for player in giveaway_summary.player_contributions
        if giveaway_skill in player.skills and player.skills[giveaway_skill].experience > 0
    ]
    if not candidates:
        st.info(f"No {giveaway_skill} XP gains were recorded in the selected window.")
        return

    with st.spinner(
        f"Fetching player profiles to calculate % XP increase ({len(candidates)} players)..."
    ):
        profile_skills = _fetch_giveaway_profiles(
            client,
            [username for username, _ in candidates],
            section_prefix,
        )

    giveaway_rows = []
    for username, gained_xp in candidates:
        player_skills = profile_skills.get(username)
        if not player_skills:
            continue
        current_xp = float(player_skills.get(giveaway_skill.casefold(), 0))
        start_xp = current_xp - gained_xp
        pct = 100.0 if start_xp <= 0 else (gained_xp / start_xp) * 100.0
        giveaway_rows.append(
            {
                "Username": username,
                "Start XP": start_xp,
                "End XP": current_xp,
                "Gained XP": gained_xp,
                "% Increase": pct,
            }
        )

    giveaway_rows.sort(key=lambda row: row["% Increase"], reverse=True)
    if not giveaway_rows:
        st.info("Could not retrieve profiles for any qualifying players.")
        return

    winner = giveaway_rows[0]
    st.success(
        f"🏆 **Winner: {winner['Username']}** — "
        f"gained {_format_experience(winner['Gained XP'])} {giveaway_skill} XP "
        f"({winner['% Increase']:.1f}% increase)"
    )
    display_rows = [
        {
            "Rank": index + 1,
            "Username": row["Username"],
            f"Start {giveaway_skill} XP": _format_experience(row["Start XP"]),
            f"End {giveaway_skill} XP": _format_experience(row["End XP"]),
            f"Gained {giveaway_skill} XP": _format_experience(row["Gained XP"]),
            "% Increase": f"{row['% Increase']:.1f}%",
        }
        for index, row in enumerate(giveaway_rows)
    ]
    st.dataframe(display_rows, hide_index=True, width="stretch")


def _render_pvm_tab(
    client: IdleClansClient,
    section_prefix: str,
    active_clan_name: str,
) -> None:
    st.subheader("PvM Snapshot")

    snapshot_key = f"{section_prefix}::pvm_snapshot"
    capture_requested_key = f"{section_prefix}::pvm_capture_requested"
    baseline_upload_key = f"{section_prefix}::pvm_baseline"
    cmp_fetch_key = f"{section_prefix}::pvm_cmp_current"

    tab_capture, tab_compare = st.tabs(
        ["📸 Generate Snapshot", "📂 Compare Previous Snapshot"]
    )

    with tab_capture:
        st.caption(
            "Capture each member's current PvM kill counts. "
            "Download the JSON and upload it later to compare progress."
        )
        if st.button(
            "📸 Capture Snapshot",
            key=f"{section_prefix}::pvm_capture_btn",
            type="primary",
        ):
            st.session_state[capture_requested_key] = True
            if snapshot_key in st.session_state:
                del st.session_state[snapshot_key]

        if (
            st.session_state.get(capture_requested_key)
            and snapshot_key not in st.session_state
        ):
            snapshot_members = _get_cached_value(
                _cache_key(section_prefix, "members"),
                lambda: client.get_clan_members(active_clan_name),
            )
            if snapshot_members:
                snapshot_data: dict[str, dict[str, int]] = {}
                progress_bar = st.progress(0, text="Fetching player profiles...")
                total_members = len(snapshot_members)
                for i, member in enumerate(snapshot_members):
                    progress_bar.progress(
                        (i + 1) / total_members,
                        text=f"Fetching {member.username}... ({i + 1}/{total_members})",
                    )
                    try:
                        profile = client.get_player_profile(member.username)
                        snapshot_data[member.username] = dict(profile.pvm_stats)
                    except (IdleClansAPIError, NotFoundError):
                        snapshot_data[member.username] = {}
                progress_bar.empty()
                st.session_state[snapshot_key] = {
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    "clan": active_clan_name,
                    "data": snapshot_data,
                }
            st.session_state[capture_requested_key] = False

        snapshot = st.session_state.get(snapshot_key)
        if snapshot:
            taken_at = snapshot.get("timestamp", "Unknown")
            snapshot_data = snapshot.get("data", {})
            col_ts, col_dl = st.columns([3, 1])
            col_ts.caption(f"Snapshot taken: {taken_at}")
            col_dl.download_button(
                "⬇️ Download JSON",
                data=json.dumps(snapshot, indent=2),
                file_name=f"pvm_snapshot_{active_clan_name}_{taken_at[:10]}.json",
                mime="application/json",
                key=f"{section_prefix}::pvm_download",
            )
            boss = st.selectbox(
                "Filter by Boss",
                options=_PVM_BOSS_FILTERS,
                key=f"{section_prefix}::pvm_boss_filter",
            )
            pvm_rows = []
            for username, pvm_stats in snapshot_data.items():
                kills = _get_pvm_stat(pvm_stats, boss)
                if kills > 0:
                    pvm_rows.append({"Username": username, f"{boss} Kills": kills})
            pvm_rows.sort(key=lambda r: r[f"{boss} Kills"], reverse=True)
            if pvm_rows:
                st.dataframe(pvm_rows, hide_index=True, width="stretch")
            else:
                st.info(f"No {boss} kills found for any clan member in this snapshot.")

    with tab_compare:
        st.caption(
            "Upload a previously downloaded snapshot JSON. "
            "Current member data will be fetched automatically and a full "
            "comparison across all bosses will be shown."
        )
        uploaded_file = st.file_uploader(
            "Upload baseline snapshot (JSON)",
            type="json",
            key=f"{section_prefix}::pvm_upload",
        )
        if uploaded_file is not None:
            try:
                parsed = json.loads(uploaded_file.read())
            except (json.JSONDecodeError, ValueError):
                st.error(
                    "Could not parse the uploaded file. "
                    "Make sure it is a valid JSON file."
                )
                st.session_state.pop(baseline_upload_key, None)
                st.session_state.pop(cmp_fetch_key, None)
                parsed = None

            if parsed is not None:
                if (
                    not isinstance(parsed, dict)
                    or "data" not in parsed
                    or not isinstance(parsed["data"], dict)
                    or not parsed["data"]
                    or not all(isinstance(v, dict) for v in parsed["data"].values())
                ):
                    st.error(
                        "The uploaded file does not look like a PvM snapshot. "
                        "Expected a JSON object with a `data` key mapping "
                        "usernames to PvM stat objects."
                    )
                    st.session_state.pop(baseline_upload_key, None)
                    st.session_state.pop(cmp_fetch_key, None)
                elif parsed != st.session_state.get(baseline_upload_key):
                    st.session_state[baseline_upload_key] = parsed
                    st.session_state.pop(cmp_fetch_key, None)

        baseline = st.session_state.get(baseline_upload_key)

        if baseline and cmp_fetch_key not in st.session_state:
            cmp_members = _get_cached_value(
                _cache_key(section_prefix, "members"),
                lambda: client.get_clan_members(active_clan_name),
            )
            cmp_current: dict[str, dict[str, int]] = {}
            if cmp_members:
                progress_bar = st.progress(0, text="Fetching current player data...")
                total = len(cmp_members)
                for i, member in enumerate(cmp_members):
                    progress_bar.progress(
                        (i + 1) / total,
                        text=f"Fetching {member.username}... ({i + 1}/{total})",
                    )
                    try:
                        profile = client.get_player_profile(member.username)
                        cmp_current[member.username] = dict(profile.pvm_stats)
                    except (IdleClansAPIError, NotFoundError):
                        cmp_current[member.username] = {}
                progress_bar.empty()
            st.session_state[cmp_fetch_key] = {
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "data": cmp_current,
            }

        if baseline and cmp_fetch_key in st.session_state:
            current_cmp = st.session_state[cmp_fetch_key]
            uploaded_ts = baseline.get("timestamp", "")
            fetched_ts = current_cmp.get("timestamp", "")

            # Always treat the older snapshot as "before".
            if uploaded_ts and fetched_ts and uploaded_ts > fetched_ts:
                before_snap, after_snap = current_cmp, baseline
            else:
                before_snap, after_snap = baseline, current_cmp

            before_data: dict[str, dict[str, int]] = before_snap.get("data", {})
            after_data: dict[str, dict[str, int]] = after_snap.get("data", {})
            before_ts = before_snap.get("timestamp", "Unknown")
            after_ts = after_snap.get("timestamp", "Unknown")
            st.caption(f"Before: {before_ts} → After: {after_ts}")

            all_usernames = sorted(set(before_data) | set(after_data), key=str.casefold)
            summary_rows = []
            full_breakdown: dict[str, list[dict[str, object]]] = {}

            for boss in _PVM_BOSS_FILTERS:
                boss_rows = []
                for username in all_usernames:
                    before_kills = _get_pvm_stat(before_data.get(username, {}), boss)
                    after_kills = _get_pvm_stat(after_data.get(username, {}), boss)
                    gained = after_kills - before_kills
                    if gained > 0:
                        boss_rows.append(
                            {
                                "Username": username,
                                "Before": before_kills,
                                "After": after_kills,
                                "Gained": gained,
                            }
                        )
                if not boss_rows:
                    continue
                boss_rows.sort(key=lambda r: r["Gained"], reverse=True)
                top = boss_rows[0]
                summary_rows.append(
                    {
                        "Boss": boss,
                        "Top Player": top["Username"],
                        "Their Kills Gained": top["Gained"],
                        "Players with Gains": len(boss_rows),
                    }
                )
                full_breakdown[boss] = boss_rows

            if summary_rows:
                st.dataframe(summary_rows, hide_index=True, width="stretch")
                with st.expander("Full breakdown by boss"):
                    for boss, rows in full_breakdown.items():
                        st.markdown(f"**{boss}**")
                        st.dataframe(rows, hide_index=True, width="stretch")
            else:
                st.info("No kill count increases found between the two snapshots.")
        elif not baseline:
            st.info("Upload a baseline snapshot above to generate a comparison.")


def _render_members_tab(
    client: IdleClansClient,
    section_prefix: str,
    active_clan_name: str,
) -> None:
    if not _load_guard(
        f"{section_prefix}::loaded::members",
        f"{section_prefix}::load_members",
        "Members",
        section_prefix,
    ):
        return

    with st.spinner("Fetching clan members..."):
        try:
            members = _get_cached_value(
                _cache_key(section_prefix, "members"),
                lambda: client.get_clan_members(active_clan_name),
            )
        except IdleClansAPIError as exc:
            render_api_error(exc)
            members = []

    if not members:
        st.info("No members were returned for this clan.")
        return

    st.subheader("Members")
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

    st.divider()
    st.subheader("Current Clan Activity")
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
            activity_rows.append({"Member": member.username, "Activity": activity_label})
        activity_rows.sort(key=lambda r: r["Activity"])
        st.dataframe(activity_rows, hide_index=True, width="stretch")
    else:
        st.info("No activity data returned for this clan's members.")


def render_clan_lookup(client: IdleClansClient) -> None:
    st.header("Clan Lookup")

    active_clan_name = st.session_state.get("active_clan_lookup_name")

    with st.form("clan-lookup-form"):
        clan_name = st.text_input(
            "Clan Name",
            key="clan_lookup_name",
            placeholder="Enter an exact Idle Clans clan name",
        )
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

    (
        tab_overview,
        tab_contributions,
        tab_giveaway,
        tab_pvm,
        tab_members,
    ) = st.tabs(
        ["📋 Overview", "📊 Contributions", "🎁 Giveaway", "⚔️ PvM Snapshot", "👥 Members"]
    )

    with tab_overview:
        _render_overview_tab(client, info, section_prefix)

    with tab_contributions:
        _render_contributions_tab(client, section_prefix, active_clan_name)

    with tab_giveaway:
        _render_giveaway_tab(client, section_prefix, active_clan_name)

    with tab_pvm:
        _render_pvm_tab(client, section_prefix, active_clan_name)

    with tab_members:
        _render_members_tab(client, section_prefix, active_clan_name)
