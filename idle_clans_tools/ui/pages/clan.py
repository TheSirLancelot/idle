"""Clan lookup page."""

from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from idle_clans_tools.api import IdleClansClient
from idle_clans_tools.api.exceptions import IdleClansAPIError
from idle_clans_tools.ui.errors import render_api_error
from idle_clans_tools.ui.formatting import format_bool, format_number


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
            member_rows = [
                {
                    "Rank": member.rank,
                    "Username": member.username,
                    "Total XP": member.total_experience,
                }
                for member in members
            ]
            st.dataframe(member_rows, hide_index=True, use_container_width=True)
        else:
            st.info("No members were returned for this clan.")

    with st.expander("Raw clan data"):
        st.json(
            {
                "info": asdict(info),
                "members": [asdict(member) for member in members],
            }
        )
