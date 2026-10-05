"""Execute Custom Query section: run free-form SQL against the loaded database."""

import os
import traceback
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, html
from dash.exceptions import PreventUpdate

from src.components import create_table_with_truncation, get_selected_columns_for_display
from src.database import DatabaseConnection


def query_section() -> dbc.Row:
    """Card with the SQL textarea and Execute/Clear buttons."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H5("Execute Custom Query", className="card-title"),
                                    dbc.Textarea(
                                        id="query-input",
                                        placeholder="Enter SQL query (e.g., SELECT * FROM table_name WHERE condition)",
                                        rows=4,
                                        className="mb-2",
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Button(
                                                    "Execute Query",
                                                    id="execute-query-btn",
                                                    color="success",
                                                ),
                                                width="auto",
                                            ),
                                            dbc.Col(
                                                dbc.Button(
                                                    "Clear",
                                                    id="clear-query-btn",
                                                    color="secondary",
                                                    outline=True,
                                                ),
                                                width="auto",
                                            ),
                                        ],
                                        className="g-2",
                                    ),
                                    html.Div(
                                        id="query-error-message",
                                        className="mt-2 text-danger small",
                                    ),
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
    Output("query-input", "value", allow_duplicate=True),
    Input("clear-query-btn", "n_clicks"),
    prevent_initial_call=True,
)
def clear_query(n_clicks):
    """Clear query input."""
    return ""


@callback(
    Output("table-results", "children", allow_duplicate=True),
    Output("results-info", "children", allow_duplicate=True),
    Output("query-error-message", "children"),
    Output("sql-display", "children", allow_duplicate=True),
    Output("current-data-store", "data", allow_duplicate=True),
    Output("viz-column-selector", "options", allow_duplicate=True),
    Output("viz-column-selector", "value", allow_duplicate=True),
    Output("table-full-data-store", "data", allow_duplicate=True),
    Output("current-filters-store", "data", allow_duplicate=True),
    Output("current-sql-store", "data", allow_duplicate=True),
    Input("execute-query-btn", "n_clicks"),
    State("query-input", "value"),
    State("db-path-input", "value"),
    State("column-selector", "data"),
    prevent_initial_call=True,
)
def execute_custom_query(n_clicks, query, db_path, selected_columns):
    """Execute custom SQL query."""
    if not query or not db_path:
        raise PreventUpdate

    db_path = str(Path(db_path).expanduser())

    if not os.path.exists(db_path):
        return "", "", "Database file not found", "", None, [], None, None, None

    try:
        executed_query = query.strip()
        if "LIMIT" not in executed_query.upper():
            executed_query = f"{executed_query} LIMIT 500"

        db = DatabaseConnection(db_path)
        if not db.connect():
            return "", "", "Error: Could not connect to database", "", None, [], None, None, None, None

        df, error = db.execute_query(query)
        db.close()

        if error:
            return "", "", f"Query Error: {error}", f"SQL: {query}", None, [], None, None, None, None

        if df.empty:
            return (
                html.P("No results found."),
                "No results found",
                "",
                f"SQL: {query}",
                None,
                [],
                None,
                None,
                None,
                query,
            )

        # Apply optional column selection for display
        display_df = get_selected_columns_for_display(df, selected_columns)

        if display_df.shape[1] == 0:
            return (
                html.P("No columns selected. Choose at least one column in Column Display."),
                f"Showing {len(df)} rows, 0 columns (all columns excluded)",
                "",
                f"SQL: {query}",
                df.to_dict("records"),
                [],
                None,
                {},
                None,
                query,
            )

        # Create table from results
        table = create_table_with_truncation(display_df)

        # Results info
        info = f"Showing {len(display_df)} rows, {len(display_df.columns)} of {len(df.columns)} columns"

        # Column options for visualization
        all_cols = display_df.columns.tolist()
        col_options = [{"label": col, "value": col} for col in all_cols]
        viz_value = all_cols[0] if all_cols else None

        # Store full query data so column display can be changed without re-running query
        df_data = df.to_dict("records")
        
        # Store displayed data (before truncation) for click-to-view feature
        # Create a dictionary with string keys for both row indices and column names
        full_data_dict = {}
        for row_idx, (_, row) in enumerate(display_df.iterrows()):
            row_key = str(row_idx)
            full_data_dict[row_key] = {}
            for col in display_df.columns:
                col_key = str(col)
                full_data_dict[row_key][col_key] = str(row[col])

        return table, info, "", f"SQL: {query}", df_data, col_options, viz_value, full_data_dict, None, executed_query

    except Exception as e:
        return (
            "",
            "",
            f"Error: {traceback.format_exc()}",
            f"SQL: {query}",
            None,
            [],
            None,
            None,
            None,
            None,
        )
