"""Authentication helpers for the Streamlit UI."""

from __future__ import annotations

import streamlit as st


def render_login_page() -> None:
    """Render the login gate. Stops script execution if the user is not authenticated."""
    if st.user.is_logged_in:
        return

    st.title("clanlytics")
    st.caption("Idle Clans public API explorer")
    st.divider()
    st.subheader("Sign in to continue")
    st.button("Sign in with Google", on_click=st.login, type="primary")
    st.stop()


def render_user_info() -> None:
    """Render the authenticated user's info and a logout button in the sidebar."""
    name = st.user.get("name") or st.user.get("email") or "User"
    st.sidebar.markdown(f"Signed in as **{name}**")
    st.sidebar.button("Sign out", on_click=st.logout)
    st.sidebar.divider()
