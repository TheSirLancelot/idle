"""Leaderboard page."""

from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from idle_clans_tools.api import IdleClansClient
from idle_clans_tools.api.exceptions import IdleClansAPIError
from idle_clans_tools.ui.errors import render_api_error


def render_leaderboards(client: IdleClansClient) -> None:
    st.header("Leaderboards")

    with st.form("leaderboard-form"):
        category = st.text_input(
            "Category",
            value="total_level",
            help="Examples: total_level, attack, mining, woodcutting.",
        )
        input_columns = st.columns(2)
        top = input_columns[0].number_input("Entries", min_value=1, max_value=100, value=10)
        page = input_columns[1].number_input("Page", min_value=1, value=1)
        submitted = st.form_submit_button("Load Leaderboard", type="primary")

    if not submitted:
        return

    category = category.strip()
    if not category:
        st.warning("Enter a leaderboard category.")
        return

    with st.spinner("Fetching leaderboard..."):
        try:
            entries = client.get_leaderboard(category, page=int(page), page_size=int(top))
        except IdleClansAPIError as exc:
            render_api_error(exc)
            return

    if not entries:
        st.info(f"No leaderboard data was returned for '{category}'.")
        return

    st.subheader(f"{category} - page {int(page)}")
    entry_rows = [
        {
            "Rank": entry.rank,
            "Username": entry.username,
            "Value": entry.value,
        }
        for entry in entries
    ]
    st.dataframe(entry_rows, hide_index=True, use_container_width=True)

    with st.expander("Raw leaderboard data"):
        st.json([asdict(entry) for entry in entries])
