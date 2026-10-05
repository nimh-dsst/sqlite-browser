"""SQLite connection wrapper, filter operator definitions, and SQL string helpers."""

import re
import sqlite3
from typing import Dict, List, Optional, Tuple

import pandas as pd


# Filter operator definitions
FILTER_OPERATORS = {
    "equals": {"label": "equals", "type": "text", "needs_value": True},
    "does_not_equal": {"label": "does not equal", "type": "text", "needs_value": True},
    "like": {"label": "like (contains)", "type": "text", "needs_value": True},
    "not_like": {"label": "not like", "type": "text", "needs_value": True},
    "less_than": {"label": "less than", "type": "number", "needs_value": True},
    "less_than_or_equal": {"label": "less than or equal", "type": "number", "needs_value": True},
    "greater_than": {"label": "greater than", "type": "number", "needs_value": True},
    "greater_than_or_equal": {"label": "greater than or equal", "type": "number", "needs_value": True},
    "in": {"label": "in", "type": "text", "needs_value": True, "help": "comma-separated values"},
    "is_null": {"label": "is null", "type": "none", "needs_value": False},
    "is_not_null": {"label": "is not null", "type": "none", "needs_value": False},
}


class DatabaseConnection:
    """Manages SQLite database connections and queries."""

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self.table_names = []
        self.current_columns = []

    def connect(self) -> bool:
        """Initialize database connection."""
        try:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            self._load_table_names()
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False

    def _load_table_names(self) -> None:
        """Load all table names from the database."""
        if not self.conn:
            return

        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        self.table_names = [row[0] for row in cursor.fetchall()]
        cursor.close()

    def get_tables(self) -> List[str]:
        """Get list of all tables."""
        return self.table_names

    def get_table_info(self, table_name: str) -> Tuple[List[str], int]:
        """Get column names and row count for a table."""
        if not self.conn:
            return [], 0

        cursor = self.conn.cursor()
        
        # Get columns
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        self.current_columns = columns

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        cursor.close()
        return columns, row_count

    def get_columns(self, table_name: str) -> List[str]:
        """Get column names for a table."""
        if not self.conn:
            return []

        cursor = self.conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        cursor.close()
        return columns

    def build_where_clause(self, filters: List[Dict]) -> Tuple[str, List]:
        """Build WHERE clause from filters list.
        
        Returns:
            Tuple of (where_clause_string, parameters_list)
        """
        if not filters:
            return "", []

        conditions = []
        params = []

        for f in filters:
            if not f.get("field") or not f.get("operator"):
                continue

            field = f["field"]
            operator = f["operator"]
            value = f.get("value", "")

            # Build condition based on operator
            if operator == "equals":
                conditions.append(f'"{field}" = ?')
                params.append(value)
            elif operator == "does_not_equal":
                conditions.append(f'"{field}" != ?')
                params.append(value)
            elif operator == "like":
                # LIKE allows wildcard matching; wrap in % for contains
                conditions.append(f'"{field}" LIKE ?')
                params.append(f"%{value}%")
            elif operator == "not_like":
                conditions.append(f'"{field}" NOT LIKE ?')
                params.append(f"%{value}%")
            elif operator == "less_than":
                conditions.append(f'"{field}" < ?')
                params.append(float(value) if value else 0)
            elif operator == "less_than_or_equal":
                conditions.append(f'"{field}" <= ?')
                params.append(float(value) if value else 0)
            elif operator == "greater_than":
                conditions.append(f'"{field}" > ?')
                params.append(float(value) if value else 0)
            elif operator == "greater_than_or_equal":
                conditions.append(f'"{field}" >= ?')
                params.append(float(value) if value else 0)
            elif operator == "in":
                # Split by comma and strip whitespace
                values = [v.strip() for v in value.split(",") if v.strip()]
                if values:
                    placeholders = ",".join(["?" for _ in values])
                    conditions.append(f'"{field}" IN ({placeholders})')
                    params.extend(values)
            elif operator == "is_null":
                conditions.append(f'"{field}" IS NULL')
            elif operator == "is_not_null":
                conditions.append(f'"{field}" IS NOT NULL')

        if not conditions:
            return "", []

        where_clause = " AND ".join(conditions)
        return where_clause, params

    def format_sql_for_display(self, where_clause: str, params: List) -> str:
        """Format SQL WHERE clause with actual parameter values for display.
        
        Args:
            where_clause: WHERE clause with ? placeholders
            params: List of parameter values
            
        Returns:
            WHERE clause with values substituted (for display only, not execution)
        """
        if not params:
            return where_clause
        
        # Replace ? placeholders with actual values
        display_clause = where_clause
        for param in params:
            # Properly quote string values, leave numbers as-is
            if isinstance(param, str):
                # Escape single quotes in strings
                escaped_value = param.replace("'", "''")
                display_clause = display_clause.replace("?", f"'{escaped_value}'", 1)
            else:
                display_clause = display_clause.replace("?", str(param), 1)
        
        return display_clause

    def execute_query(
        self, query: str, limit: Optional[int] = 500
    ) -> Tuple[pd.DataFrame, Optional[str]]:
        """Execute a SQL query and return results as DataFrame."""
        if not self.conn:
            return pd.DataFrame(), "Database not connected"

        try:
            # Add LIMIT clause if not already present and limit is specified
            query = query.strip()
            if limit and "LIMIT" not in query.upper():
                query += f" LIMIT {limit}"

            df = pd.read_sql_query(query, self.conn)
            return df, None
        except Exception as e:
            return pd.DataFrame(), str(e)

    def get_table_data(
        self, table_name: str, filters: List[Dict] = None, limit: Optional[int] = 500
    ) -> Tuple[pd.DataFrame, Optional[str], str]:
        """Get data from a specific table with optional filters.
        
        Returns:
            Tuple of (dataframe, error_message, sql_query_for_display)
        """
        where_clause, params = self.build_where_clause(filters or [])
        
        query = f'SELECT * FROM "{table_name}"'
        if where_clause:
            query += f" WHERE {where_clause}"
        
        if limit is not None:
            query += f" LIMIT {limit}"

        # Build display query with actual values
        display_query = f'SELECT * FROM "{table_name}"'
        if where_clause:
            display_where = self.format_sql_for_display(where_clause, params)
            display_query += f" WHERE {display_where}"
        if limit is not None:
            display_query += f" LIMIT {limit}"

        try:
            if params:
                df = pd.read_sql_query(query, self.conn, params=params)
            else:
                df = pd.read_sql_query(query, self.conn)
            return df, None, display_query
        except Exception as e:
            return pd.DataFrame(), str(e), display_query

    def close(self) -> None:
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None


def remove_trailing_limit_clause(query: str) -> str:
    """Remove a trailing LIMIT/OFFSET clause so summary can profile full results."""
    if not query:
        return query

    stripped = query.strip().rstrip(";")
    pattern = r"(?is)\s+LIMIT\s+\d+\s*(?:OFFSET\s+\d+\s*)?$"
    return re.sub(pattern, "", stripped).strip()
