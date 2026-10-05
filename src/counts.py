"""Counts tab: category-count treemap/sunburst and the unique-combinations table."""

from pathlib import Path

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import ALL, Input, Output, State, callback, callback_context, dcc, html
from dash.dash_table import DataTable
from dash.exceptions import PreventUpdate

from src.components import get_selected_columns_for_display
from src.database import DatabaseConnection, remove_trailing_limit_clause


def build_counts_breakdown_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Build long-form category counts for all columns with >1 unique non-missing value."""
    if df.empty:
        return pd.DataFrame(columns=["Field", "Category", "Count", "DataType", "UniqueValues"])

    rows = []
    missing_tokens = {"", "na", "n/a", "nan", "none", "null"}

    for column in df.columns:
        series = df[column]
        as_text = series.astype("string").str.strip()
        normalized = as_text.str.lower()
        missing_mask = series.isna() | normalized.isin(missing_tokens).fillna(False)
        non_missing = series[~missing_mask]
        unique_non_missing = int(non_missing.nunique(dropna=True))

        if unique_non_missing <= 1:
            continue

        category_series = as_text.where(~missing_mask, "(Missing)").fillna("(Missing)")
        value_counts = category_series.value_counts(dropna=False)

        for category, count in value_counts.items():
            rows.append(
                {
                    "Field": column,
                    "Category": str(category),
                    "Count": int(count),
                    "DataType": str(series.dtype),
                    "UniqueValues": unique_non_missing,
                }
            )

    if not rows:
        return pd.DataFrame(columns=["Field", "Category", "Count", "DataType", "UniqueValues"])

    result = pd.DataFrame(rows)
    return result.sort_values(["Field", "Count", "Category"], ascending=[True, False, True]).reset_index(drop=True)


def collapse_small_categories(counts_df: pd.DataFrame, max_categories_per_field: int = 40) -> pd.DataFrame:
    """Keep top categories per field and roll up remaining categories into an 'Other' bucket."""
    if counts_df.empty:
        return counts_df

    reduced_rows = []
    for field in counts_df["Field"].unique().tolist():
        field_df = counts_df[counts_df["Field"] == field].sort_values("Count", ascending=False)
        head_df = field_df.head(max_categories_per_field)
        for _, row in head_df.iterrows():
            reduced_rows.append(row.to_dict())

        tail_df = field_df.iloc[max_categories_per_field:]
        if not tail_df.empty:
            reduced_rows.append(
                {
                    "Field": field,
                    "Category": f"Other ({len(tail_df)} categories)",
                    "Count": int(tail_df["Count"].sum()),
                    "DataType": str(head_df.iloc[0]["DataType"]),
                    "UniqueValues": int(head_df.iloc[0]["UniqueValues"]),
                }
            )

    return pd.DataFrame(reduced_rows)


def build_counts_treemap(counts_df: pd.DataFrame) -> go.Figure:
    """Build a treemap from Field -> Category counts."""
    fig = px.treemap(
        counts_df,
        path=["Field", "Category"],
        values="Count",
        color="Count",
        color_continuous_scale="Blues",
    )
    fig.update_layout(
        title="Treemap of Category Counts",
        margin=dict(l=20, r=20, t=50, b=20),
        height=650,
    )
    return fig


def build_counts_sunburst(counts_df: pd.DataFrame) -> go.Figure:
    """Build a sunburst chart from Field -> Category counts."""
    fig = px.sunburst(
        counts_df,
        path=["Field", "Category"],
        values="Count",
        color="Count",
        color_continuous_scale="Blues",
    )
    fig.update_layout(
        title="Sunburst of Category Counts",
        margin=dict(l=20, r=20, t=50, b=20),
        height=650,
    )
    return fig


def build_unique_categorical_combinations(df: pd.DataFrame) -> pd.DataFrame:
    """Build full unique-combination counts across eligible columns in alphanumeric order."""
    if df.empty:
        return pd.DataFrame()

    eligible_columns = []
    missing_tokens = {"", "na", "n/a", "nan", "none", "null"}

    for column in df.columns:
        series = df[column]
        normalized = series.astype("string").str.strip().str.lower()
        missing_mask = series.isna() | normalized.isin(missing_tokens).fillna(False)
        non_missing = series[~missing_mask]
        unique_non_missing = int(non_missing.nunique(dropna=True))

        if unique_non_missing > 1:
            eligible_columns.append(column)

    if not eligible_columns:
        return pd.DataFrame()

    combination_df = pd.DataFrame()
    for column in eligible_columns:
        as_text = df[column].astype("string").str.strip()
        normalized = as_text.str.lower()
        cleaned = as_text.where(~normalized.isin(missing_tokens).fillna(False), "(Missing)").fillna("(Missing)")
        combination_df[column] = cleaned

    grouped = (
        combination_df
        .groupby(eligible_columns, dropna=False)
        .size()
        .reset_index(name="Count")
        .sort_values(by=eligible_columns, ascending=True)
        .reset_index(drop=True)
    )
    return grouped


def render_counts_combinations_table(df: pd.DataFrame) -> DataTable:
    """Render unique combinations table with scrollable, non-paginated rows."""
    if df.empty:
        return DataTable(id="counts-combinations-table", data=[], columns=[])

    columns = [{"name": col, "id": col} for col in df.columns]
    return DataTable(
        id="counts-combinations-table",
        data=df.to_dict("records"),
        columns=columns,
        row_selectable=False,
        selected_rows=[],
        cell_selectable=False,
        virtualization=False,
        page_action="none",
        style_cell={
            "whiteSpace": "nowrap",
            "overflow": "hidden",
            "textOverflow": "ellipsis",
            "maxWidth": "260px",
            "padding": "8px 6px",
            "textAlign": "left",
        },
        style_table={
            "overflowX": "auto",
            "overflowY": "auto",
            "maxHeight": "700px",
        },
        style_header={
            "fontWeight": "bold",
            "backgroundColor": "#f8f9fa",
            "textAlign": "left",
            "padding": "8px 6px",
            "position": "sticky",
            "top": "0",
            "zIndex": "1",
        },
        style_data_conditional=[
            {"if": {"row_index": "odd"}, "backgroundColor": "#f9f9f9"}
        ],
    )


@callback(
    Output("counts-container", "children"),
    Input("current-sql-store", "data"),
    Input("column-selector", "data"),
    Input("results-tabs", "active_tab"),
    State("db-path-input", "value"),
)
def update_counts(sql_query, selected_columns, active_tab, db_path):
    """Display category-count hierarchies for columns with more than one unique value."""
    if active_tab != "tab-counts":
        raise PreventUpdate

    if not sql_query or not db_path:
        return html.P("Loading data now...")

    db_path = str(Path(db_path).expanduser())

    try:
        db = DatabaseConnection(db_path)
        if not db.connect():
            return html.P("Could not connect to database for counts")

        counts_query = remove_trailing_limit_clause(sql_query)
        df, error = db.execute_query(counts_query, limit=None)
        db.close()

        if error:
            return html.P(f"Could not compute counts: {error}")
    except Exception as e:
        return html.P(f"Could not compute counts: {str(e)}")

    if df.empty:
        return html.P("No counts available (query returned 0 rows)")

    df = get_selected_columns_for_display(df, selected_columns)
    if df.shape[1] == 0:
        return html.P("No columns selected for counts")

    counts_df = build_counts_breakdown_dataframe(df)
    if counts_df.empty:
        return html.P("No multi-category columns found (all selected fields have <= 1 unique non-missing value)")

    display_counts_df = collapse_small_categories(counts_df, max_categories_per_field=35)
    combinations_df = build_unique_categorical_combinations(df)

    treemap_figure = build_counts_treemap(display_counts_df)
    sunburst_figure = build_counts_sunburst(display_counts_df)

    field_count = counts_df["Field"].nunique()
    category_count = counts_df.shape[0]

    combinations_section = html.P(
        "No columns with >1 unique non-missing value were available for combinations.",
        className="small text-muted",
    )
    if not combinations_df.empty:
        combination_columns = combinations_df.columns.tolist()
        sort_buttons = []
        for col in combination_columns:
            sort_buttons.append(
                html.Div(
                    [
                        html.Span(col, className="small fw-bold me-2"),
                        dbc.Button(
                            "Asc",
                            id={"type": "counts-sort-asc-btn", "index": col},
                            color="secondary",
                            outline=True,
                            size="sm",
                            className="me-1",
                        ),
                        dbc.Button(
                            "Desc",
                            id={"type": "counts-sort-desc-btn", "index": col},
                            color="secondary",
                            outline=True,
                            size="sm",
                            className="me-3",
                        ),
                    ],
                    className="d-inline-flex align-items-center mb-2",
                )
            )

        groupable_columns = [col for col in combination_columns if col != "Count"]
        default_aggregate_columns = groupable_columns[:1]
        combinations_section = html.Div(
            [
                html.H6("Unique Value Combinations (Full Data)", className="mb-2"),
                html.P(
                    "Suggestion: Using less columns in the Column Display toggle above is recommended.",
                    className="small text-muted mb-2",
                ),
                dcc.Store(
                    id="counts-combinations-store",
                    data=combinations_df.to_dict("records"),
                ),
                dcc.Store(
                    id="counts-combinations-sort-store",
                    data={"column": "Count", "ascending": False},
                ),
                html.Div(
                    [
                        html.Div("Aggregate counts by:", className="small fw-bold mb-1"),
                        html.P(
                            "Select one or more columns to group rows before counting combinations.",
                            className="small text-muted mb-1",
                        ),
                        dbc.Checklist(
                            id="counts-combo-columns-checklist",
                            options=[{"label": col, "value": col} for col in groupable_columns],
                            value=default_aggregate_columns,
                            inline=True,
                            className="mb-2",
                        ),
                        html.Div("Sort controls", className="small fw-bold mb-1"),
                        html.P(
                            "Use Asc or Desc for any column to reorder the current grouped counts table.",
                            className="small text-muted mb-1",
                        ),
                        html.Div(sort_buttons, className="mb-2"),
                        html.Div(id="counts-combinations-sort-indicator", className="small text-muted mb-2"),
                        html.Div(id="counts-combinations-table-container"),
                    ]
                ),
            ]
        )

    return dbc.Card(
        dbc.CardBody(
            [
                combinations_section,
                html.H6("Category Counts Across Multi-Value Fields", className="mb-2"),
                html.P(
                    f"Built from {field_count} fields and {category_count} total field-category counts. "
                    "Treemap and sunburst roll up very small categories into 'Other' per field for readability.",
                    className="small text-muted",
                ),
                dcc.Graph(figure=treemap_figure, config={"responsive": True}),
                dcc.Graph(figure=sunburst_figure, config={"responsive": True}),
            ]
        )
    )


@callback(
    Output("counts-combinations-table-container", "children"),
    Output("counts-combinations-sort-indicator", "children"),
    Output("counts-combinations-sort-store", "data"),
    Input({"type": "counts-sort-asc-btn", "index": ALL}, "n_clicks"),
    Input({"type": "counts-sort-desc-btn", "index": ALL}, "n_clicks"),
    Input("counts-combo-columns-checklist", "value"),
    State({"type": "counts-sort-asc-btn", "index": ALL}, "id"),
    State({"type": "counts-sort-desc-btn", "index": ALL}, "id"),
    State("counts-combinations-store", "data"),
    State("counts-combinations-sort-store", "data"),
    prevent_initial_call=False,
)
def update_counts_combinations_table(
    asc_clicks,
    desc_clicks,
    included_columns,
    asc_ids,
    desc_ids,
    combinations_data,
    current_sort,
):
    """Sort and aggregate the unique combinations table based on user controls."""
    if not combinations_data:
        return html.P("No combination data available."), "", {"column": "Count", "ascending": False}

    df = pd.DataFrame(combinations_data)
    if df.empty:
        return html.P("No combination data available."), "", {"column": "Count", "ascending": False}

    sort_state = current_sort or {"column": "Count", "ascending": False}
    triggered_id = callback_context.triggered_id

    if isinstance(triggered_id, dict):
        sort_column = triggered_id.get("index")
        if triggered_id.get("type") == "counts-sort-asc-btn":
            sort_state = {"column": sort_column, "ascending": True}
        elif triggered_id.get("type") == "counts-sort-desc-btn":
            sort_state = {"column": sort_column, "ascending": False}

    all_groupable_columns = [col for col in df.columns if col != "Count"]
    included_columns = included_columns or []
    valid_included = [col for col in all_groupable_columns if col in included_columns]

    if valid_included:
        display_df = (
            df.groupby(valid_included, dropna=False, as_index=False)["Count"]
            .sum()
            .reset_index(drop=True)
        )
    else:
        display_df = pd.DataFrame({"Count": [int(df["Count"].sum())]})

    sort_col = sort_state.get("column", "Count")
    ascending = bool(sort_state.get("ascending", False))
    if sort_col not in display_df.columns:
        sort_col = "Count" if "Count" in display_df.columns else display_df.columns[0]
        ascending = False if sort_col == "Count" else True

    display_df = display_df.sort_values(by=[sort_col], ascending=[ascending]).reset_index(drop=True)
    table_component = render_counts_combinations_table(display_df)
    sort_direction = "ascending" if ascending else "descending"
    indicator = f"Sorted by {sort_col} ({sort_direction})"
    return table_component, indicator, {"column": sort_col, "ascending": ascending}
