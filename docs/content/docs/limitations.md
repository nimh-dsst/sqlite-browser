---
title: "Limitations"
linkTitle: "Limitations"
weight: 50
description: "Known constraints and boundaries of SQLite Browser."
---

## Read-only access

SQLite Browser does not support `INSERT`, `UPDATE`, or `DELETE` statements. Any custom SQL that attempts to modify data will be rejected. This is intentional — the tool is designed exclusively for exploration and analysis.

## SQLite only

Only SQLite database files (`.sqlite`, `.db`) are supported. PostgreSQL, MySQL, DuckDB, and other database engines are not compatible.

## Single connection, no pooling

Each browser session opens a single connection to the database file. There is no connection pooling. Concurrent sessions from multiple browser tabs or users accessing the same running instance may experience contention.

## Performance with large datasets

The default query result limit is **500 rows**. This keeps the interface responsive but means large tables are not fully loaded by default. Performance may degrade noticeably for tables with more than 100,000 rows, particularly in the **Summary** and **Counts** tabs which scan the full result set.

If you need to work with very large tables, use focused SQL queries with tight `WHERE` clauses and explicit `LIMIT` values rather than loading an entire table at once.
