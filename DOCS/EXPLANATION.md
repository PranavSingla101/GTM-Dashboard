# Project Explanation — In Plain English

This document explains what the GTM RevOps Dashboard actually is, what every piece of the tech stack does, and why each tool was chosen. No jargon assumed.

---

## What Is This Project, Really?

Imagine you run a sales team. Leads come in from outbound campaigns, inbound interest, referrals, and events. Some people reply, some become real sales opportunities, some eventually buy. Most don't.

The problem: you have no dashboard that tells you *which type of company*, *which job title*, or *which lead source or sequence* is actually turning into money. You're flying blind.

This project builds that dashboard. It:
1. Creates a fake but realistic database of 750 sales leads and their outcomes.
2. Provides API and command-line ingestion paths for adding new leads.
3. Shows all of this in an interactive dashboard you can filter and slice.

The entire thing runs on your laptop. No cloud, no paid services, no APIs to set up.

---

## The Four Layers — What Each One Does

Think of it like an assembly line:

```
[Raw Data] → [Clean & Calculate] → [Store Incoming Data] → [Display]
   Data            ETL                    API               Dashboard
```

### Layer 1: Data (the "factory floor")

**What it does:** A Python script generates 750 fake company records and their sales outcomes and saves them into a database file.

**Why fake data?** Because connecting to a real CRM (Salesforce, HubSpot) requires OAuth authentication, API rate limits, paid accounts, and weeks of setup. Fake data lets us demonstrate the exact same analytical skills without any of that. The data is designed with real business rules so the patterns it produces are meaningful.

**Key files:**
- `db/seed.py` — the script that creates everything
- `db/connection.py` — a helper that knows how to open and query the database
- `ingestion/live_append.py` — a script to manually add new leads
- `revops_pipeline.db` — the actual database file (saved and committed)

---

### Layer 2: ETL (the "analyst's workbench")

ETL stands for **Extract, Transform, Load**. In plain English: take raw data out of the database, clean it up, and calculate the numbers the dashboard needs.

**What it does:**
- Joins the two database tables together (leads + sequences) into one flat table.
- Applies whatever filters the user selected (e.g. "show me only Tier 1, Outbound, last 30 days").
- Calculates all KPI numbers (reply rate, win rate, total pipeline, etc.).
- Prepares the shaped data that each chart needs.

**Why a separate layer?** If all this logic lived inside the dashboard file (`app.py`), it would become a mess of 600 lines that mixes display code with math. Keeping it separate means you can change a metric formula without touching the chart code.

**Key files:**
- `core/transformations.py` — filter logic, data joins, chart data prep functions
- `core/metrics.py` — all KPI calculations (reply rate, win rate, pipeline totals, etc.)

---

### Layer 3: API (the "intake window")

