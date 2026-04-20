---
title: "Usage"
linkTitle: "Usage"
weight: 30
description: "A walkthrough of the full SQLite Browser workflow."
---

## 1. Load a database

Enter the full path to your `.sqlite` file in the **Database path** field and click **Load**.

```
C:\path\to\database.sqlite
./data/my_db.sqlite
```

The app displays the available tables once the file is loaded successfully.

## 2. Select a table

Choose a table from the dropdown and click **Load Table**. The app shows:

- The list of column names and their types
- The total row count
- Populated filter field selectors ready for use

## 3. Filter with Advanced Search

The **Advanced Search** section lets you build multi-condition queries without writing SQL.

1. Select a **field** (column name)
2. Choose an **operator** (equals, contains, greater than, etc.)
3. Enter a **value** — press **Enter** after typing a value manually
4. Click **+ Add Filter** to add another condition (all conditions are combined with AND)
5. Click **Apply Filters** to run the query

For the full list of operators and examples see [Advanced Usage]({{< relref "advanced-usage" >}}).

## 4. Execute a custom SQL query (optional)

Use the **Execute Custom Query** section to write any SQL you need. Click **Execute Query** and results appear in the **Table View** tab along with the generated SQL for reference.

See [Advanced Usage]({{< relref "advanced-usage" >}}) for example queries.

## 5. Analyze and explore

Switch between tabs to dig deeper into your data:

| Tab | What it shows |
|---|---|
| **Table View** | Paginated query results |
| **Summary** | Per-column profile: missingness, unique count, top values, min/max, data type |
| **Counts** | Categorical combination counts. Use **Aggregate counts by** to choose grouping columns. Sort any column with the **Asc/Desc** controls. Treemap and sunburst charts show distribution across multi-value fields. |
| **Statistics** | Descriptive statistics for numeric columns |
| **Visualizations** | Histograms, bar charts, and scatter plots. Select a column and chart type to render. |

## 6. Export results

Click **Export to TSV** to download your current filtered or queried results as a tab-separated file. The exported file includes the SQL query that produced it.

> Exports reflect the active filters at the time of download, not the full table.
