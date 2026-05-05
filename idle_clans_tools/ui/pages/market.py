"""Market listings page."""

from __future__ import annotations

from dataclasses import asdict

import streamlit as st

from idle_clans_tools.api import IdleClansClient
from idle_clans_tools.api.exceptions import IdleClansAPIError
from idle_clans_tools.ui.errors import render_api_error


def render_market(client: IdleClansClient) -> None:
    st.header("Market")

    with st.form("market-form"):
        item_name = st.text_input("Item Name", placeholder="Optional item name filter")
        submitted = st.form_submit_button("Load Market Listings", type="primary")

    if not submitted:
        return

    item_name = item_name.strip() or None
    with st.spinner("Fetching market listings..."):
        try:
            items = client.get_market_items(item_name=item_name)
        except IdleClansAPIError as exc:
            render_api_error(exc)
            return

    label = f" for {item_name}" if item_name else ""
    if not items:
        st.info(f"No market listings were returned{label}.")
        return

    st.subheader(f"Market Listings{label}")
    item_rows = [
        {
            "Item": item.item_name,
            "Price": item.price,
            "Quantity": item.quantity,
            "Seller": item.seller or "Unknown",
            "Item ID": item.item_id,
        }
        for item in items
    ]
    st.dataframe(item_rows, hide_index=True, width='stretch')

    with st.expander("Raw market data"):
        st.json([asdict(item) for item in items])
