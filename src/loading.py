"""Load Database and Tables sections: open a SQLite file and pick a table."""

import os
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from src.database import DatabaseConnection


def load_database_section() -> dbc.Row:
    """Card with the database path input and Load button."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H5("Load Database", className="card-title"),
                                    dbc.InputGroup(
                                        [
                                            dbc.Input(
                                                id="db-path-input",
                                                placeholder="Enter path to .sqlite file",
                                                type="text",
                                                value="./data/db.sqlite",
                                            ),
                                            dbc.Button(
                                                "Load", id="load-db-btn", color="primary"
                                            ),
                                        ]
                                    ),
                                    html.Div(
                                        id="db-status-message",
                                        className="mt-2 text-muted small",
                                    ),
                                ]
                            )
                        ]
                    ),
                ],
                width=12,
                lg=6,
            )
        ],
        className="mb-4",
    )


def table_selection_section() -> dbc.Row:
    """Card with the table dropdown and Load Table button."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H5("Tables", className="card-title"),
                                    dcc.Dropdown(
                                        id="table-selector",
                                        placeholder="Select a table...",
                                        className="mb-2",
                                    ),
                                    dbc.Button(
                                        "Load Table",
                                        id="load-table-btn",
                                        color="info",
                                        size="sm",
                                    ),
                                    html.Div(
                                        id="table-info",
                                        className="mt-2 small text-muted",
                                    ),
                                ]
                            )
                        ]
                    ),
                ],
                width=12,
                lg=6,
            )
        ],
        className="mb-4",
    )


@callback(
    Output("db-status-message", "children"),
    Output("table-selector", "options"),
    Output("table-selector", "value"),
    Input("load-db-btn", "n_clicks"),
    State("db-path-input", "value"),
    prevent_initial_call=True,
)
def load_database(n_clicks, db_path):
    """Load database and display available tables."""
    if not db_path:
        return "Please enter a database path", [], None

    db_path = str(Path(db_path).expanduser())

    if not os.path.exists(db_path):
        return f"Error: File not found: {db_path}", [], None

    try:
        db = DatabaseConnection(db_path)
        if not db.connect():
            return "Error: Could not open database", [], None

        tables = db.get_tables()
        db.close()

        if not tables:
            return "Database loaded but no tables found", [], None

        options = [{"label": t, "value": t} for t in tables]
        # Auto-select first table
        first_table = tables[0] if tables else None
        return f"✓ Database loaded: {len(tables)} tables", options, first_table

    except Exception as e:
        return f"Error loading database: {str(e)}", [], None


@callback(
    Output("table-info", "children"),
    Output("table-columns-store", "data"),
    Input("load-table-btn", "n_clicks"),
    State("table-selector", "value"),
    State("db-path-input", "value"),
    prevent_initial_call=True,
)
def load_table_info(n_clicks, table_name, db_path):
    """Load table info and store column names."""
    if not table_name or not db_path:
        raise PreventUpdate

    db_path = str(Path(db_path).expanduser())
    
    try:
        db = DatabaseConnection(db_path)
        if not db.connect():
            return "Error connecting to database", None

        columns, row_count = db.get_table_info(table_name)
        db.close()

        info = f"Columns: {len(columns)} | Rows: {row_count}"
        return info, columns

    except Exception as e:
        return f"Error: {str(e)}", None


@callback(
    Output("table-selector", "value", allow_duplicate=True),
    Output("current-table-store", "data"),
    Input("load-table-btn", "n_clicks"),
    State("table-selector", "value"),
    prevent_initial_call=True,
)
def store_table_name(n_clicks, table_name):
    """Store the current table name."""
    return table_name, table_name
