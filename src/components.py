"""Shared table rendering and column-selection helpers used across features."""

from typing import Dict, List, Optional

import pandas as pd
from dash.dash_table import DataTable


def create_table_with_truncation(df: pd.DataFrame) -> DataTable:
    """Create a DataTable with full data but CSS-truncated display at 40 chars."""
    if df.empty:
        return DataTable(data=[], columns=[], id="table-results-datatable")
    
    # Create columns configuration
    columns = [
        {
            "name": col,
            "id": col,
        }
        for col in df.columns
    ]
    
    # Use full data without truncation - CSS will handle display truncation
    # Also add title attribute for hover tooltips
    display_data = []
    for _, row in df.iterrows():
        row_data = {}
        for col in df.columns:
            cell_value = str(row[col]) if row[col] is not None else ""
            # Add title attribute for hover tooltip showing full content
            row_data[col] = cell_value
        display_data.append(row_data)
    
    return DataTable(
        id="table-results-datatable",
        data=display_data,
        columns=columns,
        row_selectable=False,
        selected_rows=[],
        cell_selectable=False,
        virtualization=False,
        page_action='none',
        style_cell={
            "whiteSpace": "nowrap",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "maxWidth": "300px",
            "padding": "10px 5px",
            "cursor": "pointer",
        },
        style_cell_conditional=[
            {
                "if": {"column_id": col},
                "textAlign": "left",
            }
            for col in df.columns
        ],
        style_as_list_view=True,
        style_table={
            "overflowX": "auto",
            "overflowY": "auto",
            "maxHeight": "600px",
        },
        style_header={
            "fontWeight": "bold",
            "backgroundColor": "#f8f9fa",
            "textAlign": "left",
            "padding": "10px 5px",
            "whiteSpace": "nowrap",
            "position": "sticky",
            "top": "0",
            "zIndex": "10",
        },
        style_data={
            "backgroundColor": "white",
            "border": "1px solid #ddd",
        },
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "#f9f9f9",
            }
        ],
    )


def get_selected_columns_for_display(df: pd.DataFrame, selected_columns: Optional[List[str]]) -> pd.DataFrame:
    """Return DataFrame filtered to selected columns, preserving source column order."""
    if selected_columns is None:
        return df

    selected_set = set(selected_columns)
    valid_columns = [col for col in df.columns if col in selected_set]
    return df.loc[:, valid_columns]


def get_column_selector_options(columns: List[str]) -> List[Dict[str, str]]:
    """Build dropdown options for the column selector."""
    return [{"label": col, "value": col} for col in columns]


def get_columns_from_records(records: Optional[List[Dict]]) -> List[str]:
    """Extract ordered columns from query result records."""
    if not records:
        return []

    columns = []
    seen = set()
    for row in records:
        if not isinstance(row, dict):
            continue
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                columns.append(key)
    return columns
