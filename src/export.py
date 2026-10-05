"""Export section: write the full filtered table and its SQL to timestamped files."""

from datetime import datetime
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Input, Output, State, callback, html

from src.components import get_selected_columns_for_display
from src.database import DatabaseConnection


def export_section() -> dbc.Row:
    """Card with the export directory input and Export button."""
    return dbc.Row(
        [
            dbc.Col(
                [
                    dbc.Card(
                        [
                            dbc.CardBody(
                                [
                                    html.H5("Export Filtered Table", className="card-title"),
                                    dbc.InputGroup(
                                        [
                                            dbc.Input(
                                                id="export-path-input",
                                                placeholder="Enter directory path (e.g., C:/Users/username/Desktop)",
                                                type="text",
                                                value="./data/exports",
                                            ),
                                        ],
                                        className="mb-3",
                                    ),
                                    dbc.Checkbox(
                                        id="export-selected-columns-only",
                                        label="Export only currently selected/displayed columns",
                                        value=False,
                                        className="mb-3",
                                    ),
                                    dbc.Button(
                                        "Export Filtered Table",
                                        id="export-table-btn",
                                        color="primary",
                                        size="lg",
                                        className="w-100",
                                        style={
                                            "backgroundColor": "#003366",
                                            "color": "white",
                                            "fontWeight": "bold",
                                            "fontSize": "1.2rem",
                                            "padding": "15px",
                                        },
                                    ),
                                    html.Div(
                                        id="export-status-message",
                                        className="mt-2 small",
                                    ),
                                ]
                            )
                        ]
                    ),
                ],
                width=12,
            )
        ],
        className="mb-4 mt-4",
    )


@callback(
    Output("export-status-message", "children"),
    Output("export-status-message", "className"),
    Input("export-table-btn", "n_clicks"),
    State("export-path-input", "value"),
    State("export-selected-columns-only", "value"),
    State("column-selector", "data"),
    State("current-filters-store", "data"),
    State("current-table-store", "data"),
    State("db-path-input", "value"),
    prevent_initial_call=True,
)
def export_filtered_table(
    n_clicks,
    export_path,
    export_selected_only,
    selected_columns,
    filters,
    table_name,
    db_path,
):
    """Export the filtered table to a TSV file with timestamp.
    Re-executes the query without LIMIT to get all matching rows."""
    if not table_name or not db_path:
        return "No data to export. Please load and filter a table first.", "mt-2 small text-danger"
    
    if not export_path:
        return "Please enter a directory path.", "mt-2 small text-danger"
    
    try:
        # Expand user path and create Path object
        export_dir = Path(export_path).expanduser()
        
        # Check if directory exists
        if not export_dir.exists():
            # Try to create the directory
            try:
                export_dir.mkdir(parents=True, exist_ok=True)
            except Exception as mkdir_error:
                return f"Error: Directory does not exist and could not be created: {export_path}", "mt-2 small text-danger"
        
        if not export_dir.is_dir():
            return f"Error: Path is not a directory: {export_path}", "mt-2 small text-danger"
        
        # Re-execute the query WITHOUT the LIMIT to get all data
        db_path_expanded = str(Path(db_path).expanduser())
        db = DatabaseConnection(db_path_expanded)
        if not db.connect():
            return "Error: Could not connect to database", "mt-2 small text-danger"
        
        # Get ALL data by passing limit=None
        df, error, sql_query = db.get_table_data(table_name, filters=filters or [], limit=None)
        db.close()
        
        if error:
            return f"Query Error: {error}", "mt-2 small text-danger"
        
        if df.empty:
            return "No data to export (query returned 0 rows).", "mt-2 small text-danger"

        exported_df = df
        export_sql_query = sql_query
        
        if export_selected_only:
            exported_df = get_selected_columns_for_display(df, selected_columns)
            if exported_df.shape[1] == 0:
                return (
                    "Export failed: no columns selected. Select at least one column or uncheck selected-columns-only export.",
                    "mt-2 small text-danger",
                )
            
            # Build SQL query with explicit column names instead of SELECT *
            selected_col_names = ', '.join([f'"{col}"' for col in exported_df.columns])
            export_sql_query = sql_query.replace('SELECT *', f'SELECT {selected_col_names}', 1)
        
        # Create timestamp in YYYYMMDD_hhmmss format
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create filenames
        basename = f"{timestamp}_dataset_browser_export"
        tsv_filename = f"{basename}.tsv"
        query_filename = f"{basename}_query.txt"
        
        tsv_path = export_dir / tsv_filename
        query_path = export_dir / query_filename
        
        # Export data to TSV
        exported_df.to_csv(tsv_path, sep="\t", index=False)
        
        # Export SQL query to text file
        with open(query_path, "w", encoding="utf-8") as f:
            f.write(export_sql_query)
        
        return (
            f"✓ Successfully exported {len(exported_df)} rows and {len(exported_df.columns)} columns to: {tsv_path}\n"
            f"✓ SQL query saved to: {query_path}"
        ), "mt-2 small text-success"
        
    except Exception as e:
        return f"Error exporting file: {str(e)}", "mt-2 small text-danger"
