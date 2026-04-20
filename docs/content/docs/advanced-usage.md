---
title: "Advanced Usage"
linkTitle: "Advanced Usage"
weight: 40
description: "Filter operators, worked examples, and custom SQL query patterns."
---

## Advanced Search operators

The filter builder supports 11 operators covering the most common query patterns.

| Operator | SQL equivalent | Best for |
|---|---|---|
| **equals** | `col = "value"` | Exact match on a known value |
| **does not equal** | `col != "value"` | Excluding a specific value |
| **like (contains)** | `col LIKE "%value%"` | Substring / partial-string search |
| **not like** | `col NOT LIKE "%value%"` | Excluding a pattern |
| **less than** | `col < value` | Strict upper bound |
| **less than or equal** | `col <= value` | Inclusive upper bound |
| **greater than** | `col > value` | Strict lower bound |
| **greater than or equal** | `col >= value` | Inclusive lower bound |
| **in** | `col IN (v1, v2, v3)` | Matching any of several values |
| **is null** | `col IS NULL` | Finding missing / empty values |
| **is not null** | `col IS NOT NULL` | Excluding missing values |

All conditions added with **+ Add Filter** are combined with `AND`.

## Filter examples

### Substring match

Find all rows where `ent__sub` contains `"MOA"`:

```
Field:    ent__sub
Operator: like (contains)
Value:    MOA
```

### Multiple conditions

Participants over 30 with an active status:

```
Filter 1 — Field: age       Operator: greater than   Value: 30
Filter 2 — Field: status    Operator: equals         Value: active
```

### Checking for missing data

Find rows where `optional_field` has no value:

```
Field:    optional_field
Operator: is null
(no value needed)
```

### Matching a set of values

Rows where `site` is one of several known values:

```
Field:    site
Operator: in
Value:    siteA, siteB, siteC
```

## Custom SQL examples

The **Execute Custom Query** panel accepts any valid SQLite SQL.

### Basic select with limit

```sql
SELECT * FROM "participants" LIMIT 100;
```

### Column subset with filter

```sql
SELECT subject_id, age, diagnosis
FROM "participants"
WHERE age > 30
LIMIT 1000;
```

### Aggregation

```sql
SELECT condition, COUNT(*) AS count
FROM "data"
GROUP BY condition
ORDER BY count DESC;
```

### Join across tables

```sql
SELECT p.subject_id, s.score
FROM "participants" p
JOIN "scores" s ON p.subject_id = s.subject_id
WHERE p.age >= 18;
```

## Query limits

By default, the results table displays a maximum of **500 rows** to prevent memory issues with large databases. To retrieve more rows use a custom SQL query with an explicit `LIMIT`:

```sql
SELECT * FROM "large_table" LIMIT 5000;
```

The TSV export reflects whatever rows are currently loaded — raise the limit in SQL before exporting if you need the full result set.
