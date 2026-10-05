"""Top-level page layout assembled from each feature's section."""

import dash_bootstrap_components as dbc
from dash import dcc, html

from src.columns import column_display_section
from src.export import export_section
from src.filters import filter_builder_section
from src.loading import load_database_section, table_selection_section
from src.query import query_section
from src.results import results_section


def build_layout() -> dbc.Container:
    """Build the full app layout.

    Returns
    -------
    dbc.Container
        Page title, feature sections in display order, and hidden app-state stores.
    """
    return dbc.Container(
        [
            dbc.Row(
                [
                    dbc.Col(
                        html.H1("SQLite Database Browser", className="mb-4 mt-4"),
                        width=12,
                    )
                ]
            ),
            load_database_section(),
            table_selection_section(),
            filter_builder_section(),
            query_section(),
            column_display_section(),
            results_section(),
            export_section(),
            # Hidden stores for app state
            dcc.Store(id="current-data-store", storage_type="memory"),
            dcc.Store(id="current-filters-store", storage_type="memory"),
            dcc.Store(id="filter-count-store", data={"count": 1}),
            dcc.Store(id="current-table-store", storage_type="memory"),
            dcc.Store(id="table-columns-store", storage_type="memory"),
            dcc.Store(id="current-sql-store", storage_type="memory"),
        ],
        fluid=True,
        className="mb-5",
    )
