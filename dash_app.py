#!/usr/bin/env python3

"""
Plotly Dash app for querying and visualizing data from SQLite databases.
Features advanced search with modular filter builder, multiple operators,
and support for complex queries.

Each feature lives in its own module under src/. Callbacks are registered
with Dash's global `callback` decorator when those modules are imported.
"""

import dash_bootstrap_components as dbc
from dash import Dash

# Imported for their side effect of registering callbacks (summary and counts have no layout section).
from src import columns, counts, export, filters, loading, query, results, summary  # noqa: F401
from src.layout import build_layout

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
app.title = "Database Browser"
app.layout = build_layout()


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=8050)
