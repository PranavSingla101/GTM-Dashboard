import random
import uuid
from datetime import date, timedelta
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from config import (
    CONV_RATE,
    EMPLOYEE_RANGE,
    ICP_TIERS,
    INDUSTRIES,
    OUTLIER_MULTIPLIER_RANGE,
    OUTLIER_PROB,
    OWNER_POOL_SIZE,
    PERSONAS,
    REGIONS,
    REPLY_RATE,
    REVENUE_RANGE,
    SEED,
    SOURCE_TO_SEQUENCES,
    SOURCES,
    SOURCE_WEIGHTS,
    STATUS_WEIGHTS,
    TIER_WEIGHTS,
)
from db.connection import get_conn

app = FastAPI(title="GTM RevOps Ingestion API")


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


random.seed(SEED + 202)
_OWNER_POOL = [f"Owner {i+1}" for i in range(OWNER_POOL_SIZE)]


def _status(replied: bool, converted: bool) -> str:
    if not replied:
        return "No Reply"
    if not converted:
        return "Replied - No Opp"
    return random.choices(list(STATUS_WEIGHTS), weights=list(STATUS_WEIGHTS.values()), k=1)[0]


def _deal_value(tier: str, converted: bool) -> int:
    from config import DEAL_RANGE

    if not converted:
        return 0
    value = random.randint(*DEAL_RANGE[tier])
    if random.random() < OUTLIER_PROB:
        value = int(round((value * random.uniform(*OUTLIER_MULTIPLIER_RANGE)) / 1000) * 1000)
    return value


@app.get("/health")
def health() -> dict:
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    return {"status": "ok", "db_row_count": int(count)}


@app.post("/ingest/leads", response_model=IngestResponse)
def ingest_leads(payload: IngestRequest) -> IngestResponse:
    lead_ids: list[str] = []
    with get_conn() as conn:
        for rec in payload.records:
            tier = rec.icp_tier
            source = rec.source
            lead_id = str(uuid.uuid4())
            seq_id = str(uuid.uuid4())
            step_count = random.randint(1, 8)
            replied = random.random() < REPLY_RATE[tier]
            converted = replied and random.random() < CONV_RATE[tier]
            status = _status(replied, converted)

            started = min(date.today(), rec.created_at + timedelta(days=random.randint(0, 3)))
            last_touch = min(date.today(), started + timedelta(days=step_count * random.randint(2, 4)))
            opp_at = None
            closed_at = None
            if converted:
                opp_at = min(date.today(), last_touch + timedelta(days=random.randint(1, 7)))
                if status in {"Closed Won", "Closed Lost"}:
                    closed_at = min(date.today(), opp_at + timedelta(days=random.randint(14, 90)))

            conn.execute(
                """
                INSERT INTO leads (
                    lead_id, company_name, icp_tier, persona, source, industry,
                    employee_count, annual_revenue, region, owner_name, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lead_id,
                    rec.company_name,
                    tier,
                    rec.persona if rec.persona in PERSONAS else random.choice(PERSONAS),
                    source,
                    rec.industry or random.choice(INDUSTRIES),
                    rec.employee_count or random.randint(*EMPLOYEE_RANGE[tier]),
                    rec.annual_revenue or random.randint(*REVENUE_RANGE[tier]),
                    rec.region or random.choice(REGIONS),
                    rec.owner_name or random.choice(_OWNER_POOL),
                    rec.created_at.isoformat(),
                ),
            )
            conn.execute(
                """
                INSERT INTO sequences (
                    sequence_id, lead_id, sequence_name, step_count, replied,
                    converted_to_opp, deal_value, status, started_at, last_touch_at,
                    opportunity_created_at, closed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    seq_id,
                    lead_id,
                    random.choice(SOURCE_TO_SEQUENCES[source]),
                    step_count,
                    int(replied),
                    int(converted),
                    _deal_value(tier, converted),
                    status,
                    started.isoformat(),
                    last_touch.isoformat(),
                    opp_at.isoformat() if opp_at else None,
                    closed_at.isoformat() if closed_at else None,
                ),
            )
            lead_ids.append(lead_id)

    return IngestResponse(inserted=len(lead_ids), lead_ids=lead_ids)
