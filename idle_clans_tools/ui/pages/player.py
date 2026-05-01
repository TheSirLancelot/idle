"""Player lookup page."""

from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from idle_clans_tools.api import IdleClansClient
from idle_clans_tools.api.exceptions import IdleClansAPIError
from idle_clans_tools.api.models import PlayerProfile
from idle_clans_tools.ui.errors import render_api_error
from idle_clans_tools.ui.formatting import format_number


def render_player_lookup(client: IdleClansClient) -> None:
    st.header("Player Lookup")

    with st.form("player-lookup-form"):
        username = st.text_input("Username", placeholder="Enter an Idle Clans username")
        submitted = st.form_submit_button("Look Up Player", type="primary")

    if not submitted:
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

    _render_player_profile(profile)

    with st.expander("Raw profile data"):
        st.json(asdict(profile))


def _render_player_profile(profile: PlayerProfile) -> None:
    st.subheader(profile.username or "Unknown player")

    metric_columns = st.columns(3)
    metric_columns[0].metric("Clan", profile.clan_name or "None")
    metric_columns[1].metric("Combat Level", format_number(profile.combat_level))
    metric_columns[2].metric("Total XP", format_number(profile.total_experience))

    if not profile.skills:
        st.info("No skill data was returned for this player.")
        return

    skill_rows = [
        {"Skill": skill, "XP": xp}
        for skill, xp in sorted(profile.skills.items(), key=lambda item: item[0].casefold())
    ]
    st.dataframe(skill_rows, hide_index=True, use_container_width=True)
