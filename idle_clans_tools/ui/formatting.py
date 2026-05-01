"""Formatting helpers for the Streamlit UI."""

from __future__ import annotations


def format_bool(value: bool | None) -> str:
    if value is None:
        return "Unknown"
    return "Yes" if value else "No"


def format_number(value: int) -> str:
    return f"{value:,}"
