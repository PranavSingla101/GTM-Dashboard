DROP TABLE IF EXISTS sequences;
DROP TABLE IF EXISTS leads;

CREATE TABLE leads (
    lead_id             TEXT PRIMARY KEY,
    company_name        TEXT NOT NULL,
    icp_tier            TEXT NOT NULL,
    persona             TEXT NOT NULL,
    source              TEXT NOT NULL,
    industry            TEXT NOT NULL,
    employee_count      INTEGER NOT NULL,
    annual_revenue      INTEGER NOT NULL,
    region              TEXT NOT NULL,
    owner_name          TEXT NOT NULL,
    created_at          DATE NOT NULL
);

CREATE TABLE sequences (
    sequence_id             TEXT PRIMARY KEY,
    lead_id                 TEXT NOT NULL,
    sequence_name           TEXT NOT NULL,
    step_count              INTEGER NOT NULL,
    replied                 INTEGER NOT NULL,
    converted_to_opp        INTEGER NOT NULL,
    deal_value              INTEGER NOT NULL,
    status                  TEXT NOT NULL,
    started_at              DATE NOT NULL,
    last_touch_at           DATE NOT NULL,
    opportunity_created_at  DATE,
    closed_at               DATE,
    FOREIGN KEY (lead_id) REFERENCES leads(lead_id)
);
