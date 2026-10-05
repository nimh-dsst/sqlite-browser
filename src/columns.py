"""Column Display section: choose which result columns are shown and analyzed."""

import dash_bootstrap_components as dbc
import pandas as pd
from dash import ALL, Input, Output, State, callback, callback_context, dcc, html
from dash.exceptions import PreventUpdate

from src.components import (
    create_table_with_truncation,
    get_columns_from_records,
    get_selected_columns_for_display,
)


def column_display_section() -> dbc.Row:
    """Card with the collapsible column checklist."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                html.H5("Column Display", className="card-title mb-0"),
                                                width="auto",
                                            ),
                                            dbc.Col(
                                                dbc.Button(
                                                    "Toggle",
                                                    id="toggle-column-selector-btn",
                                                    color="info",
                                                    outline=True,
                                                    size="sm",
                                                ),
                                                width="auto",
                                            ),
                                        ],
                                        className="mb-2",
                                    ),
                                    html.P(
                                        "Select columns to include in the table view. Unselected columns are excluded.",
                                        className="small text-muted mb-2",
                                    ),
                                    dbc.Collapse(
                                        [
                                            dbc.Row(
                                                [
                                                    dbc.Col(
                                                        dbc.Button(
                                                            "Select All",
                                                            id="select-all-columns-btn",
                                                            color="primary",
                                                            outline=True,
                                                            size="sm",
                                                        ),
                                                        width="auto",
                                                    ),
                                                    dbc.Col(
                                                        dbc.Button(
                                                            "Clear All",
                                                            id="clear-all-columns-btn",
                                                            color="secondary",
                                                            outline=True,
                                                            size="sm",
                                                        ),
                                                        width="auto",
                                                    ),
                                                ],
                                                className="mb-3",
                                            ),
                                            html.Div(
                                                id="column-checklist-container",
                                                style={
                                                    "maxHeight": "300px",
                                                    "overflowY": "auto",
                                                    "border": "1px solid #ddd",
                                                    "borderRadius": "4px",
                                                    "padding": "10px",
                                                },
                                            ),
                                        ],
                                        id="column-selector-collapse",
                                        is_open=False,
                                    ),
                                    # Hidden store for column selector state
                                    dcc.Store(id="column-selector", data=None),
                                ]
                            )
                        ]
                    ),
                ],
                width=12,
            )
        ],
        className="mb-4",
    )


@callback(
    Output("column-selector-collapse", "is_open"),
    Input("toggle-column-selector-btn", "n_clicks"),
    State("column-selector-collapse", "is_open"),
    prevent_initial_call=True,
)
def toggle_column_selector(n_clicks, is_open):
    """Toggle the column selector collapse state."""
    return not is_open


@callback(
    Output("column-checklist-container", "children"),
    Output("column-selector", "data"),
    Input("table-columns-store", "data"),
    Input("current-data-store", "data"),
    Input({"type": "column-checkbox", "index": ALL}, "value"),
    Input("select-all-columns-btn", "n_clicks"),
    Input("clear-all-columns-btn", "n_clicks"),
    State("column-selector", "data"),
    State({"type": "column-checkbox", "index": ALL}, "id"),
)
def update_column_selector(
    table_columns,
    current_data,
    checkbox_values,
    select_all_clicks,
    clear_all_clicks,
    current_selection,
    checkbox_ids,
):
    """Render column checklist and manage selection state."""
    data_columns = get_columns_from_records(current_data)
    available_columns = data_columns or (table_columns or [])

    if not available_columns:
        return html.P("No columns available", className="text-muted small"), None

    ctx = callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else None

    # Determine selected columns based on trigger
    if trigger_id == "select-all-columns-btn":
        selected_columns = available_columns
    elif trigger_id == "clear-all-columns-btn":
        selected_columns = []
    elif trigger_id == "current-data-store":
        # Preserve existing user selection after query/filter refresh.
        if current_selection is None:
            selected_columns = available_columns
        else:
            selected_set = set(current_selection)
            selected_columns = [col for col in available_columns if col in selected_set]
    elif trigger_id == "table-columns-store":
        # New table loaded: default to all table columns.
        selected_columns = available_columns
    elif "column-checkbox" in str(trigger_id):
        # User toggled a checkbox - build selection from checkbox states
        selected_columns = []
        for checkbox_id, checked in zip(checkbox_ids, checkbox_values):
            if checked:
                selected_columns.append(checkbox_id["index"])
    else:
        # Preserve current selection
        selected_columns = current_selection if current_selection is not None else available_columns

    # Build 6-column checklist layout
    num_cols = 6
    num_columns = len(available_columns)
    rows = []
    
    for i in range(0, num_columns, num_cols):
        cols = []
        for j in range(num_cols):
            idx = i + j
            if idx < num_columns:
                col_name = available_columns[idx]
                is_checked = col_name in (selected_columns or [])
                cols.append(
                    dbc.Col(
                        dbc.Checkbox(
                            id={"type": "column-checkbox", "index": col_name},
                            label=col_name,
                            value=is_checked,
                            className="mb-2",
                        ),
                        width=2,
                    )
                )
            else:
                cols.append(dbc.Col(width=2))
        
        rows.append(dbc.Row(cols, className="g-2"))
    
    return html.Div(rows), selected_columns


@callback(
    Output("table-results", "children", allow_duplicate=True),
    Output("results-info", "children", allow_duplicate=True),
    Output("viz-column-selector", "options", allow_duplicate=True),
    Output("viz-column-selector", "value", allow_duplicate=True),
    Output("table-full-data-store", "data", allow_duplicate=True),
    Input("column-selector", "data"),
    State("current-data-store", "data"),
    prevent_initial_call=True,
)
def apply_column_selection_to_display(selected_columns, current_data):
    """Apply selected columns to the current result set without re-running SQL."""
    if not current_data:
        raise PreventUpdate

    df = pd.DataFrame(current_data)

    if df.empty:
        return html.P("No results found."), "No results found", [], None, {}

    display_df = get_selected_columns_for_display(df, selected_columns)

    if display_df.shape[1] == 0:
        return (
            html.P("No columns selected. Choose at least one column in Column Display."),
            f"Showing {len(df)} rows, 0 columns (all columns excluded)",
            [],
            None,
            {},
        )

    table = create_table_with_truncation(display_df)
    info = f"Showing {len(display_df)} rows, {len(display_df.columns)} of {len(df.columns)} columns"
    col_options = [{"label": col, "value": col} for col in display_df.columns]
    viz_value = display_df.columns[0] if len(display_df.columns) > 0 else None

    full_data_dict = {}
    for row_idx, (_, row) in enumerate(display_df.iterrows()):
        row_key = str(row_idx)
        full_data_dict[row_key] = {}
        for col in display_df.columns:
            col_key = str(col)
            full_data_dict[row_key][col_key] = str(row[col])

    return table, info, col_options, viz_value, full_data_dict
