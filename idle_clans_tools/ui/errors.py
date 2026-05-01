"""User-facing error rendering for the Streamlit UI."""

from __future__ import annotations

import streamlit as st

from idle_clans_tools.api.exceptions import (
    IdleClansAPIError,
    NetworkError,
    NotFoundError,
    RateLimitError,
)


def render_api_error(exc: IdleClansAPIError) -> None:
    if isinstance(exc, NotFoundError):
        st.error("No matching result was found.")
    elif isinstance(exc, RateLimitError):
        st.error("The Idle Clans API rate limit was reached. Try again in a moment.")
    elif isinstance(exc, NetworkError):
        st.error("Could not reach the Idle Clans API. Check your connection and try again.")
    else:
        st.error(f"The Idle Clans API returned an error: {exc}")
