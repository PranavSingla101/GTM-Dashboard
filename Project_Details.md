# GTM RevOps Dashboard - Build Specification

All decisions are final. Build sequentially. No hedging, no open questions.

---

## What This Builds

A local GTM Revenue Operations dashboard with four layers:

1. **Data layer** - Python script generates a SQLite database of realistic GTM pipeline records.
2. **ETL layer** - Python modules load, join, filter, and compute KPI metrics from SQLite.
3. **API layer** - FastAPI endpoint accepts new lead payloads, runs business logic server-side, writes to SQLite.
4. **Dashboard layer** - Streamlit app reads from SQLite, applies sidebar filters, renders KPIs and Plotly charts.

The database is committed to the repository so reviewers do not need to regenerate it.

---

## Business Problem

GTM teams cannot see which pipeline sequences, ICP tiers, personas, and lead sources actually produce closed-won revenue. Without this, reps spend effort on low-converting segments while missing patterns that drive pipeline. This dashboard connects top-of-funnel activity to bottom-of-funnel revenue outcomes across outbound, inbound, referral, and event-sourced leads.

---

## Stack

```text
Python          3.11+
SQLite          built-in (no external service)
Faker           25.x
Pandas          2.x
Streamlit       1.35.x
Plotly          5.x
FastAPI         0.111.x
Uvicorn         0.30.x
Pydantic        2.x
python-dotenv   1.x
```

`requirements.txt` must pin exact versions resolved during install.

---

## Repository Structure

```text
GTM Dashboard/
  Project_Details.md
  README.md
  requirements.txt
  revops_pipeline.db
  app.py                        # Streamlit presentation/orchestration only - no business logic
  config.py                     # Business/data constants: DB path, weights, tier rules
  core/
    __init__.py
    metrics.py                  # compute_kpis and all KPI helpers
    transformations.py          # load, join, filter, and chart-prep functions
  db/
    __init__.py
    connection.py               # get_conn(), execute_query()
    schema.sql                  # DDL for leads and sequences tables
    seed.py                     # generate_mock_data() entry point
  ingestion/
    __init__.py
    live_append.py              # append_live_leads - direct SQLite insert
    api.py                      # FastAPI ingest endpoint
  .streamlit/
    config.toml
  assets/
    dashboard_preview.png
  DOCS/
    architecture.md
    data_dictionary.md
```

---

## Phase 1: Data Layer

### File: `config.py`

Single source of truth for business rules and data-generation constants. No logic - imports only from the standard library.

```python
# Exports (all UPPERCASE module-level names):
DB_PATH: str                  # absolute path to revops_pipeline.db
ICP_TIERS: list[str]
TIER_WEIGHTS: list[float]
PERSONAS: list[str]
SOURCES: list[str]
SOURCE_WEIGHTS: list[float]
INDUSTRIES: list[str]
REGIONS: list[str]
SOURCE_TO_SEQUENCES: dict[str, list[str]]
REPLY_RATE: dict[str, float]
CONV_RATE: dict[str, float]
STATUS_WEIGHTS: dict[str, float]   # {"Closed Won": 0.30, "Closed Lost": 0.50, "Open": 0.20}
DEAL_RANGE: dict[str, tuple[int, int]]
EMPLOYEE_RANGE: dict[str, tuple[int, int]]
REVENUE_RANGE: dict[str, tuple[int, int]]
OUTLIER_PROB: float            # 0.03
OUTLIER_MULTIPLIER_RANGE: tuple[float, float]  # (1.5, 3.0)
LEAD_COUNT: int                # 750
OWNER_POOL_SIZE: int           # 15
SEED: int                      # 42
```

All business rules and data-generation constants must be imported from `config.py`. UI display settings, chart labels, chart colors, and framework-specific layout values may live in `app.py` when they only affect presentation.

---

### SQLite Database

File: `revops_pipeline.db`

### File: `db/schema.sql`

