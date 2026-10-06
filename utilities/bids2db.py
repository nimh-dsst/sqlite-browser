#! /usr/bin/env python3

###
# Indexes a BIDS dataset with bids2table (like `b2t2 index`), adds each file's
# JSON sidecar metadata as a "metadata" column, and writes it to an SQLite file
# (database) browsable in SQLite Browser.
###

import argparse
import concurrent.futures
import json
import logging
import os
import sqlite3
from pathlib import Path

import bids2table as b2t2
from tqdm import tqdm


def load_metadata_json(file_path):
    """Load a BIDS file's inherited sidecar metadata as a JSON string.

    Parameters
    ----------
    file_path : str
        Absolute path to a BIDS data file.

    Returns
    -------
    str
        JSON text of the merged sidecar metadata, ``"{}"`` if there is none.
    """
    return json.dumps(b2t2.load_bids_metadata(file_path, inherit=True))


def serialize_extra_entities(value):
    """Convert an ``extra_entities`` map cell to JSON text for SQLite.

    Parameters
    ----------
    value : list of tuple or None
        Map value as read by pyarrow into pandas, a list of ``(key, value)`` pairs.

    Returns
    -------
    str or None
        JSON object text, or ``None`` if the map is missing or empty.
    """
    return json.dumps(dict(value)) if value else None


def main():
    parser = argparse.ArgumentParser(
        description="Index a BIDS dataset with bids2table, including sidecar "
        "metadata, into an SQLite file."
    )
    parser.add_argument(
        "path", type=Path, metavar="PATH",
        help="Root folder of the BIDS dataset."
    )
    parser.add_argument(
        "-o", "--output", type=Path, metavar="SQLITE_FILE", required=True,
        help="Path for the output SQLite file."
    )
    parser.add_argument(
        "--subjects", metavar="SUB", type=str, nargs="+", default=None,
        help="List of subject folder names or glob patterns to only include in the "
        "index, including the 'sub-' prefix (e.g. sub-01 'sub-1*')."
    )
    parser.add_argument(
        "-j", "--workers", type=int, default=0,
        help="Number of worker processes for loading sidecar metadata. Setting to -1 "
        "runs as many workers as there are cores available. Setting to 0 runs in the "
        "main process. (default: %(default)d)"
    )
    parser.add_argument(
        "--use-threads", action="store_true",
        help="Use threads instead of processes when workers > 0."
    )
    parser.add_argument(
        "-q", "--no-progress", action="store_true",
        help="Disable the progress bar."
    )
    parser.add_argument(
        "-v", "--verbose", action="count", default=0,
        help="Increase logging. -v enables warnings. -vv enables even more logging."
    )
    args = parser.parse_args()

    logging.getLogger("bids2table").setLevel(
        ["ERROR", "WARNING", "INFO"][min(args.verbose, 2)]
    )

    # if the output file doesn't have a .sqlite extension, print an error and return
    if args.output.suffix != ".sqlite":
        print(f"Output file must have a .sqlite extension: {args.output}")
        return
    # else if the output file already exists and permissions are locked, print an error and return
    elif args.output.exists() and os.stat(args.output).st_mode & 0o222 == 0:
        print(f"Output file already exists, but permissions are locking you out: {args.output}")
        return

    if not args.path.is_dir():
        print(f"BIDS dataset folder not found: {args.path}")
        return

    print(f"Indexing {args.path}")
    table = b2t2.index_dataset(args.path, include_subjects=args.subjects)
    if table.num_rows == 0:
        print(f"No BIDS files found in: {args.path} (use -v for details)")
        return

    df = table.to_pandas()
    # "root" is dictionary-encoded (categorical in pandas); store it as plain text
    df["root"] = df["root"].astype(str)
    df["extra_entities"] = df["extra_entities"].map(serialize_extra_entities)

    file_paths = [str(Path(r) / p) for r, p in zip(df["root"], df["path"])]
    max_workers = None if args.workers == -1 else args.workers
    progress = dict(
        total=len(file_paths), desc="Loading metadata", disable=args.no_progress
    )
    if max_workers == 0:
        metadata = list(tqdm(map(load_metadata_json, file_paths), **progress))
    else:
        executor_cls = (
            concurrent.futures.ThreadPoolExecutor if args.use_threads
            else concurrent.futures.ProcessPoolExecutor
        )
        # Chunking amortizes inter-process overhead and keeps sidecar caching useful
        with executor_cls(max_workers=max_workers) as executor:
            metadata = list(tqdm(
                executor.map(load_metadata_json, file_paths, chunksize=64), **progress
            ))
    df["metadata"] = metadata

    conn = sqlite3.connect(str(args.output))
    df.to_sql("data", conn, if_exists="replace", index=False)
    conn.close()

    print(f"Successfully indexed {len(df)} files from {args.path} to {args.output}")


if __name__ == "__main__":
    main()
