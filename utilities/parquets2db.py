#! /usr/bin/env python3

###
# Converts a glob pattern to find many Parquet files into an SQLite file
# (database) using a two-argument CLI and Pandas' read_parquet().
# Afterward, the SQLite file will be browsable in a Flutter web app
###

import argparse
import json
import os
import numpy
import pandas
import sqlite3
from glob import glob
from pathlib import Path

# Python types produced by pandas for nested Parquet columns (struct, list, map)
NESTED_TYPES = (dict, list, tuple, numpy.ndarray)


def _json_default(obj):
    """Convert values that ``json.dumps`` can't handle natively.

    Parameters
    ----------
    obj : object
        A value found inside a nested Parquet cell.

    Returns
    -------
    object
        A JSON-serializable equivalent of ``obj``.
    """
    if isinstance(obj, numpy.ndarray):
        return obj.tolist()
    if isinstance(obj, numpy.generic):
        return obj.item()
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    return str(obj)


def serialize_nested_columns(df):
    """Convert nested cell values to JSON strings so SQLite can store them.

    SQLite only accepts scalar values, but Parquet struct, list, and map
    columns are read by pandas as dicts, arrays, and lists of tuples.

    Parameters
    ----------
    df : pandas.DataFrame
        DataFrame read from one or more Parquet files.

    Returns
    -------
    pandas.DataFrame
        The same DataFrame with nested values replaced by JSON text.
    """
    for col in df.columns:
        if df[col].dtype != object:
            continue
        is_nested = df[col].map(lambda v: isinstance(v, NESTED_TYPES))
        if is_nested.any():
            df.loc[is_nested, col] = df.loc[is_nested, col].map(
                lambda v: json.dumps(v, default=_json_default)
            )
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Convert all glob'ed Parquet files into an SQLite file."
    )
    parser.add_argument(
        "parquet_glob", type=str, metavar="PARQUET_GLOB",
        help="Python glob pattern to all of the Parquet files."
    )
    parser.add_argument(
        "-o", "--output", type=Path, metavar="SQLITE_FILE", required=True,
        help="Path for the output SQLite file."
    )
    args = parser.parse_args()

    # if the output file doesn't have a .sqlite extension, print an error and return
    if args.output.suffix != ".sqlite":
        print(f"Output file must have a .sqlite extension: {args.output}")
        return
    # else if the output file already exists and permissions are locked, print an error and return
    elif args.output.exists() and os.stat(args.output).st_mode & 0o222 == 0:
        print(f"Output file already exists, but permissions are locking you out: {args.output}")
        return

    parquet_glob = args.parquet_glob
    parquet_files = [p for p in glob(parquet_glob) if p.endswith(".parquet")]
    if not parquet_files:
        print(f"No Parquet files found for glob pattern: {parquet_glob}")
        return

    for i, parquet_file in enumerate(parquet_files):
        print(f"Processing {parquet_file}")

        if i == 0:
            # if this is the first parquet file, read it in as "df"
            df = pandas.read_parquet(parquet_file)
        else:
            # else, read it in as "new_df" and concatenate it with "df"
            new_df = pandas.read_parquet(parquet_file)
            df = pandas.concat([df, new_df], ignore_index=True)

    if len(parquet_files) > 0:
        df = serialize_nested_columns(df)
        conn = sqlite3.connect(str(args.output))
        df.to_sql("data", conn, if_exists="replace", index=False)
        conn.close()

        print(f"Successfully converted {parquet_glob} to {args.output}")

if __name__ == "__main__":
    main()
