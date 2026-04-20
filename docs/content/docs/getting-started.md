---
title: "Getting Started"
linkTitle: "Getting Started"
weight: 20
description: "Install dependencies and launch SQLite Browser for the first time."
---

## Prerequisites

- **Python 3.13 or higher**
- **[uv](https://docs.astral.sh/uv/)** — a fast, Rust-based Python package manager

## Install uv

If you do not already have `uv`, follow the [uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) for your platform.

## Install dependencies

From the root of the repository, run:

```bash
uv sync
```

This reads `pyproject.toml` and installs all required packages into an isolated virtual environment.

> **Windows + OneDrive:** If the repository is inside a OneDrive-synced folder you may see a hardlink error (`os error 396`). The project is pre-configured with `link-mode = "copy"` in `pyproject.toml` to prevent this — `uv sync` should succeed without any extra steps.

## Start the app

```bash
uv run python dash_app.py
```

Open your browser and navigate to:

```
http://127.0.0.1:8050
```

The app is only accessible on your own machine (it does not listen on the network).

## Next step

Once the app is running, see [Usage]({{< relref "usage" >}}) to load a database and start exploring.
