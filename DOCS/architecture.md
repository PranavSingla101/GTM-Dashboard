# Architecture

## System Layers

### 1) Data Layer
- Ownership: `config.py`, `db/schema.sql`, `db/seed.py`, `revops_pipeline.db`.
- Responsibility:
  - `config.py` is the single source of constants for distributions, business rates, and ranges.
  - `db/schema.sql` defines DDL for `leads` and `sequences`.
  - `db/seed.py` recreates schema, generates deterministic mock records, inserts them, and runs quality assertions.

### 2) ETL Layer
- Ownership: `core/transformations.py`, `core/metrics.py`.
- Responsibility:
  - Load/join data from SQLite.
  - Apply reusable filtering logic.
  - Compute chart-ready slices and KPI dictionaries.
  - Keep business calculations pure (no file/network I/O).

### 3) API Layer
- Ownership: `ingestion/api.py`, `ingestion/live_append.py`.
- Responsibility:
  - Write path into SQLite for new leads.
  - Server-side enrichment of optional lead attributes.
  - Sequence behavior generation from the same weighted business logic used by seed.
  - Health endpoint exposing basic DB row count.

### 4) Dashboard Layer
- Ownership: `app.py`, `.streamlit/config.toml`.
- Responsibility:
  - Thin Streamlit entrypoint and presentation orchestration.
  - Sidebar filtering, KPI display, charts, and recent-record table.
  - No low-level DB write logic in UI layer.

## Data Flow
1. `db/seed.py` generates and inserts baseline `leads` and `sequences` into SQLite.
2. `app.py` calls ETL functions in `core/` to load and transform records.
3. KPI/chart outputs render in Streamlit with sidebar filters.
4. New records arrive through `POST /ingest/leads` or `ingestion/live_append.py`.
5. Subsequent dashboard refreshes include newly appended rows.

## Package Responsibility Boundaries
- `config.py`: constants only.
- `db/`: only package that directly manages SQLite connection and schema reset/seed.
- `core/`: pure logic and metric/transform computation.
- `ingestion/`: all write-path operations (API + script append).
- `app.py`: dashboard presentation and interaction shell.
