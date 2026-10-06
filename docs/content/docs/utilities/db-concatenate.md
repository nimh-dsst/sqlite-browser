---
title: "Concatenating SQLite files"
linkTitle: "Concatenating SQLite files"
weight: 20
aliases: ["/docs/db-concatenate/"]
description: "Use db_concatenate.py to stack the same table from several SQLite files into one."
---

`utilities/db_concatenate.py` appends the rows of one table (default `data`) from several `.sqlite` files into a single output `.sqlite` file. This is useful when a dataset was indexed in pieces, for example one file per site produced by [bids2db.py]({{< relref "bids2db" >}}) or [parquets2db.py]({{< relref "parquets2db" >}}).

## Usage

```bash
uv run python utilities/db_concatenate.py SQLITE_FILE [SQLITE_FILE ...] -o OUTPUT_FILE [options]
```

| Argument | Default | Description |
| --- | --- | --- |
| `SQLITE_FILE ...` | required | Space-separated input files; each must end in `.sqlite` |
| `-o` / `--output` | required | Output file; must end in `.sqlite` and must not be one of the inputs |
| `-t` / `--table` | `data` | Table to concatenate from every input |

Example:

```bash
uv run python utilities/db_concatenate.py site1.sqlite site2.sqlite site3.sqlite -o all_sites.sqlite
```

## Notes

- Before writing anything, every input's table must have the **same column names**, in any order. If any input is missing the table or has missing or extra columns, the differences are printed and no output is written.
- Rows are matched by column name, in the order the files are listed. The output uses the column order and declared types of the first input.
- If the output file already exists, its copy of the table is replaced; other tables in it are kept.
- Only column names and declared types are copied. Indexes and constraints (e.g., primary keys) are not.
