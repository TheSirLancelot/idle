"""Streamlit application for clanlytics."""

from __future__ import annotations

import streamlit as st

from idle_clans_tools.api import IdleClansClient
from idle_clans_tools.ui.auth import render_login_page, render_user_info
from idle_clans_tools.ui.pages import (
    render_clan_lookup,
    render_leaderboards,
    render_market,
    render_player_lookup,
)

PAGES = ["Player Lookup", "Clan Lookup", "Leaderboards", "Market"]


def main() -> None:
    st.set_page_config(page_title="clanlytics", page_icon="CL", layout="wide")

    render_login_page()

    st.title("clanlytics")
    st.caption("Idle Clans public API explorer")

    client = IdleClansClient()

    render_user_info()

    if pending_page := st.session_state.pop("pending_page", None):
        st.session_state.navigation_page = pending_page

    selected_page = st.sidebar.radio(
        "Navigation",
        PAGES,
        key="navigation_page",
    )

    if selected_page == "Player Lookup":
        render_player_lookup(client)
    elif selected_page == "Clan Lookup":
        render_clan_lookup(client)
    elif selected_page == "Leaderboards":
        render_leaderboards(client)
    elif selected_page == "Market":
        render_market(client)


if __name__ == "__main__":
    main()