Plain SQL DDL file. Applied by `db/seed.py` on each run (DROP IF EXISTS, then CREATE).

### Full Schema

```sql
CREATE TABLE leads (
    lead_id             TEXT PRIMARY KEY,
    company_name        TEXT NOT NULL,
    icp_tier            TEXT NOT NULL,      -- 'Tier 1', 'Tier 2', 'Tier 3'
    persona             TEXT NOT NULL,
    source              TEXT NOT NULL,
    industry            TEXT NOT NULL,
    employee_count      INTEGER NOT NULL,
    annual_revenue      INTEGER NOT NULL,   -- USD
    region              TEXT NOT NULL,
    owner_name          TEXT NOT NULL,
    created_at          DATE NOT NULL
);

CREATE TABLE sequences (
    sequence_id             TEXT PRIMARY KEY,
    lead_id                 TEXT NOT NULL,
    sequence_name           TEXT NOT NULL,
    step_count              INTEGER NOT NULL,
    replied                 INTEGER NOT NULL,   -- 0 or 1
    converted_to_opp        INTEGER NOT NULL,   -- 0 or 1
    deal_value              INTEGER NOT NULL,   -- 0 if not converted
    status                  TEXT NOT NULL,      -- 'Open', 'Closed Won', 'Closed Lost', 'No Reply', 'Replied - No Opp'
    started_at              DATE NOT NULL,
    last_touch_at           DATE NOT NULL,
    opportunity_created_at  DATE,              -- NULL if not converted
    closed_at               DATE,              -- NULL if status = 'Open', 'No Reply', or 'Replied - No Opp'
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id)
);
```

### Enumerated Field Values

**icp_tier** - distribution:
```
Tier 1: 20%
Tier 2: 30%
Tier 3: 50%
```

**persona** - pick from:
```python
PERSONAS = [
    "VP of Sales",
    "VP of Marketing",
    "Chief Revenue Officer",
    "Chief Financial Officer",
    "Head of Revenue Operations",
    "Director of Sales Operations",
    "CEO",
]
```

**source** - distribution:
```
Outbound:  50%
Inbound:   20%
Referral:  20%
Event:     10%
```

**industry** - pick from:
```python
INDUSTRIES = [
    "SaaS",
    "Fintech",
    "Healthcare Tech",
    "E-commerce",
    "Logistics",
    "Cybersecurity",
    "HR Tech",
]
```

**region** - pick from:
```python
REGIONS = ["North America", "Europe", "APAC", "LATAM", "MENA"]
```

**employee_count** - ranges by ICP tier:
```
Tier 1: randint(500, 5000)
Tier 2: randint(100, 499)
Tier 3: randint(10,  99)
```

**annual_revenue** - ranges by ICP tier (USD):
```
Tier 1: randint(50_000_000,  500_000_000)
Tier 2: randint(10_000_000,  49_000_000)
Tier 3: randint(1_000_000,   9_000_000)
```

**sequence_name** - mapped from source:
```python
SOURCE_TO_SEQUENCES = {
    "Outbound": ["Q2 Outbound Cold", "ABM Campaign"],
    "Inbound":  ["Inbound Follow-up"],
    "Referral": ["Executive Referral", "Partner Sourced"],
    "Event":    ["Event Follow-up"],
}
```
Pick randomly from the list matching the lead's source.

**step_count** - `randint(1, 8)` regardless of tier.

**owner_name** - generate with `Faker().name()`, seeded so reruns produce the same 15 distinct owner names. Use `random.choice(OWNER_POOL)` where `OWNER_POOL` is a list built at startup.

### Weighted Business Logic

**Reply probability by tier:**
```
Tier 1: 40%
Tier 2: 20%
Tier 3:  8%
```

**Conversion-to-opportunity probability (only if replied = True):**
```
Tier 1: 50%
Tier 2: 30%
Tier 3: 15%
```

