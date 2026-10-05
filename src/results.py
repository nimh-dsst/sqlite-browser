"""Results tabs: Table View, Statistics, and Visualizations.

The Summary and Counts tabs are populated by `src.summary` and `src.counts`.
"""

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, callback, dcc, html

from src.components import create_table_with_truncation, get_selected_columns_for_display


def results_section() -> dbc.Row:
    """Row holding the results tabs."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Tabs(
                        id="results-tabs",
                        active_tab="tab-table-view",
                        children=[
                            dbc.Tab(
                                label="Table View",
                                tab_id="tab-table-view",
                                children=[
                                    html.Div(
                                        id="results-info",
                                        className="mb-3 mt-3 small text-muted",
                                    ),
                                    html.Div(
                                        id="sql-display",
                                        className="mb-3 mt-2 p-2 bg-light rounded border",
                                        style={"fontFamily": "monospace", "fontSize": "0.85rem"},
                                    ),
                                    html.H6("Table Display", className="mt-3 mb-2"),
                                    html.P("Table cells are limited to 40 characters for readability. Hover over cells or copy the text to view the full content. Use 'Export Data' to download the full dataset.", className="small text-muted"),
                                    html.Div(
                                        id="table-results",
                                        className="table-responsive",
                                    ),
                                    html.Div(
                                        id="debug-active-cell",
                                        style={"fontSize": "0.8rem", "color": "#666", "marginTop": "10px", "padding": "5px", "backgroundColor": "#f0f0f0"}
                                    ),
                                    dcc.Store(id="table-full-data-store"),

                                ],
                            ),
                            dbc.Tab(
                                label="Summary",
                                tab_id="tab-summary",
                                children=[
                                    html.Div(
                                        id="summary-container",
                                        className="mt-3",
                                    ),
                                ],
                            ),
                            dbc.Tab(
                                label="Counts",
                                tab_id="tab-counts",
                                children=[
                                    html.Div(
                                        id="counts-container",
                                        className="mt-3",
                                    ),
                                ],
                            ),
                            dbc.Tab(
                                label="Statistics",
                                tab_id="tab-statistics",
                                children=[
                                    html.Div(
                                        id="statistics-container",
                                        className="mt-3",
                                    ),
                                ],
                            ),
                            dbc.Tab(
                                label="Visualizations",
                                tab_id="tab-visualizations",
                                children=[
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.H6("Column for Visualization:"),
                                                    dcc.Dropdown(
                                                        id="viz-column-selector",
                                                        placeholder="Select column...",
                                                    ),
                                                ],
                                                width=12,
                                                lg=6,
                                            ),
                                            dbc.Col(
                                                [
                                                    html.H6("Visualization Type:"),
                                                    dcc.RadioItems(
                                                        id="viz-type-selector",
                                                        options=[
                                                            {"label": " Histogram", "value": "histogram"},
                                                            {"label": " Bar Chart", "value": "bar"},
                                                            {"label": " Scatter", "value": "scatter"},
                                                        ],
                                                        value="histogram",
                                                        inline=True,
                                                    ),
                                                ],
                                                width=12,
                                                lg=6,
                                            ),
                                        ],
                                        className="mb-3 mt-3",
                                    ),
                                    dcc.Graph(
                                        id="data-visualization",
                                        config={"responsive": True},
                                    ),
                                ],
                            ),
                        ]
                    ),
                ],
                width=12,
            )
        ]
    )


@callback(
    Output("data-visualization", "figure"),
    Input("current-data-store", "data"),
    Input("column-selector", "data"),
    Input("viz-column-selector", "value"),
    Input("viz-type-selector", "value"),
)
def update_visualization(data, selected_columns, column, viz_type):
    """Update visualization based on selected column and type."""
    if not data or not column:
        return {
            "data": [],
            "layout": go.Layout(
                title="Select a column to visualize",
                xaxis={"title": "X"},
                yaxis={"title": "Y"},
            ),
        }

    df = pd.DataFrame(data)
    df = get_selected_columns_for_display(df, selected_columns)

    if df.shape[1] == 0:
        return {
            "data": [],
            "layout": go.Layout(
                title="No columns selected for visualization",
                xaxis={"title": "X"},
                yaxis={"title": "Y"},
            ),
        }

    if column not in df.columns:
        return {
            "data": [],
            "layout": go.Layout(
                title="Column not found",
                xaxis={"title": "X"},
                yaxis={"title": "Y"},
            ),
        }

    try:
        if viz_type == "histogram":
            fig = px.histogram(
                df,
                x=column,
                title=f"Distribution of {column}",
                nbins=30,
            )
        elif viz_type == "bar":
            # For bar chart, use value counts
            value_counts = df[column].value_counts().head(20)
            fig = px.bar(
                x=value_counts.index,
                y=value_counts.values,
                title=f"Top 20 values in {column}",
                labels={"x": column, "y": "Count"},
            )
        elif viz_type == "scatter":
            # For scatter, create a simple scatter with index
            fig = px.scatter(
                df,
                y=column,
                title=f"Scatter plot of {column}",
                labels={"index": "Row", "y": column},
            )
        else:
            fig = px.histogram(df, x=column, title=f"Distribution of {column}")

        fig.update_layout(height=500, hovermode="x unified")
        return fig

    except Exception as e:
        return {
            "data": [],
            "layout": go.Layout(
                title=f"Error creating visualization: {str(e)}",
                xaxis={"title": "X"},
                yaxis={"title": "Y"},
            ),
        }


@callback(
    Output("statistics-container", "children"),
    Input("current-data-store", "data"),
    Input("column-selector", "data"),
)
def update_statistics(data, selected_columns):
    """Display basic statistics about the data."""
    if not data:
        return html.P("Load data first to see statistics")

    df = pd.DataFrame(data)
    df = get_selected_columns_for_display(df, selected_columns)

    if df.shape[1] == 0:
        return html.P("No columns selected for statistics")

    # Get numeric columns
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    if not numeric_cols:
        return html.P("No numeric columns found for statistics")

    # Create statistics table
    stats_data = []
    for col in numeric_cols:
        stats_data.append(
            {
                "Column": col,
                "Count": df[col].count(),
                "Mean": f"{df[col].mean():.2f}",
                "Std Dev": f"{df[col].std():.2f}",
                "Min": f"{df[col].min():.2f}",
                "Max": f"{df[col].max():.2f}",
            }
        )

    if not stats_data:
        return html.P("No statistics available")

    stats_df = pd.DataFrame(stats_data)
    stats_table = create_table_with_truncation(stats_df)

    return dbc.Card(
        dbc.CardBody(
            [
                html.H6("Numeric Column Statistics"),
                stats_table,
            ]
        )
    )


@callback(
    Output("debug-active-cell", "children"),
    Input("table-results-datatable", "id"),
)
def show_table_info(table_id):
    """Show info about the table."""
    return "Use the search and filter features above to find and query data. Cells display up to 40 characters - copy full text as needed."
