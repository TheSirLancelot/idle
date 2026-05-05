"""Clan lookup page."""

from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from idle_clans_tools.api import IdleClansClient
from idle_clans_tools.api.exceptions import IdleClansAPIError
from idle_clans_tools.ui.errors import render_api_error
from idle_clans_tools.ui.formatting import format_bool, format_number


def _open_player_lookup(username: str) -> None:
    st.session_state.pending_player_lookup_username = username
    st.session_state.pending_page = "Player Lookup"


def _format_experience(value: float) -> str:
    return f"{value:,.0f}"


def _format_milliseconds_as_minutes_seconds(value: int) -> str:
    total_seconds = max(0, value) // 1000
    minutes, seconds = divmod(total_seconds, 60)
    return f"{minutes}:{seconds:02d}"


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

    with st.spinner("Fetching clan information..."):
        try:
            info = client.get_clan_info(active_clan_name)
            members = client.get_clan_members(active_clan_name) if include_members else []
            cup_standings = client.get_clan_cup_standings(active_clan_name)
            upgrade_lookup = client.get_clan_upgrade_lookup()
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

    st.subheader("Clan Cup Standings")
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
        st.dataframe(rows, hide_index=True, width='stretch')
    else:
        st.info("No Clan Cup standings found for this clan.")

    st.subheader("Clan Contributions")
    hours = st.selectbox(
        "Contribution Window",
        options=[24, 48, 72, 96, 120, 168],
        index=3,
        format_func=lambda value: f"Last {value} hours",
        key="clan_contribution_hours",
    )
    with st.spinner("Fetching clan contribution data..."):
        try:
            experience_summary = client.get_clan_experience_summary(active_clan_name, hours=hours)
        except IdleClansAPIError as exc:
            render_api_error(exc)
            return

    available_skills = sorted(experience_summary.skill_totals, key=str.casefold)
    if available_skills and experience_summary.player_contributions:
        default_skill = "Woodcutting" if "Woodcutting" in available_skills else available_skills[0]
        skill = st.selectbox(
            "Skill",
            options=available_skills,
            index=available_skills.index(default_skill),
            key="clan_contribution_skill",
        )
        contribution_rows = []
        for player in experience_summary.player_contributions:
            skill_snapshot = player.skills.get(skill)
            skill_experience = skill_snapshot.experience if skill_snapshot is not None else 0.0
            if skill_experience <= 0:
                continue
            contribution_rows.append(
                {
                    "Username": player.username,
                    f"{skill} XP": skill_experience,
                    f"{skill} Level": skill_snapshot.level if skill_snapshot is not None else 0,
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
            st.dataframe(formatted_rows, hide_index=True, width='stretch')
        else:
            st.info(f"No {skill} contributions were found in the selected time window.")
    else:
        st.info("No clan contribution data was returned for the selected time window.")

    if include_members:
        st.subheader("Members")
        if members:
            member_rows = [{"Rank": member.rank, "Username": member.username} for member in members]
            st.dataframe(member_rows, hide_index=True, width='stretch')
            with st.expander("Open member in Player Lookup"):
                cols = st.columns(4)
                for index, member in enumerate(members):
                    cols[index % 4].button(
                        member.username,
                        key=f"clan-member-{index}-{member.username}",
                        on_click=_open_player_lookup,
                        args=(member.username,),
                        width='stretch',
                    )
        else:
            st.info("No members were returned for this clan.")

    st.subheader("Clan Upgrades")
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
        st.dataframe(upgrade_rows, hide_index=True, width='stretch')
    else:
        st.info("No upgrade data found for this clan.")

    with st.expander("Raw clan data"):
        st.json(
            {
                "info": asdict(info),
                "members": [asdict(member) for member in members],
                "cup_standings": [asdict(s) for s in cup_standings],
                "experience_summary": asdict(experience_summary),
            }
        )