**Status assignment (only if converted_to_opp = True):**
```
Closed Won:  30%
Closed Lost: 50%
Open:        20%
```

If `replied = False`, status is always `'No Reply'` and `converted_to_opp = 0`.
If `replied = True` and `converted_to_opp = False`, status is always `'Replied - No Opp'`.
If `converted_to_opp = True`, status is assigned from the weights above.

### Deal Value Logic

`deal_value = 0` unless `converted_to_opp = True`.

Deal value ranges by ICP tier (USD):
```
Tier 1: randint(50_000, 180_000)
Tier 2: randint(20_000, 100_000)
Tier 3: randint(5_000,   50_000)
```

Add outliers: with 3% probability per converted record, multiply the base deal value by `uniform(1.5, 3.0)` and round to the nearest 1000.

Closed Lost records retain their original deal value (needed for historical pipeline analysis). Only `status = 'Closed Won'` records count toward revenue metrics.
`Total Opp Pipeline` includes all converted opportunities (`status` in `'Open'`, `'Closed Won'`, `'Closed Lost'`).
`Lost Pipeline` includes only `status = 'Closed Lost'`.

### Date Logic

All dates are derived from `created_at`, which is `today - randint(0, 90)` days (90-day lookback, not 60).

```
started_at             = created_at + timedelta(days=randint(0, 3))
last_touch_at          = started_at + timedelta(days=step_count * randint(2, 4))
opportunity_created_at = last_touch_at + timedelta(days=randint(1, 7))   # only if converted_to_opp
closed_at              = opportunity_created_at + timedelta(days=randint(14, 90))  # only if Closed Won or Closed Lost
```

No date may be in the future. Generate dates so the chronological order is preserved first, then cap only when doing so does not violate the required sequence:

```
created_at <= started_at <= last_touch_at <= opportunity_created_at <= closed_at
```

For converted records, if the full chain would extend beyond `today`, move the later dates back to the latest valid non-future dates while preserving order. Same-day values are allowed only when needed to avoid future dates.

### Volume

Generate **750 lead records** and one sequence record per lead (1:1 relationship).

### Data Quality Checks

Run after generation and print a summary report:

```
Total leads:              750
Total sequences:          750
Orphaned sequences:       0
Leads with no sequence:   0
Null lead_ids:            0
Tier distribution:        Tier 1 ~20%, Tier 2 ~30%, Tier 3 ~50%
Reply rate Tier 1:        ~40%
Reply rate Tier 3:        ~8%
Converted with deal=0:    0
Closed Won with deal=0:   0
Dates in future:          0
```

Any assertion failure must raise an exception and halt.

### File: `db/connection.py`

```python
# Exports:
def get_conn() -> sqlite3.Connection
    # Returns a connection to revops_pipeline.db with row_factory = sqlite3.Row
    # DB_PATH sourced from config.py

def execute_query(sql: str, params: tuple = ()) -> pd.DataFrame
    # Runs a SELECT and returns a DataFrame
```

### File: `db/seed.py`

Entry point: `python db/seed.py`

Steps:
1. Read and execute `db/schema.sql` (DROP IF EXISTS, then CREATE for both tables).
2. Seed `random` and `Faker` with `SEED` from `config.py` for reproducibility.
3. Generate the OWNER_POOL: `OWNER_POOL_SIZE` names from Faker.
4. Generate `LEAD_COUNT` lead dicts using the field specs and constants from `config.py`.
5. For each lead, generate one sequence dict.
6. Bulk-insert leads, then sequences.
7. Run all data quality checks.
8. Print the summary report.

### File: `ingestion/live_append.py`

Standalone script for manually appending new records:

```
python ingestion/live_append.py --count 3
```

Generates `--count` new records using the same weighted logic (via `config.py`) and inserts directly to SQLite via `db/connection.py`. Prints the inserted lead_ids.

---

## Phase 2: ETL Layer

### File: `core/transformations.py`

