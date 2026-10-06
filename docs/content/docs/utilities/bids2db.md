---
title: "Creating an SQLite file directly from a BIDS dataset"
linkTitle: "From BIDS to an SQLite file"
weight: 10
aliases: ["/docs/bids2db/"]
description: "Index a BIDS dataset with bids2table, including JSON sidecar metadata, into a SQLite file using bids2db.py."
---

`utilities/bids2db.py` indexes a BIDS dataset with [bids2table](https://github.com/childmindresearch/bids2table) (the same as `b2t2 index`), adds each file's JSON sidecar metadata, and writes the result to a SQLite file that SQLite Browser can open.

Use this instead of [parquets2db.py]({{< relref "parquets2db" >}}) when you want sidecar metadata, because bids2table v2 Parquet files don't include it.

## Prerequisites

- SQLite Browser dependencies installed (`uv sync` in the repo root), which includes bids2table
- A BIDS dataset folder containing `dataset_description.json` and `sub-*` folders

## Usage

```bash
uv run python utilities/bids2db.py PATH -o SQLITE_FILE [options]
```

| Argument | Required | Description |
| --- | --- | --- |
| `PATH` | Yes | Root folder of the BIDS dataset |
| `-o` / `--output` | Yes | Path for the output `.sqlite` file (must end in `.sqlite`) |
| `--subjects` | No | Subject folder names or glob patterns to include, with the `sub-` prefix (e.g. `sub-01 'sub-1*'`) |
| `-j` / `--workers` | No | Worker processes for loading metadata (`0` = main process (the default), `-1` = all cores) |
| `--use-threads` | No | Use threads instead of processes when `--workers` > 0 |
| `-q` / `--no-progress` | No | Disable the progress bar |
| `-v` / `--verbose` | No | `-v` for warnings, `-vv` for more logging |

Example:

```bash
uv run python utilities/bids2db.py /path/to/ds001553 -o data/ds001553.sqlite -j -1
```

## Output

The result is written to a table named **`data`**, with one row per BIDS data file:

- The standard bids2table v2 columns: `dataset`, one column per BIDS entity (`sub`, `ses`, `task`, ...), `datatype`, `suffix`, `ext`, `extra_entities`, `root`, and `path`.
- **`metadata`**: the file's sidecar JSON as text, merged from all applicable sidecars following the BIDS inheritance principle. Files without a sidecar get `{}`.
- `extra_entities` (entities that aren't in the BIDS schema) is stored as JSON text, or `NULL` when there are none.

## Notes

- An existing table in the output file is replaced.
- Sidecar loading reads JSON files from disk for every row, so `-j` can speed up large datasets considerably.
- If no BIDS files are found, the script exits without writing anything; rerun with `-v` to see why.
