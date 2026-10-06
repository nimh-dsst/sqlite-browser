#!/usr/bin/env python3

"""
Concatenate the same table from multiple SQLite files into one output SQLite file.
Every input table must have the same column names (in any order) to be concatenated.
"""

import argparse
import os
import sqlite3
import sys
from pathlib import Path


def quote_identifier(name):
    """
    Quote an SQLite identifier (table or column name).

    Parameters
    ----------
    name : str
        Raw identifier.

    Returns
    -------
    str
        Identifier wrapped in double quotes, with embedded quotes escaped.
    """
    return '"' + name.replace('"', '""') + '"'


def read_columns(sqlite_file, table):
    """
    Read the column names and declared types of a table.

    Parameters
    ----------
    sqlite_file : pathlib.Path
        Path to the SQLite file.
    table : str
        Name of the table to inspect.

    Returns
    -------
    list of tuple of (str, str) or None
        ``(name, declared_type)`` pairs in table order, or None if the table does not exist.
    """
    # Open read-only so a mistyped path is never created as an empty database
    conn = sqlite3.connect(f"{sqlite_file.resolve().as_uri()}?mode=ro", uri=True)
    try:
        rows = conn.execute(f"PRAGMA table_info({quote_identifier(table)})").fetchall()
    finally:
        conn.close()
    return [(row[1], row[2]) for row in rows] or None


def check_columns(inputs, table):
    """
    Check that every input table has the same set of column names.

    Parameters
    ----------
    inputs : list of pathlib.Path
        Input SQLite files; the first is the reference.
    table : str
        Name of the table to compare.

    Returns
    -------
    list of tuple of (str, str) or None
        Reference ``(name, declared_type)`` pairs if all inputs match, otherwise None.
    """
    reference = None
    all_match = True
    for sqlite_file in inputs:
        columns = read_columns(sqlite_file, table)
        if columns is None:
            print(f"Error: Table '{table}' not found in {sqlite_file}")
            all_match = False
            continue
        print(f"  {sqlite_file}: {len(columns)} columns")

        if reference is None:
            reference = columns
            reference_file = sqlite_file
            continue

        reference_names = {name for name, _ in reference}
        names = {name for name, _ in columns}
        if names != reference_names:
            all_match = False
            print(f"Error: Columns in {sqlite_file} differ from {reference_file}")
            missing = sorted(reference_names - names)
            extra = sorted(names - reference_names)
            if missing:
                print(f"  Missing: {', '.join(missing)}")
            if extra:
                print(f"  Extra: {', '.join(extra)}")

    return reference if all_match else None


def concatenate(inputs, output, table, columns):
    """
    Write the concatenated table to the output file, replacing any existing table.

    Parameters
    ----------
    inputs : list of pathlib.Path
        Input SQLite files, appended in the given order.
    output : pathlib.Path
        Output SQLite file.
    table : str
        Name of the table to read from each input and write to the output.
    columns : list of tuple of (str, str)
        ``(name, declared_type)`` pairs defining the output column order and types.
    """
    quoted_table = quote_identifier(table)
    # Select by name so inputs with a different column order still align
    column_list = ", ".join(quote_identifier(name) for name, _ in columns)
    column_defs = ", ".join(
        f"{quote_identifier(name)} {col_type}".strip() for name, col_type in columns
    )

    conn = sqlite3.connect(str(output))
    try:
        with conn:
            conn.execute(f"DROP TABLE IF EXISTS {quoted_table}")
            conn.execute(f"CREATE TABLE {quoted_table} ({column_defs})")

        for sqlite_file in inputs:
            # ATTACH cannot run inside a transaction, so attach/insert/detach per file
            conn.execute("ATTACH DATABASE ? AS src", (str(sqlite_file),))
            try:
                with conn:
                    cursor = conn.execute(
                        f"INSERT INTO main.{quoted_table} ({column_list}) "
                        f"SELECT {column_list} FROM src.{quoted_table}"
                    )
                print(f"  Appended {cursor.rowcount} rows from {sqlite_file}")
            finally:
                conn.execute("DETACH DATABASE src")

        total = conn.execute(f"SELECT COUNT(*) FROM {quoted_table}").fetchone()[0]
        print(f"  Result: {total} rows, {len(columns)} columns")
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Concatenate the same table from multiple SQLite files into one SQLite file."
    )
    parser.add_argument(
        "inputs", type=Path, nargs="+", metavar="SQLITE_FILE",
        help="Space-separated input SQLite files (each must end in .sqlite)."
    )
    parser.add_argument(
        "-o", "--output", type=Path, metavar="OUTPUT_FILE", required=True,
        help="Path for the output SQLite file (must end in .sqlite)."
    )
    parser.add_argument(
        "-t", "--table", type=str, default="data", metavar="TABLE",
        help="Name of the table to concatenate (default: data)."
    )
    args = parser.parse_args()

    # Validate inputs
    for sqlite_file in args.inputs:
        if sqlite_file.suffix != ".sqlite":
            print(f"Error: Input file must have a .sqlite extension: {sqlite_file}")
            return 1
        if not sqlite_file.is_file():
            print(f"Error: Input file does not exist: {sqlite_file}")
            return 1

    # Validate output
    if args.output.suffix != ".sqlite":
        print(f"Error: Output file must have a .sqlite extension: {args.output}")
        return 1
    if args.output.resolve() in {p.resolve() for p in args.inputs}:
        print(f"Error: Output file cannot also be an input file: {args.output}")
        return 1
    if args.output.exists() and os.stat(args.output).st_mode & 0o222 == 0:
        print(f"Error: Output file already exists, but permissions are locking you out: {args.output}")
        return 1

    try:
        print(f"Checking columns of table '{args.table}' in {len(args.inputs)} files...")
        columns = check_columns(args.inputs, args.table)
        if columns is None:
            print("Error: Input tables cannot be concatenated.")
            return 1

        print(f"Writing concatenated table '{args.table}' to {args.output}...")
        concatenate(args.inputs, args.output, args.table, columns)
    except sqlite3.Error as e:
        print(f"Error: {e}")
        return 1

    print(f"\nSuccess! Concatenated {len(args.inputs)} files into {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