```python
def load_joined_data() -> pd.DataFrame:
    """
    SELECT all columns from leads LEFT JOIN sequences ON lead_id.
    Returns one row per lead. Converts replied/converted_to_opp to bool.
    Parses date columns to datetime.
    """

def apply_filters(
    df: pd.DataFrame,
    tiers: list[str],
    sources: list[str],
    personas: list[str],
    date_start: date,
    date_end: date,
) -> pd.DataFrame:
    """
    Filters df by icp_tier, source, persona, and created_at range (inclusive).
    Returns filtered copy.
    """

def prepare_funnel_data(df: pd.DataFrame) -> dict:
    """
    Returns:
    {
        "Total Leads":       int,
        "Replied":           int,
        "Opportunity":       int,
        "Closed Won":        int,
    }
    """

def prepare_persona_win_rates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups by persona. Returns DataFrame with columns:
    persona | won | lost | win_rate
    win_rate = won / (won + lost), rounded to 4 decimal places.
    Rows where (won + lost) == 0 are excluded.
    Sorted ascending by win_rate.
    """

def prepare_pipeline_by_tier(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups by icp_tier. Returns DataFrame with columns:
    icp_tier | pipeline_value
    pipeline_value = sum(deal_value where converted_to_opp = True).
    This is total opportunity pipeline (open + won + lost).
    """

def prepare_lost_pipeline_by_tier(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups by icp_tier. Returns DataFrame with columns:
    icp_tier | lost_pipeline_value
    lost_pipeline_value = sum(deal_value where status = 'Closed Lost').
    """

def prepare_revenue_by_source(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups by source. Returns DataFrame with columns:
    source | closed_won_revenue
    closed_won_revenue = sum(deal_value where status = 'Closed Won').
    """

def prepare_reply_rate_by_source(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups by source. Returns DataFrame with columns:
    source | reply_rate
    reply_rate = sum(replied) / count(lead_id), rounded to 4 decimal places.
    """

def prepare_opp_rate_by_tier(df: pd.DataFrame) -> pd.DataFrame:
    """
    Groups by icp_tier. Returns DataFrame with columns:
    icp_tier | opp_conversion_rate
    opp_conversion_rate = sum(converted_to_opp) / count(lead_id), rounded to 4 decimal places.
    """

def prepare_recent_records(df: pd.DataFrame, n: int = 50) -> pd.DataFrame:
    """
    Returns the n most recent rows sorted by created_at descending.
    Columns: created_at, company_name, icp_tier, persona, source,
             replied, converted_to_opp, status, deal_value.
    """
```

### File: `core/metrics.py`

```python
def compute_kpis(df: pd.DataFrame) -> dict:
    """
    Returns:
    {
        "total_leads":          int,
        "total_replies":        int,
        "reply_rate":           float,   # replies / leads, 0.0 if leads == 0
        "total_opps":           int,
        "opp_rate":             float,   # opps / leads, 0.0 if leads == 0
        "closed_won_count":     int,
        "win_rate":             float,   # won / (won + lost), 0.0 if denominator == 0
        "total_pipeline":       int,     # sum deal_value where converted_to_opp (open + won + lost)
        "lost_pipeline":        int,     # sum deal_value where status = 'Closed Lost'
        "closed_won_revenue":   int,     # sum deal_value where status = 'Closed Won'
        "active_sequences":     int,     # count where status = 'Open'
        "avg_deal_size":        float,   # avg deal_value where converted and deal_value > 0, 0.0 if none
    }
    """
```

All metrics must handle an empty DataFrame without raising exceptions. Return 0 or 0.0 for every field when df is empty.

---

## Phase 3: API Layer

### File: `ingestion/api.py`

Run with: `uvicorn ingestion.api:app --port 8000`

#### Pydantic Models

