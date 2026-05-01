"""Streamlit application for clanlytics."""

from __future__ import annotations

import streamlit as st

from idle_clans_tools.api import IdleClansClient
from idle_clans_tools.ui.pages import (
    render_clan_lookup,
    render_leaderboards,
    render_market,
    render_player_lookup,
)


def main() -> None:
    st.set_page_config(page_title="clanlytics", page_icon="CL", layout="wide")

    st.title("clanlytics")
    st.caption("Idle Clans public API explorer")

    client = IdleClansClient()

    selected_page = st.sidebar.radio(
        "Navigation",
        ["Player Lookup", "Clan Lookup", "Leaderboards", "Market"],
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
