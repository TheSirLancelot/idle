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


def render_clan_lookup(client: IdleClansClient) -> None:
    st.header("Clan Lookup")

    with st.form("clan-lookup-form"):
        clan_name = st.text_input("Clan Name", placeholder="Enter an exact Idle Clans clan name")
        include_members = st.checkbox("Show member list", value=True)
        submitted = st.form_submit_button("Look Up Clan", type="primary")

    if not submitted:
        return

    clan_name = clan_name.strip()
    if not clan_name:
        st.warning("Enter a clan name to look up a clan.")
        return

    with st.spinner("Fetching clan information..."):
        try:
            info = client.get_clan_info(clan_name)
            members = client.get_clan_members(clan_name) if include_members else []
        except IdleClansAPIError as exc:
            render_api_error(exc)
            return

    st.subheader(info.name or clan_name)
    metric_columns = st.columns(4)
    metric_columns[0].metric("Members", format_number(info.member_count))
    metric_columns[1].metric("Total XP", format_number(info.total_experience))
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

    if include_members:
        st.subheader("Members")
        if members:
            header_columns = st.columns([2, 4, 2])
            header_columns[0].write("**Rank**")
            header_columns[1].write("**Username**")
            header_columns[2].write("**Total XP**")

            for index, member in enumerate(members):
                row_columns = st.columns([2, 4, 2])
                row_columns[0].write(member.rank)
                row_columns[1].button(
                    member.username,
                    key=f"clan-member-{index}-{member.username}",
                    on_click=_open_player_lookup,
                    args=(member.username,),
                    type="tertiary",
                )
                row_columns[2].write(format_number(member.total_experience))
        else:
            st.info("No members were returned for this clan.")

    with st.expander("Raw clan data"):
        st.json(
            {
                "info": asdict(info),
                "members": [asdict(member) for member in members],
            }
        )