```python
from pydantic import BaseModel, Field

class LeadInput(BaseModel):
    company_name: str
    icp_tier: Literal["Tier 1", "Tier 2", "Tier 3"]
    persona: str
    source: Literal["Outbound", "Inbound", "Referral", "Event"]
    created_at: date
    industry: str | None = None
    employee_count: int | None = Field(default=None, ge=1)
    annual_revenue: int | None = Field(default=None, ge=0)
    region: str | None = None
    owner_name: str | None = None

class IngestRequest(BaseModel):
    records: list[LeadInput] = Field(min_length=1, max_length=10)

class IngestResponse(BaseModel):
    inserted: int
    lead_ids: list[str]
```

#### Endpoint

```
POST /ingest/leads
Content-Type: application/json

Request body: IngestRequest
Response body: IngestResponse
```

The API enriches each record server-side:
- Assigns `lead_id` as `UUID4`.
- Looks up or assigns `industry`, `employee_count`, `annual_revenue`, `region`, `owner_name` using the same distributions defined in Phase 1. These are optional fields in `LeadInput`; if not provided, generate them.
- Applies weighted business logic to assign sequence behavior.
- Assigns `sequence_id` as `UUID4`.
- Writes to SQLite via `db/connection.py`.

#### Health check

```
GET /health
Response: {"status": "ok", "db_row_count": int}
```

---

## Phase 4: Dashboard Layer

### File: `.streamlit/config.toml`

```toml
[theme]
base                    = "dark"
primaryColor            = "#0A84FF"
backgroundColor         = "#000000"
secondaryBackgroundColor = "#1C1C1E"
textColor               = "#FFFFFF"
font                    = "sans serif"
```

### File: `app.py`

Entry point: `streamlit run app.py`

#### Page Config (first Streamlit call)

```python
st.set_page_config(
    page_title="GTM RevOps Dashboard",
    page_icon="bar_chart",
    layout="wide",
    initial_sidebar_state="expanded",
)
```

#### Data Load

Load once with `@st.cache_data(ttl=60)`:

```python
@st.cache_data(ttl=60)
def get_data() -> pd.DataFrame:
    return load_joined_data()
```

#### Sidebar Filters

```python
st.sidebar.title("Filters")

# ICP Tier
all_tiers = ["Tier 1", "Tier 2", "Tier 3"]
selected_tiers = st.sidebar.multiselect("ICP Tier", all_tiers, default=all_tiers)

# Lead Source
all_sources = ["Outbound", "Inbound", "Referral", "Event"]
selected_sources = st.sidebar.multiselect("Lead Source", all_sources, default=all_sources)

# Persona
all_personas = sorted(df["persona"].unique().tolist())
selected_personas = st.sidebar.multiselect("Persona", all_personas, default=all_personas)

# Date Range
min_date = df["created_at"].min().date()
max_date = df["created_at"].max().date()
date_start, date_end = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date,
)

# Refresh button
if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()
```

Apply `apply_filters(df, selected_tiers, selected_sources, selected_personas, date_start, date_end)` immediately after sidebar.

Show `st.sidebar.caption(f"{len(filtered_df)} records matching filters")`.

#### Layout: Row 0 - Header

```python
st.title("GTM RevOps Dashboard")
st.caption("GTM pipeline performance - refreshes every 60s")
```

#### Layout: Row 1 - KPI Metrics

6 columns, equal width.

```python
col1, col2, col3, col4, col5, col6 = st.columns(6)
```

| Column | Metric | Format |
|--------|--------|--------|
| col1 | Total Opp Pipeline | `$1.2M` or `$125K` |
| col2 | Closed-Won Revenue | `$1.2M` or `$125K` |
| col3 | Win Rate | `34.2%` |
| col4 | Reply Rate | `18.5%` |
| col5 | Active Sequences | `142` |
| col6 | Avg Deal Size | `$72K` |

Below KPI row, render:
`st.caption(f"Lost Pipeline: {fmt_currency(kpis['lost_pipeline'])}")`

Currency formatting function:

```python
def fmt_currency(value: float) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:.0f}"
```

