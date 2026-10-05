---
title: "Enriching a SQLite database with a TSV join"
linkTitle: "Joining a TSV file"
weight: 60
description: "Use db_join.py to join a TSV or CSV file into an existing SQLite database table."
---

After creating a SQLite file (see [Creating a SQLite file]({{< relref "parquets2db" >}})), you may want to enrich the `data` table with additional per-subject or per-session metadata stored in a separate TSV or CSV file — for example, a phenotype file or an ID-mapping file. `utilities/db_join.py` performs that join and writes the result back into the database.

## Prerequisites

- An existing `.sqlite` database (e.g., produced by `parquets2db.py`)
- A TSV or CSV file with a column that shares values with a column in the database table

## Usage

```bash
uv run python utilities/db_join.py DATABASE CSV_FILE -k DB_KEY -c CSV_KEY [options]
```

### Required arguments

| Argument | Description |
| --- | --- |
| `DATABASE` | Path to the existing `.sqlite` file |
| `CSV_FILE` | Path to the TSV or CSV file to join in |
| `-k` / `--db-key` | Column name **in the database table** to join on |
| `-c` / `--csv-key` | Column name **in the TSV/CSV file** to join on |

### Optional arguments

| Argument | Default | Description |
| --- | --- | --- |
| `-t` / `--table` | `data` | Name of the database table to read from |
| `-j` / `--join-type` | `outer` | Join type: `left`, `right`, `inner`, or `outer` |
| `-o` / `--output-table` | `data` | Name of the table to write the joined result to |
| `--replace` | off | Replace the output table if it already exists |
| `-s` / `--separator` | auto | Column delimiter; auto-detected from file extension (`.tsv`/`.tab` → tab, everything else → comma) |

## Step-by-step

### 1. Identify your join columns

Open `db.sqlite` in SQLite Browser and note the column name you want to join on. Then check your TSV or CSV file for the matching column name — the two do not need to have the same name.

For example, a bids2table-generated database stores the subject identifier in a column called **`ent__sub`** (e.g., `01`, `MOA01`), while a phenotype file or participants TSV typically uses **`participant_id`** (e.g., `sub-01`, `sub-MOA01`).

#### Handling the `sub-` prefix in bids2table databases

BIDS subject identifiers in phenotype and mapping files commonly include a `sub-` prefix that is absent from `ent__sub` values in a bids2table-generated database. If your values don't match, strip the prefix from `participant_id` before running the join:

```bash
python -c "
import pandas as pd
df = pd.read_csv('phenotype.tsv', sep='\t')
df['participant_id'] = df['participant_id'].str.removeprefix('sub-')
df.to_csv('phenotype_stripped.tsv', sep='\t', index=False)
"
```

Then join on `phenotype_stripped.tsv` using `-c participant_id`.

### 2. Choose a join type

| Join type | Rows kept |
| --- | --- |
| `outer` (default) | All rows from both sides; unmatched rows get `NaN` for missing columns |
| `left` | All rows from the database table; unmatched TSV rows are discarded |
| `right` | All rows from the TSV; unmatched database rows are discarded |
| `inner` | Only rows that match on both sides |

For most enrichment workflows where you want to keep all imaging records and simply append metadata columns, **`left`** is the safest choice.

### 3. Run the script

```bash
uv run python utilities/db_join.py \
    db.sqlite \
    FILL_IN_THE_BLANK.tsv \
    -k FILL_IN_THE_BLANK_DB_COLUMN \
    -c FILL_IN_THE_BLANK_TSV_COLUMN \
    --join-type left \
    --replace
```

A realistic example joining a phenotype file into a bids2table database:

```bash
uv run python utilities/db_join.py \
    db.sqlite \
    phenotype_stripped.tsv \
    -k ent__sub \
    -c participant_id \
    --join-type left \
    --replace
```

The script prints progress as it runs.

### 4. Verify the result

Reload `db.sqlite` in SQLite Browser. The `data` table should now contain the original columns plus the new columns from the TSV file.

## Notes

- If the output table already exists, you **must** pass `--replace`; otherwise the script exits with an error. This is intentional — it prevents accidental overwrites.
- If you specify an `--output-table` name that differs from the source `--table`, the original table is left untouched and the joined result is written as a new table alongside it.
- When both the database and TSV have a column with the same name (other than the join key), pandas will suffix them with `_x` (database) and `_y` (TSV) to avoid collisions.
- The separator is auto-detected: `.tsv` and `.tab` files are read as tab-separated; all other extensions are assumed to be comma-separated. Use `-s` to override (e.g., `-s ";"` for semicolon-delimited files).
