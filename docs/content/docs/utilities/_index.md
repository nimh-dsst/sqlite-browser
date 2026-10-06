---
title: "Utilities"
linkTitle: "Utilities"
weight: 55
description: "Command-line scripts for building and preparing SQLite files for SQLite Browser."
---

SQLite Browser opens existing SQLite files. Use these scripts in `utilities/` when you need to create one from your data, merge several into one, or add extra columns before browsing. They are listed in order of preference.

1. [Indexing a BIDS dataset]({{< relref "bids2db" >}}): build a SQLite file directly from a BIDS dataset, including JSON sidecar metadata.
2. [Concatenating SQLite files]({{< relref "db-concatenate" >}}): stack the same table from several SQLite files into one.
3. [Joining a TSV file]({{< relref "db-join" >}}): add per-subject or per-session metadata from a TSV or CSV file to an existing database.
4. [Creating a SQLite file from Parquet files]({{< relref "parquets2db" >}}): convert existing Parquet files, such as bids2table output, into a SQLite file.
