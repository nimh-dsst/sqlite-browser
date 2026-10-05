"""Summary tab: per-column profile table and quick charts over the full query result."""

from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Input, Output, State, callback, dcc, html
from dash.exceptions import PreventUpdate

from src.components import create_table_with_truncation, get_selected_columns_for_display
from src.database import DatabaseConnection, remove_trailing_limit_clause


def format_summary_value(value) -> str:
    """Format values for summary display."""
    if pd.isna(value):
        return "—"

    if pd.api.types.is_number(value):
        return f"{float(value):.4g}"

    if hasattr(value, "isoformat") and not isinstance(value, str):
        return value.isoformat()

    return str(value)


def build_column_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Build per-column at-a-glance summary for the current data."""
    if df.empty:
        return pd.DataFrame()

    rows = []
    total_rows = len(df)
    missing_tokens = {"", "na", "n/a", "nan", "none", "null"}

    for column in df.columns:
        series = df[column]
        normalized = series.astype("string").str.strip().str.lower()
        missing_mask = series.isna() | normalized.isin(missing_tokens).fillna(False)
        missing_count = int(missing_mask.sum())
        missing_pct = (missing_count / total_rows * 100) if total_rows else 0.0

        non_missing = series[~missing_mask]
        unique_count = int(non_missing.nunique(dropna=True))

        top_counts = non_missing.astype("string").value_counts().head(5)
        top_values = ", ".join([f"{value} ({count})" for value, count in top_counts.items()])
        if not top_values:
            top_values = "—"

        min_value = "—"
        max_value = "—"
        if not non_missing.empty:
            try:
                min_value = format_summary_value(non_missing.min())
                max_value = format_summary_value(non_missing.max())
            except Exception:
                min_value = "—"
                max_value = "—"

        rows.append(
            {
                "Column": column,
                "Data Type": str(series.dtype),
                "Rows": total_rows,
                "Missing": f"{missing_count} ({missing_pct:.1f}%)",
                "Unique Values": unique_count,
                "Top Values (count)": top_values,
                "Min": min_value,
                "Max": max_value,
            }
        )

    return pd.DataFrame(rows)


def build_summary_charts(df: pd.DataFrame):
    """Build one adaptive chart per column and lay them out in a 3-column grid."""
    def truncate_label(label, max_len: int) -> str:
        text = str(label)
        return f"{text[:max_len]}..." if len(text) > max_len else text

    chart_components = []
    no_non_missing_columns = []
    missing_tokens = {"", "na", "n/a", "nan", "none", "null"}

    for column in df.columns:
        series = df[column]
        normalized = series.astype("string").str.strip().str.lower()
        missing_mask = series.isna() | normalized.isin(missing_tokens).fillna(False)
        non_missing = series[~missing_mask]

        total_rows = len(series)
        missing_count = int(missing_mask.sum())
        present_count = total_rows - missing_count
        missing_pct = (missing_count / total_rows * 100) if total_rows else 0.0
        unique_count = int(non_missing.nunique(dropna=True))

        chart_title = f"{column}"
        figure = None
        chart_content = None

        if unique_count <= 1:
            if present_count == 0:
                no_non_missing_columns.append(column)
                continue

            single_value = format_summary_value(non_missing.iloc[0]) if present_count > 0 else "No non-missing value"
            display_single_value = (
                f"{single_value[:30]}..." if isinstance(single_value, str) and len(single_value) > 30 else single_value
            )
            chart_content = html.Div(
                [
                    html.Div("Unique Value", className="text-muted small"),
                    html.Div(display_single_value, style={"fontSize": "1.5rem", "fontWeight": "700", "wordBreak": "break-word"}),
                ],
                style={
                    "height": "280px",
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "textAlign": "center",
                    "padding": "12px",
                    "border": "1px solid #e9ecef",
                    "borderRadius": "6px",
                    "backgroundColor": "#fafafa",
                },
            )
            chart_kind = "single-value-emphasis"
        elif 2 <= unique_count <= 15:
            counts = non_missing.astype("string").value_counts().sort_values(ascending=False)
            # Reverse arrays so the highest count appears at the top in a horizontal bar chart.
            y_values = [truncate_label(v, 40) for v in counts.index.tolist()[::-1]]
            x_values = counts.values.tolist()[::-1]
            figure = go.Figure(
                data=[
                    go.Bar(
                        x=x_values,
                        y=y_values,
                        orientation="h",
                        marker=dict(color="#1f77b4"),
                        hovertemplate="%{y}: %{x}<extra></extra>",
                    )
                ]
            )
            figure.update_layout(
                xaxis_title="Count",
                yaxis_title="",
                yaxis=dict(automargin=True),
            )
            chart_kind = "horizontal-histogram"
        else:
            if pd.api.types.is_numeric_dtype(series):
                figure = px.histogram(
                    x=non_missing,
                    nbins=30,
                    labels={"x": column, "y": "Count"},
                )
            else:
                # For high-cardinality categorical/text columns, show top value frequencies.
                counts = non_missing.astype("string").value_counts().head(20)
                truncated_labels = [truncate_label(v, 20) for v in counts.index]
                figure = px.histogram(
                    x=truncated_labels,
                    y=counts.values,
                    labels={"x": column, "y": "Count"},
                )
            chart_kind = "histogram"

        if figure is not None:
            figure.update_layout(
                title=f"{chart_title}",
                margin=dict(l=20, r=20, t=45, b=30),
                height=280,
                showlegend=False,
            )
            chart_content = dcc.Graph(figure=figure, config={"displayModeBar": False})

        stats_line = html.Div(
            f"Type: {series.dtype} | Unique: {unique_count} | Missing: {missing_count}/{total_rows} ({missing_pct:.1f}%) | Chart: {chart_kind}",
            className="small text-muted mt-1",
        )

        chart_components.append(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H6(chart_title, className="mb-2"),
                            chart_content,
                            stats_line,
                        ]
                    ),
                    className="h-100",
                ),
                width=12,
                lg=4,
            )
        )

    if not chart_components:
        grid = html.P("No chartable summary fields found.", className="text-muted")
    else:
        grid = dbc.Row(chart_components, className="g-3 mb-3")

    return grid, no_non_missing_columns


@callback(
    Output("summary-container", "children"),
    Input("current-sql-store", "data"),
    Input("column-selector", "data"),
    Input("results-tabs", "active_tab"),
    State("db-path-input", "value"),
)
def update_summary(sql_query, selected_columns, active_tab, db_path):
    """Display at-a-glance summary for each selected column."""
    if active_tab != "tab-summary":
        raise PreventUpdate

    if not sql_query or not db_path:
        return html.P("Loading data now...")

    db_path = str(Path(db_path).expanduser())

    try:
        db = DatabaseConnection(db_path)
        if not db.connect():
            return html.P("Could not connect to database for summary")

        summary_query = remove_trailing_limit_clause(sql_query)
        df, error = db.execute_query(summary_query, limit=None)
        db.close()

        if error:
            return html.P(f"Could not compute summary: {error}")
    except Exception as e:
        return html.P(f"Could not compute summary: {str(e)}")

    if df.empty:
        return html.P("No summary available (query returned 0 rows)")

    df = get_selected_columns_for_display(df, selected_columns)

    if df.shape[1] == 0:
        return html.P("No columns selected for summary")

    summary_df = build_column_summary(df)

    if summary_df.empty:
        return html.P("No summary available")

    summary_charts, no_non_missing_columns = build_summary_charts(df)
    summary_table = create_table_with_truncation(summary_df)

    no_non_missing_section = None
    if no_non_missing_columns:
        no_non_missing_section = dbc.Alert(
            [
                html.Div("Columns with no non-missing values:"),
                html.Ul([html.Li(col) for col in no_non_missing_columns], className="mb-0 mt-1"),
            ],
            color="light",
            className="mt-2",
        )

    return dbc.Card(
        dbc.CardBody(
            [
                html.H6("Per-Column Quick Charts", className="mb-2"),
                summary_charts,
                no_non_missing_section,
                html.H6("Column Summary"),
                summary_table,
            ]
        )
    )
