"""Browse locally exported game-data section JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st

from idle_clans_tools.api import IdleClansClient


def _data_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    return repo_root / "data" / "game_data_sections"


def _summarize_payload(payload: Any) -> tuple[str, int | None]:
    if isinstance(payload, dict):
        return ("object", len(payload))
    if isinstance(payload, list):
        return ("array", len(payload))
    return (type(payload).__name__, None)


def _is_record_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, dict) for item in value)


def _extract_record_sets(payload: Any) -> dict[str, list[dict[str, Any]]]:
    record_sets: dict[str, list[dict[str, Any]]] = {}

    if _is_record_list(payload):
        record_sets["$root"] = payload
        return record_sets

    if not isinstance(payload, dict):
        return record_sets

    for key, value in payload.items():
        if _is_record_list(value):
            record_sets[str(key)] = value
            continue

        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                if _is_record_list(nested_value):
                    record_sets[f"{key}.{nested_key}"] = nested_value

    return record_sets


def _flatten_record(
    value: Any,
    prefix: str = "",
    *,
    max_depth: int = 4,
    max_list_items: int = 10,
) -> dict[str, Any]:
    rows: dict[str, Any] = {}

    def _walk(current: Any, path: str, depth: int) -> None:
        if depth > max_depth:
            rows[path or "value"] = str(current)
            return

        if isinstance(current, dict):
            if not current:
                rows[path or "value"] = "{}"
                return
            for key, nested in current.items():
                next_path = f"{path}.{key}" if path else str(key)
                _walk(nested, next_path, depth + 1)
            return

        if isinstance(current, list):
            if not current:
                rows[path or "value"] = "[]"
                return
            if all(not isinstance(item, (dict, list)) for item in current):
                preview = ", ".join(str(item) for item in current[:max_list_items])
                if len(current) > max_list_items:
                    preview += ", ..."
                rows[path or "value"] = preview
                return

            for index, nested in enumerate(current[:max_list_items]):
                next_path = f"{path}[{index}]" if path else f"[{index}]"
                _walk(nested, next_path, depth + 1)
            if len(current) > max_list_items:
                rows[f"{path}.__truncated" if path else "__truncated"] = (
                    f"{len(current) - max_list_items} additional items"
                )
            return

        rows[path or "value"] = current

    _walk(value, prefix, 0)
    return rows


def _render_table_view(payload: Any) -> None:
    st.subheader("Table Explorer")
    record_sets = _extract_record_sets(payload)

    if not record_sets:
        st.info(
            "No list-of-object datasets detected in this file. "
            "Use Raw JSON View for direct inspection."
        )
        return

    set_name = st.selectbox(
        "Dataset",
        options=list(record_sets.keys()),
        key="game_data_browser_dataset",
    )
    records = record_sets[set_name]
    st.caption(f"Detected {len(records):,} records in {set_name}.")

    controls = st.columns(2)
    max_rows = controls[0].slider(
        "Rows to load",
        min_value=50,
        max_value=5000,
        value=500,
        step=50,
        key="game_data_browser_rows_to_load",
    )
    start_at = controls[1].number_input(
        "Start row",
        min_value=1,
        max_value=max(1, len(records)),
        value=1,
        step=1,
        key="game_data_browser_start_row",
    )

    start_idx = int(start_at) - 1
    slice_records = records[start_idx : start_idx + int(max_rows)]
    flat_rows = [_flatten_record(record) for record in slice_records]

    if not flat_rows:
        st.info("No rows in selected range.")
        return

    ordered_columns: list[str] = []
    for row in flat_rows:
        for column in row:
            if column not in ordered_columns:
                ordered_columns.append(column)

    preferred = [
        column
        for column in ordered_columns
        if column.lower() in {"id", "itemid", "name", "type", "title"}
    ]
    default_columns = (
        preferred
        + [column for column in ordered_columns if column not in preferred][
            : max(0, 12 - len(preferred))
        ]
    )

    selected_columns = st.multiselect(
        "Columns",
        options=ordered_columns,
        default=default_columns or ordered_columns[:12],
        key="game_data_browser_columns",
    )

    query = st.text_input(
        "Filter rows (contains text)",
        placeholder="e.g. woodcut, sword, 1200",
        key="game_data_browser_row_filter",
    ).strip()

    filtered_rows = flat_rows
    if query:
        needle = query.casefold()
        filtered_rows = [
            row
            for row in flat_rows
            if any(needle in str(value).casefold() for value in row.values())
        ]

    display_columns = selected_columns or ordered_columns
    table_rows = [{column: row.get(column) for column in display_columns} for row in filtered_rows]

    st.write(f"Showing {len(table_rows):,} of {len(flat_rows):,} loaded rows.")
    st.dataframe(table_rows, hide_index=True, width="stretch")


def _render_raw_json_view(payload: Any) -> None:
    search = st.text_input(
        "Search JSON text",
        placeholder="Type text to filter matching lines",
        key="game_data_browser_search",
    ).strip()

    rendered = json.dumps(payload, indent=2, sort_keys=True)
    rendered_lines = rendered.splitlines()

    def _format_with_line_numbers(start: int, end: int, focus_line: int | None = None) -> str:
        numbered_lines: list[str] = []
        for idx in range(start, end):
            marker = ">>" if focus_line is not None and idx == focus_line else "  "
            numbered_lines.append(f"{marker} {idx + 1:>6}: {rendered_lines[idx]}")
        return "\n".join(numbered_lines)

    if search:
        needle = search.casefold()
        matching_indexes = [
            idx for idx, line in enumerate(rendered_lines) if needle in line.casefold()
        ]
        st.write(f"Matches: {len(matching_indexes):,} line(s)")

        if not matching_indexes:
            st.info("No matches.")
            return

        match_labels = [
            f"Line {idx + 1}: {rendered_lines[idx].strip()[:120]}"
            for idx in matching_indexes[:1000]
        ]
        selected_label = st.selectbox(
            "Go to match",
            options=match_labels,
            key="game_data_browser_selected_match",
        )
        selected_match_idx = match_labels.index(selected_label)
        focus_line = matching_indexes[selected_match_idx]

        context_window = st.slider(
            "Context lines around match",
            min_value=3,
            max_value=200,
            value=25,
            step=1,
            key="game_data_browser_context_window",
        )

        start = max(0, focus_line - context_window)
        end = min(len(rendered_lines), focus_line + context_window + 1)
        st.caption(
            f"Showing lines {start + 1:,}-{end:,} of {len(rendered_lines):,}. "
            "Matched line is marked with >>."
        )
        st.code(_format_with_line_numbers(start, end, focus_line=focus_line), language="json")

        if len(matching_indexes) > 1000:
            st.caption("Showing first 1,000 matches in the dropdown.")
    else:
        show_limit = st.slider(
            "Preview lines",
            min_value=100,
            max_value=3000,
            value=800,
            step=100,
            key="game_data_browser_preview_limit",
        )
        preview = _format_with_line_numbers(0, min(show_limit, len(rendered_lines)))
        st.code(preview, language="json")
        if len(rendered_lines) > show_limit:
            st.caption("Preview truncated. Increase the line limit to view more.")


def render_game_data_browser(_client: IdleClansClient) -> None:
    st.header("Game Data Browser")
    st.caption("Browse exported game-data sections from data/game_data_sections.")

    directory = _data_dir()
    files = sorted(directory.glob("*.json"), key=lambda path: path.name.casefold())

    if not files:
        st.info(
            "No exported game-data files found. Run: "
            "python -m idle_clans_tools gamedata --list-sections "
            "and export sections into data/game_data_sections."
        )
        return

    selected_name = st.selectbox(
        "Section File",
        options=[f.name for f in files],
        key="game_data_browser_selected_file",
    )
    selected_file = directory / selected_name

    try:
        content = selected_file.read_text(encoding="utf-8")
        payload = json.loads(content)
    except OSError as exc:
        st.error(f"Failed to read file: {exc}")
        return
    except json.JSONDecodeError as exc:
        st.error(f"Invalid JSON in selected file: {exc}")
        return

    payload_type, payload_size = _summarize_payload(payload)
    meta_cols = st.columns(3)
    meta_cols[0].metric("File Size", f"{selected_file.stat().st_size:,} bytes")
    meta_cols[1].metric("Payload Type", payload_type)
    meta_cols[2].metric(
        "Entries" if payload_size is not None else "Entries",
        f"{payload_size:,}" if payload_size is not None else "N/A",
    )

    if isinstance(payload, dict) and payload:
        st.subheader("Top-Level Keys")
        st.dataframe(
            [{"Key": key} for key in sorted(payload.keys(), key=str.casefold)],
            hide_index=True,
            width="stretch",
        )

    view_tabs = st.tabs(["Table View", "Raw JSON View"])
    with view_tabs[0]:
        _render_table_view(payload)
    with view_tabs[1]:
        _render_raw_json_view(payload)

    st.download_button(
        label="Download selected JSON",
        data=content,
        file_name=selected_file.name,
        mime="application/json",
        key="game_data_browser_download",
    )
