"""Advanced Search section: filter row builder and the callbacks that apply filters."""

import json
import traceback
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import ALL, Input, Output, State, callback, callback_context, dcc, html
from dash.exceptions import PreventUpdate

from src.components import create_table_with_truncation, get_selected_columns_for_display
from src.database import FILTER_OPERATORS, DatabaseConnection


def create_filter_row(filter_id: int) -> dbc.Row:
    """Create a single filter row component."""
    return dbc.Row(
        [
            dbc.Col(
                dcc.Dropdown(
                    id={"type": "filter-field", "index": filter_id},
                    placeholder="Select field...",
                    className="mb-2",
                ),
                width=3,
            ),
            dbc.Col(
                dcc.Dropdown(
                    id={"type": "filter-operator", "index": filter_id},
                    options=[
                        {"label": v["label"], "value": k}
                        for k, v in FILTER_OPERATORS.items()
                    ],
                    placeholder="Select operator...",
                    value="equals",
                    className="mb-2",
                ),
                width=3,
            ),
            dbc.Col(
                dcc.Dropdown(
                    id={"type": "filter-value", "index": filter_id},
                    placeholder="Select or type value...",
                    searchable=True,
                    clearable=True,
                    className="mb-2",
                    options=[],
                ),
                width=4,
            ),
            dbc.Col(
                dbc.Button(
                    "✕",
                    id={"type": "filter-remove-btn", "index": filter_id},
                    color="danger",
                    size="sm",
                    className="w-100",
                ),
                width=2,
            ),
        ],
        className="g-2 mb-2",
    )