**What it does:** A small web server that listens for incoming lead data. When a client sends a new batch of leads, they land here first. The API validates them, runs all the business logic (what tier? did they reply? what's the deal value?), and writes the final record to the database.

**Why an API and not just writing directly to the database?** Two reasons:
1. It separates concerns — external tools don't need to know about database paths, business logic, or Python. They just send a simple JSON message.
2. It demonstrates a real-world pattern. In production systems, data almost always enters through an API endpoint, not a direct database write.

**Key file:**
- `ingestion/api.py` — the FastAPI server with two endpoints: `POST /ingest/leads` and `GET /health`

---

### Layer 4: Dashboard (the "display screen")

**What it does:** A web app that opens in your browser, reads from the database, lets you filter by tier/source/persona/date, and shows charts and KPIs.

**Key file:**
- `app.py` — the entire dashboard

**What you see:**
- **Row 1:** 6 big numbers at the top (Total Pipeline, Revenue, Win Rate, Reply Rate, Active Sequences, Avg Deal Size)
- **Row 2:** A funnel chart showing drop-off from lead → reply → opportunity → closed won. A bar chart showing which job title (persona) wins most often.
- **Row 3:** Four smaller charts — pipeline by tier, revenue by lead source, reply rate by source, opp conversion rate by tier.
- **Row 4:** A scrollable table of the 50 most recent leads.

---

## The Tech Stack — Every Tool Explained

### Python
**What:** The main programming language for the generator, ETL, API, and dashboard.
**Why:** Python is the standard for data work. Pandas, Streamlit, Faker, and FastAPI are all Python libraries. Nothing else would let you build all four layers this quickly.

---

### SQLite
**What:** A database that lives in a single file (`revops_pipeline.db`) on your hard drive. No server, no install, no config.
**Why:** This project needs a real relational database (so you can JOIN tables, run aggregations, enforce foreign keys) but doesn't need the complexity of PostgreSQL or MySQL. SQLite is built into Python — you don't install anything.
**Where it appears:** `db/connection.py` opens the connection. Read and write paths use this helper when they touch SQLite.

---

### Faker
**What:** A Python library that generates realistic fake data — company names, person names, addresses, etc.
**Why:** Without Faker, you'd have to hand-write 750 rows of test data. Faker generates `Acme Corp`, `Greenfield Systems`, `Horizon Analytics` — names that look real in screenshots and demos.
**Where it appears:** In `db/seed.py` and ingestion helpers. It generates company names and owner names.

---

### Pandas
**What:** A Python library for working with tabular data — think of it as Excel, but in code. You load data into a "DataFrame" (a table), then filter rows, group by columns, compute averages, etc.
**Why:** The ETL layer needs to join the leads and sequences tables, apply multiple filters at once, and compute grouped aggregations (e.g. reply rate per source). Pandas does all of this in a few lines. Without it, you'd be writing raw SQL for every calculation.
**Where it appears:** `core/transformations.py` and `core/metrics.py` are Pandas-based. `app.py` receives DataFrames from these modules.

---

### Streamlit
**What:** A Python library that turns a Python script into a web app. You write `st.title("Hello")` and it renders a webpage with that title. No HTML, no JavaScript, no CSS required.
**Why:** Building a dashboard from scratch in React or Vue would take weeks. Streamlit produces a working, interactive web app from plain Python in hours. It handles the sidebar filters, the layout columns, the data tables, and the chart rendering containers automatically.
**Where it appears:** `app.py` is entirely Streamlit. `.streamlit/config.toml` sets the dark theme.

---

### Plotly
**What:** A Python charting library that creates interactive charts — hover effects, zoom, tooltips. The charts render in the browser.
**Why:** Streamlit has its own basic charts, but they don't support the funnel chart shape, custom colors, or dark-mode styling. Plotly gives precise control over every visual element. It integrates cleanly with Streamlit using `st.plotly_chart()`.
**Where it appears:** `app.py` — all chart construction uses `plotly.graph_objects` (`go.Funnel`, `go.Bar`).

---

### FastAPI
**What:** A Python library for building web APIs. You define an endpoint (a URL), describe what data it accepts, and FastAPI handles validation, error messages, and the HTTP layer.
**Why:** External tools or manual clients need somewhere to send data. FastAPI creates that `POST /ingest/leads` endpoint. It also handles bad input automatically — if a client sends an invalid ICP tier, FastAPI returns a clear error without any custom error-handling code needed.
**Where it appears:** `ingestion/api.py`.

---

### Uvicorn
**What:** The web server that runs the FastAPI application. FastAPI defines the routes; Uvicorn is the engine that actually listens on a port and handles HTTP connections.
**Why:** FastAPI requires a server to run. Uvicorn is the standard, lightweight choice. You run it with `uvicorn ingestion.api:app --port 8000`.
**Where it appears:** Not in any file directly — it's a run command. It's listed in `requirements.txt` because FastAPI depends on it.

---

### Pydantic
**What:** A Python library for data validation. You define a "model" (a class that describes the shape of data), and Pydantic automatically checks that incoming data matches that shape.
**Why:** When a client sends a payload to the API, Pydantic ensures `icp_tier` is one of the three allowed values, `created_at` is a valid date, and `company_name` is not empty — before any of your code runs. Without Pydantic you'd write 20 lines of manual `if` checks for every field.
**Where it appears:** `ingestion/api.py` — the `LeadInput`, `IngestRequest`, and `IngestResponse` classes.

---

### python-dotenv
**What:** Loads environment variables from a `.env` file into your Python environment.
**Why:** If you ever add a secret (API key, database URL, etc.), you don't want to hardcode it in a Python file that gets committed to git. python-dotenv lets you put it in `.env` and load it safely.
**Where it appears:** `ingestion/api.py` — called once at startup with `load_dotenv()`. Not actively used in the base build but useful before any secret is needed.

---

## The Two Database Tables

The entire project revolves around two tables that are linked together.

### `leads` table
One row per company that was contacted. Stores who they are.

| Column | What it means |
|--------|---------------|
| `lead_id` | Unique ID (UUID) |
| `company_name` | Fake company name from Faker |
| `icp_tier` | How good a fit this company is: Tier 1 = best, Tier 3 = weakest |
| `persona` | The job title of the person contacted (e.g. VP of Sales) |
| `source` | How they entered the pipeline: Outbound, Inbound, Referral, or Event |
| `industry` | SaaS, Fintech, Healthcare Tech, etc. |
| `employee_count` | Company size — bigger companies are in higher tiers |
| `annual_revenue` | Company revenue — higher in better tiers |
| `region` | North America, Europe, APAC, LATAM, MENA |
| `owner_name` | Which sales rep owns this lead |
| `created_at` | When the lead was created (within the last 90 days) |

### `sequences` table
One row per lead (1:1 relationship). Stores what happened after outreach.

| Column | What it means |
|--------|---------------|
| `sequence_id` | Unique ID (UUID) |
| `lead_id` | Links back to the leads table |
| `sequence_name` | Name of the email campaign (e.g. "Q2 Outbound Cold") |
| `step_count` | How many emails were sent (1–8) |
| `replied` | Did they reply? 1 = yes, 0 = no |
| `converted_to_opp` | Did the reply lead to a sales opportunity? 1 = yes |
| `deal_value` | Dollar value of the opportunity (0 if no opportunity) |
| `status` | Current state: Open, Closed Won, Closed Lost, or No Reply |
| `started_at` | When the sequence started |
| `last_touch_at` | When the last email was sent |
| `opportunity_created_at` | When the opp was formally created (NULL if no opp) |
| `closed_at` | When the deal was won or lost (NULL if still open) |

---

## The Business Logic Behind the Fake Data

The data isn't random. It's weighted to reflect real sales patterns:

**ICP Tier = how well a company fits your ideal customer profile**
- Tier 1 companies (best fit) are 20% of leads but reply 40% of the time and convert 50% of replies to opportunities.
- Tier 3 companies (weakest fit) are 50% of leads but only reply 8% of the time and convert just 15% of replies.
- This is intentional: it makes the dashboard show a clear story — chasing bad-fit accounts is inefficient.

**Deal values are also tiered**
- Tier 1: $50K–$180K (large enterprise contracts)
- Tier 2: $20K–$100K (mid-market)
- Tier 3: $5K–$50K (smaller companies)

**Status flow (what happens to a converted opportunity)**
- 30% become Closed Won (revenue)
- 50% become Closed Lost (didn't buy)
- 20% stay Open (still in negotiation)

**Dates are chained logically**
- A sequence can only start *after* the lead was created.
- An opportunity can only be created *after* the last email touch.
- A deal can only close *after* the opportunity was created.
- No date is allowed to be in the future.

---

## How Data Flows Through the System

```
db/seed.py
        │
        ▼
revops_pipeline.db  ◄──── ingestion/api.py
        │
        ▼
core/transformations.py + core/metrics.py
        │
        ▼
app.py (Streamlit Dashboard)
        │
        ▼
Browser (you see charts and KPIs)
```

1. The database is seeded once with 750 records.
2. New leads can be added through the FastAPI endpoint or the `ingestion/live_append.py` script.
3. The API validates payloads, runs business logic, and writes to SQLite.
4. The Streamlit dashboard reads from SQLite (cached for 60 seconds).
5. When you hit "Refresh Data" in the sidebar, it clears the cache and re-reads.

---

## The KPIs — What Each Number Means

| KPI | Formula | What it tells you |
|-----|---------|-------------------|
| Total Pipeline | Sum of all deal values where converted to opportunity | How much potential revenue is in the funnel |
| Closed-Won Revenue | Sum of deal values where status = Closed Won | How much has actually been booked |
| Win Rate | Closed Won ÷ (Closed Won + Closed Lost) | What percentage of finished deals you win |
| Reply Rate | Total replies ÷ Total leads | How often outreach gets a response |
| Active Sequences | Count of leads with status = Open | How many deals are currently in motion |
| Avg Deal Size | Average deal value across converted opportunities | The typical contract value |

All KPIs update instantly when you change sidebar filters. If no records match the filter, the dashboard shows a warning instead of crashing with a divide-by-zero error.

---

## What Each File Actually Does (Quick Reference)

| File | Plain-English job |
|------|-------------------|
| `db/seed.py` | Creates the fake database from scratch |
| `db/connection.py` | Opens the database and runs queries |
| `ingestion/live_append.py` | Manually adds new leads |
| `core/transformations.py` | Joins tables, applies filters, shapes data for charts |
| `core/metrics.py` | Computes all 11 KPI numbers |
| `ingestion/api.py` | Receives new leads via HTTP, validates them, saves to DB |
| `app.py` | The entire dashboard — layout, filters, charts, table |
| `.streamlit/config.toml` | Makes the dashboard dark (background black, accent blue) |
| `requirements.txt` | List of all Python packages needed to run the project |
| `revops_pipeline.db` | The database file (committed so you don't have to regenerate) |

---

## Why Not Just Use Excel or Google Sheets?

Excel/Sheets can't:
- Run an API that receives live data
- Apply programmatic business logic to generated records
- Render interactive filterable charts that update in real-time
- Be version-controlled and reproduced from a single command

This project demonstrates skills that matter for data engineering, analytics engineering, and RevOps tooling roles — not just spreadsheet work.

---

## Why Not Use a Real CRM?

Connecting to Salesforce or HubSpot requires:
- A paid account or developer sandbox
- OAuth 2.0 authentication setup
- API rate limit handling
- Weeks of data to accumulate naturally

The mock generator produces the same analytical value — the patterns, the chart shapes, the KPI logic — without any external dependency. The trade-off is documented clearly in the README so reviewers understand it was a deliberate choice, not an omission.
