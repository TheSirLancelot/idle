"""Authentication helpers for the Streamlit UI."""

from __future__ import annotations

import streamlit as st

_AUTH_IN_PROGRESS_KEY = "auth_login_in_progress"


def _start_login() -> None:
    # Mark the flow as started before redirecting to the provider.
    st.session_state[_AUTH_IN_PROGRESS_KEY] = True
    st.login()


def render_login_page() -> None:
    """Render the login gate. Stops script execution if the user is not authenticated."""
    if st.user.is_logged_in:
        st.session_state.pop(_AUTH_IN_PROGRESS_KEY, None)
        return

    st.title("clanlytics")
    st.caption("Idle Clans public API explorer")
    st.divider()
    st.subheader("Sign in to continue")

    login_in_progress = st.session_state.get(_AUTH_IN_PROGRESS_KEY, False)

    if login_in_progress:
        st.info("Sign-in is already in progress. If it appears stuck, reset and try again.")
        if st.button("Reset Sign-In Flow", width="stretch"):
            st.session_state.pop(_AUTH_IN_PROGRESS_KEY, None)
            st.rerun()
    else:
        if st.button("Sign in with Google", type="primary", width="stretch"):
            _start_login()

    st.stop()


def render_user_info() -> None:
    """Render the authenticated user's info and a logout button in the sidebar."""
    name = st.user.get("name") or st.user.get("email") or "User"
    st.sidebar.markdown(f"Signed in as **{name}**")
    st.sidebar.button("Sign out", on_click=st.logout)
    st.sidebar.divider()