Percentage formatting: `f"{value * 100:.1f}%"`

#### Layout: Row 2 - Funnel + Persona Win Rate

Two columns: `col_left, col_right = st.columns([1, 1])`

**Left: GTM Funnel**

Chart type: `go.Funnel`

```python
fig = go.Figure(go.Funnel(
    y=["Total Leads", "Replied", "Opportunity", "Closed Won"],
    x=[funnel["Total Leads"], funnel["Replied"], funnel["Opportunity"], funnel["Closed Won"]],
    textinfo="value+percent initial",
    marker=dict(color=["#0A84FF", "#30A0FF", "#30D158", "#FFD60A"]),
    connector=dict(line=dict(color="#636366", width=1)),
))
fig.update_layout(
    title="GTM Funnel",
    paper_bgcolor="#000000",
    plot_bgcolor="#000000",
    font=dict(color="#FFFFFF"),
    margin=dict(l=20, r=20, t=40, b=20),
)
```

**Right: Win Rate by Persona**

Chart type: `go.Bar` (horizontal)

```python
fig = go.Figure(go.Bar(
    y=persona_df["persona"],
    x=persona_df["win_rate"],
    orientation="h",
    marker=dict(color="#0A84FF"),
    text=[f"{v*100:.1f}%" for v in persona_df["win_rate"]],
    textposition="outside",
))
fig.update_layout(
    title="Win Rate by Persona",
    xaxis=dict(tickformat=".0%", showgrid=False),
    yaxis=dict(showgrid=False),
    paper_bgcolor="#000000",
    plot_bgcolor="#1C1C1E",
    font=dict(color="#FFFFFF"),
    margin=dict(l=20, r=40, t=40, b=20),
)
```

#### Layout: Row 3 - Segment Analysis

Four columns: `c1, c2, c3, c4 = st.columns(4)`

| Column | Chart | Type | Color |
|--------|-------|------|-------|
| c1 | Pipeline by ICP Tier | Vertical Bar | `#0A84FF` |
| c2 | Closed-Won Revenue by Source | Vertical Bar | `#30D158` |
| c3 | Reply Rate by Source | Vertical Bar | `#0A84FF` |
| c4 | Opp Conversion Rate by Tier | Vertical Bar | `#FFD60A` |

All four charts share these layout settings:
```python
paper_bgcolor="#000000"
plot_bgcolor="#1C1C1E"
font=dict(color="#FFFFFF")
showlegend=False
margin=dict(l=10, r=10, t=40, b=20)
xaxis=dict(showgrid=False)
yaxis=dict(showgrid=True, gridcolor="#2C2C2E")
```

Pipeline and Revenue charts: format y-axis as currency (`tickprefix="$"`, `tickformat=".2s"`).
Rate charts: format y-axis as percentage (`tickformat=".0%"`).

#### Layout: Row 4 - Recent Records Table

```python
st.subheader("Recent Pipeline")
recent = prepare_recent_records(filtered_df, n=50)
st.dataframe(
    recent,
    use_container_width=True,
    hide_index=True,
    column_config={
        "deal_value": st.column_config.NumberColumn("Deal Value", format="$%d"),
        "created_at": st.column_config.DateColumn("Created"),
        "replied": st.column_config.CheckboxColumn("Replied"),
        "converted_to_opp": st.column_config.CheckboxColumn("Converted"),
    }
)
```

#### Empty State Handling

If `filtered_df` is empty after applying filters, show `st.warning("No records match the selected filters.")` and return early - do not render any charts.

---

## Phase 5: README

### File: `README.md`

Required sections in order:

```
# GTM RevOps Pipeline Dashboard
## Overview
## Business Problem
## Dashboard Preview         <- embed assets/dashboard_preview.png
## Architecture
## Data Model
## Metrics Reference         <- define every KPI with its formula
## Tech Stack
## Getting Started
## Running the Dashboard
## Running the Live Ingestion
## Trade-Offs
## Future Improvements
```