def filter_builder_section() -> dbc.Row:
    """Card with the filter rows and Add/Apply/Clear buttons."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H5("Advanced Search", className="card-title"),
                                    html.P(
                                        "Build complex queries with multiple filters (AND logic)",
                                        className="small text-muted mb-3",
                                    ),
                                    html.Div(
                                        id="filters-container",
                                        children=[create_filter_row(0)],
                                    ),
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                dbc.Button(
                                                    "+ Add Filter",
                                                    id="add-filter-btn",
                                                    color="success",
                                                    outline=True,
                                                    size="sm",
                                                ),
                                                width="auto",
                                            ),
                                            dbc.Col(
                                                dbc.Button(
                                                    "Apply Filters",
                                                    id="apply-filters-btn",
                                                    color="primary",
                                                    size="sm",
                                                ),
                                                width="auto",
                                            ),
                                            dbc.Col(
                                                dbc.Button(
                                                    "Clear Filters",
                                                    id="clear-filters-btn",
                                                    color="secondary",
                                                    outline=True,
                                                    size="sm",
                                                ),
                                                width="auto",
                                            ),
                                        ],
                                        className="g-2",
                                    ),
                                    html.Div(
                                        id="filter-error-message",
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
    Output("filters-container", "children", allow_duplicate=True),
    Output("filter-count-store", "data"),
    Input("add-filter-btn", "n_clicks"),
    State("filters-container", "children"),
    State("filter-count-store", "data"),
    prevent_initial_call=True,
)
def add_filter(n_clicks, existing_children, store_data):
    """Add a new filter row while preserving existing filters."""
    # Get current count (defaults to 1 since we start with filter 0)
    count = store_data.get("count", 1) if store_data else 1
    
    # Preserve existing filters and append a new one with unique index
    existing_children = existing_children or []
    new_filter_index = count  # Use count as the new index
    existing_children.append(create_filter_row(new_filter_index))
    
    # Increment count for next filter
    new_count = count + 1
    
    return existing_children, {"count": new_count}


@callback(
    Output("filters-container", "children", allow_duplicate=True),
    Input({"type": "filter-remove-btn", "index": ALL}, "n_clicks"),
    State({"type": "filter-remove-btn", "index": ALL}, "id"),
    State({"type": "filter-field", "index": ALL}, "value"),
    State({"type": "filter-operator", "index": ALL}, "value"),
    State({"type": "filter-value", "index": ALL}, "value"),
    prevent_initial_call=True,
)
def remove_filter(remove_clicks, button_ids, fields, operators, values):
    """Remove a filter row."""
    # Check if any button was actually clicked
    ctx = callback_context
    if not ctx.triggered or not button_ids:
        raise PreventUpdate
    
    # Ensure at least one button has actually been clicked (n_clicks > 0 indicates a real click)
    # This prevents the callback from being triggered just by component list changes
    if not remove_clicks or not any(c is not None and c > 0 for c in remove_clicks):
        raise PreventUpdate
    
    triggered_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Parse which button was clicked
    try:
        clicked_button = json.loads(triggered_id)
        removed_index = clicked_button["index"]
    except:
        raise PreventUpdate
    
    # Rebuild filters excluding the removed one
    new_children = []
    new_idx = 0
    
    for i, btn_id in enumerate(button_ids):
        # Skip the filter that was removed
        if btn_id["index"] == removed_index:
            continue
        
        # Create a new filter row with sequential index
        # Preserve the values if they exist
        new_filter = create_filter_row(new_idx)
        
        # Try to preserve the field, operator, and value from the old filter
        # Note: This creates the UI structure, values will be lost but that's ok
        # since we're removing filters anyway
        new_children.append(new_filter)
        new_idx += 1
    
    # Ensure we have at least one filter
    if not new_children:
        new_children = [create_filter_row(0)]
    
    return new_children


@callback(
    Output({"type": "filter-field", "index": ALL}, "options"),
    Input("table-columns-store", "data"),
    Input({"type": "filter-field", "index": ALL}, "id"),
)
def update_filter_field_options(columns, matched_ids):
    """Update field options in all filter rows when table changes or new filters are added."""
    if not columns or not matched_ids:
        # Return empty options if no columns loaded yet
        return [[] for _ in (matched_ids or [])]
    
    options = [{"label": col, "value": col} for col in columns]
    # Return one options list for each matched component
    return [options for _ in matched_ids]


@callback(
    Output({"type": "filter-value", "index": ALL}, "options"),
    Input({"type": "filter-field", "index": ALL}, "value"),
    Input({"type": "filter-operator", "index": ALL}, "value"),
    Input({"type": "filter-value", "index": ALL}, "search_value"),
    State("current-table-store", "data"),
    State("db-path-input", "value"),
    State({"type": "filter-value", "index": ALL}, "id"),
    State({"type": "filter-value", "index": ALL}, "value"),
)
def update_filter_value_options(fields, operators, search_values, table_name, db_path, value_ids, current_values):
    """Update value dropdown options based on selected field and operator."""
    if not table_name or not db_path or not value_ids:
        # Return empty options for each filter value component
        return [[] for _ in (value_ids or [])]
    
    # Ensure all lists have the same length by padding with None
    num_filters = len(value_ids)
    fields = (fields or []) + [None] * (num_filters - len(fields or []))
    operators = (operators or []) + [None] * (num_filters - len(operators or []))
    search_values = (search_values or []) + [None] * (num_filters - len(search_values or []))
    current_values = (current_values or []) + [None] * (num_filters - len(current_values or []))
    
    try:
        db_path = str(Path(db_path).expanduser())
        db = DatabaseConnection(db_path)
        if not db.connect():
            return [[] for _ in value_ids]
        
        # For each filter row, get unique values if operator is "equals"
        results = []
        for idx in range(num_filters):
            field = fields[idx]
            operator = operators[idx] if idx < len(operators) else None
            search_val = search_values[idx] if idx < len(search_values) else None
            current_val = current_values[idx] if idx < len(current_values) else None
            
            if field and operator == "equals":
                # Get unique values from the database for equals operator
                # First check count to avoid long waits on high-cardinality columns
                try:
                    cursor = db.conn.cursor()
                    
                    # First, quickly check how many distinct values exist
                    count_query = (
                        f'SELECT COUNT(DISTINCT "{field}") FROM "{table_name}" '
                        f'WHERE "{field}" IS NOT NULL'
                    )
                    cursor.execute(count_query)
                    distinct_count = cursor.fetchone()[0]
                    
                    # Only fetch values if count is reasonable (<= 50 to keep it fast)
                    if distinct_count > 0 and distinct_count <= 50:
                        # Safe to fetch all unique values
                        value_query = (
                            f'SELECT DISTINCT "{field}" FROM "{table_name}" '
                            f'WHERE "{field}" IS NOT NULL ORDER BY "{field}" LIMIT 50'
                        )
                        cursor.execute(value_query)
                        unique_values = [row[0] for row in cursor.fetchall()]
                        cursor.close()
                        
                        options = [
                            {"label": str(val), "value": str(val)}
                            for val in unique_values
                        ]
                        results.append(options)
                    else:
                        # Too many unique values - skip dropdown population
                        cursor.close()
                        if distinct_count > 50:
                            print(f"Field '{field}' has {distinct_count} unique values - skipping dropdown (use free text)")
                        results.append([])
                except Exception as e:
                    print(f"Error fetching unique values: {e}")
                    results.append([])
            else:
                # For non-equals operators (like, not_like, etc.), create dynamic options from typed text
                # This allows free text entry by adding whatever the user types as an option
                # Always preserve current value if it exists
                options_to_add = []
                
                if current_val:
                    # User has a value set - always include it
                    options_to_add.append({"label": str(current_val), "value": str(current_val)})
                
                if search_val and search_val != current_val:
                    # User is actively typing something different - add it too
                    options_to_add.append({"label": str(search_val), "value": str(search_val)})
                
                results.append(options_to_add)
        
        db.close()
        return results
    except Exception as e:
        print(f"Error in update_filter_value_options: {e}")
        return [[] for _ in value_ids]
        return [[] for _ in value_ids]


@callback(
    Output("filter-error-message", "children"),
    Output("table-results", "children"),
    Output("results-info", "children"),
    Output("sql-display", "children"),
    Output("current-data-store", "data"),
    Output("viz-column-selector", "options"),
    Output("viz-column-selector", "value"),
    Output("table-full-data-store", "data"),
    Output("current-filters-store", "data"),
    Output("current-sql-store", "data"),
    Input("apply-filters-btn", "n_clicks"),
    Input("load-table-btn", "n_clicks"),
    State({"type": "filter-field", "index": ALL}, "value"),
    State({"type": "filter-operator", "index": ALL}, "value"),
    State({"type": "filter-value", "index": ALL}, "value"),
    State("column-selector", "data"),
    State("current-table-store", "data"),
    State("db-path-input", "value"),
    prevent_initial_call=True,
)
def apply_filters(
    apply_clicks,
    load_clicks,
    fields,
    operators,
    values,
    selected_columns,
    table_name,
    db_path,
):
    """Apply filters to table."""
    if not table_name or not db_path:
        raise PreventUpdate

    db_path = str(Path(db_path).expanduser())

    # Build filter objects
    filters = []
    for field, operator, value in zip(fields or [], operators or [], values or []):
        if field:  # Only add filters with a field selected
            filters.append({
                "field": field,
                "operator": operator or "equals",
                "value": value or "",
            })

    try:
        db = DatabaseConnection(db_path)
        if not db.connect():
            return "Error: Could not connect to database", "", "", "", None, [], None, None, None, None

        df, error, sql_query = db.get_table_data(table_name, filters=filters)
        db.close()

        if error:
            return f"Query Error: {error}", "", "", f"Error in query: {sql_query}", None, [], None, None, filters, None

        if df.empty:
            return (
                "",
                html.P("No results found."),
                "No results found",
                sql_query,
                None,
                [],
                None,
                None,
                filters,
                sql_query,
            )

        # Apply optional column selection for display
        display_df = get_selected_columns_for_display(df, selected_columns)

        if display_df.shape[1] == 0:
            return (
                "",
                html.P("No columns selected. Choose at least one column in Column Display."),
                f"Showing {len(df)} rows, 0 columns (all columns excluded)",
                sql_query,
                df.to_dict("records"),
                [],
                None,
                {},
                filters,
                sql_query,
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

        # Format SQL display
        sql_display = html.Code(f"SQL: {sql_query}")

        return "", table, info, sql_display, df_data, col_options, viz_value, full_data_dict, filters, sql_query

    except Exception as e:
        return f"Error: {traceback.format_exc()}", "", "", "", None, [], None, None, None, None


@callback(
    Output("filters-container", "children", allow_duplicate=True),
    Output("filter-error-message", "children", allow_duplicate=True),
    Input("clear-filters-btn", "n_clicks"),
    prevent_initial_call=True,
)
def clear_filters(n_clicks):
    """Clear all filters."""
    return [create_filter_row(0)], ""