**Trade-Offs section must include:**

> SQLite is used instead of Postgres because the project runs entirely locally with no external services. The data generator replaces a CRM API integration because Salesforce/HubSpot API rate limits and OAuth setup would add days of work without changing the analytical value demonstrated.

**Future Improvements section must include:**
- Replace mock generator with Salesforce, HubSpot, or Apollo API ingestion.
- Add dbt-style transformation layer for complex SQL models.
- Add cohort analysis by lead creation week.
- Add sales cycle duration metric (opportunity_created_at to closed_at).
- Add revenue forecasting from open pipeline with a simple close-rate multiplier.
- Deploy to Streamlit Community Cloud with a Postgres backend.
- Add token-based authentication to the ingest endpoint.

---

## Phase 6: Documentation

### File: `DOCS/data_dictionary.md`

Document every column in both tables: name, type, allowed values, derivation rule.

### File: `DOCS/architecture.md`

Describe the four layers (data, ETL, API, dashboard), how data flows between them, and which files own which responsibility. Call out the role of `config.py` as the single constant source, `db/` as the only SQLite-touching package, `core/` as pure logic with no I/O, `ingestion/` as the write path, and `app.py` as a thin Streamlit entrypoint.

---

## Implementation Order

Build strictly in this order. Do not start a step before the previous one passes its verification.

1. `requirements.txt` - install and pin.
2. `config.py` - all constants.
3. `db/schema.sql` - DDL only, no Python.
4. `db/connection.py` - connection helper.
5. `db/seed.py` - generate and validate `revops_pipeline.db`.
6. `core/transformations.py` - all transform functions.
7. `core/metrics.py` - `compute_kpis`.
8. `app.py` - Streamlit shell with page config and sidebar only (no charts yet).
9. Add KPI row to `app.py`.
10. Add funnel chart.
11. Add persona win-rate chart.
12. Add Row 3 segment charts.
13. Add Row 4 recent records table.
14. Add `.streamlit/config.toml`.
15. `ingestion/api.py` - FastAPI endpoint.
16. `ingestion/live_append.py` - direct append script.
17. `README.md`.
18. `DOCS/data_dictionary.md` and `DOCS/architecture.md`.
19. Take screenshot -> `assets/dashboard_preview.png`.
20. Run full verification checklist.

---

## Verification Checklist

### Data

- [x] `revops_pipeline.db` created.
- [x] `leads` has 750 rows.
- [x] `sequences` has 750 rows.
- [x] Every sequence.lead_id exists in leads.
- [x] No null lead_ids or sequence_ids.
- [x] Tier 1 reply rate is materially higher than Tier 3 reply rate.
- [x] `deal_value = 0` for all non-converted records.
- [x] `deal_value > 0` for all Closed Won records.
- [x] No dates in the future.
- [x] `opportunity_created_at` is NULL for non-converted records.
- [x] `closed_at` is NULL for Open, No Reply, and Replied - No Opp records.

### ETL

- [x] `compute_kpis` returns correct types for all keys.
- [x] Empty DataFrame returns all zeros - no exception.
- [x] Win rate returns 0.0 when no Closed Won or Closed Lost records exist.
- [x] `apply_filters` with all defaults returns the full dataset.

### API

- [x] `POST /ingest/leads` with valid payload returns 200 and `inserted > 0`.
- [x] `GET /health` returns 200.
- [x] Inserting via API increments SQLite row count.
- [x] Invalid `icp_tier` value returns 422 with Pydantic validation error.

### Dashboard

- [x] `streamlit run app.py` starts with no errors.
- [x] All 6 KPIs render with correct formatting.
- [x] Filtering to Tier 1 only changes all metrics and charts.
- [x] Empty filter state shows warning, no crash.
- [x] Funnel chart renders all four stages.
- [x] Recent records table shows correct columns.
- [x] Dark theme is applied (background is not white).


