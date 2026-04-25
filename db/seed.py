import random
import sqlite3
import sys
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from faker import Faker

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config import (
    CONV_RATE,
    DB_PATH,
    DEAL_RANGE,
    EMPLOYEE_RANGE,
    ICP_TIERS,
    INDUSTRIES,
    LEAD_COUNT,
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


def _generate_status(replied: bool, converted: bool) -> str:
    if not replied:
        return "No Reply"
    if not converted:
        return "Replied - No Opp"
    choices = list(STATUS_WEIGHTS.keys())
    weights = list(STATUS_WEIGHTS.values())
    return random.choices(choices, weights=weights, k=1)[0]


def _calc_deal_value(tier: str, converted: bool) -> int:
    if not converted:
        return 0
    low, high = DEAL_RANGE[tier]
    value = random.randint(low, high)
    if random.random() < OUTLIER_PROB:
        value = int(round((value * random.uniform(*OUTLIER_MULTIPLIER_RANGE)) / 1000) * 1000)
    return value


def _generate_dates(step_count: int, converted: bool, status: str) -> dict[str, str | None]:
    today = date.today()
    created_at = today - timedelta(days=random.randint(0, 90))
    started_at = created_at + timedelta(days=random.randint(0, 3))
    last_touch_at = started_at + timedelta(days=step_count * random.randint(2, 4))

    opp_at = None
    closed_at = None
    if converted:
        opp_at = last_touch_at + timedelta(days=random.randint(1, 7))
        if status in {"Closed Won", "Closed Lost"}:
            closed_at = opp_at + timedelta(days=random.randint(14, 90))

    if closed_at and closed_at > today:
        closed_at = today
    if opp_at and opp_at > today:
        opp_at = today
    if last_touch_at > today:
        last_touch_at = today
    if started_at > last_touch_at:
        started_at = last_touch_at
    if created_at > started_at:
        created_at = started_at
    if opp_at is not None and opp_at < last_touch_at:
        opp_at = last_touch_at
    if closed_at is not None and opp_at is not None and closed_at < opp_at:
        closed_at = opp_at

    return {
        "created_at": created_at.isoformat(),
        "started_at": started_at.isoformat(),
        "last_touch_at": last_touch_at.isoformat(),
        "opportunity_created_at": opp_at.isoformat() if opp_at else None,
        "closed_at": closed_at.isoformat() if closed_at else None,
    }


def _generate_lead(fake: Faker, owners: list[str]) -> dict:
    tier = random.choices(ICP_TIERS, weights=TIER_WEIGHTS, k=1)[0]
    source = random.choices(SOURCES, weights=SOURCE_WEIGHTS, k=1)[0]
    employee_count = random.randint(*EMPLOYEE_RANGE[tier])
    annual_revenue = random.randint(*REVENUE_RANGE[tier])
    created_at = (date.today() - timedelta(days=random.randint(0, 90))).isoformat()
    return {
        "lead_id": str(uuid.uuid4()),
        "company_name": fake.company(),
        "icp_tier": tier,
        "persona": random.choice(PERSONAS),
        "source": source,
        "industry": random.choice(INDUSTRIES),
        "employee_count": employee_count,
        "annual_revenue": annual_revenue,
        "region": random.choice(REGIONS),
        "owner_name": random.choice(owners),
        "created_at": created_at,
    }


def _generate_sequence(lead: dict) -> dict:
    tier = lead["icp_tier"]
    replied = random.random() < REPLY_RATE[tier]
    converted = replied and random.random() < CONV_RATE[tier]
    status = _generate_status(replied, converted)
    step_count = random.randint(1, 8)
    dates = _generate_dates(step_count=step_count, converted=converted, status=status)

    return {
        "sequence_id": str(uuid.uuid4()),
        "lead_id": lead["lead_id"],
        "sequence_name": random.choice(SOURCE_TO_SEQUENCES[lead["source"]]),
        "step_count": step_count,
        "replied": int(replied),
        "converted_to_opp": int(converted),
        "deal_value": _calc_deal_value(tier, converted),
        "status": status,
        "started_at": dates["started_at"],
        "last_touch_at": dates["last_touch_at"],
        "opportunity_created_at": dates["opportunity_created_at"],
        "closed_at": dates["closed_at"],
    }


def _quality_checks(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    total_leads = cur.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    total_sequences = cur.execute("SELECT COUNT(*) FROM sequences").fetchone()[0]
    orphaned = cur.execute(
        "SELECT COUNT(*) FROM sequences s LEFT JOIN leads l ON s.lead_id = l.lead_id WHERE l.lead_id IS NULL"
    ).fetchone()[0]
    no_sequence = cur.execute(
        "SELECT COUNT(*) FROM leads l LEFT JOIN sequences s ON l.lead_id = s.lead_id WHERE s.sequence_id IS NULL"
    ).fetchone()[0]
    null_lead_ids = cur.execute("SELECT COUNT(*) FROM leads WHERE lead_id IS NULL").fetchone()[0]
    conv_deal_zero = cur.execute(
        "SELECT COUNT(*) FROM sequences WHERE converted_to_opp = 1 AND deal_value = 0"
    ).fetchone()[0]
    won_deal_zero = cur.execute(
        "SELECT COUNT(*) FROM sequences WHERE status = 'Closed Won' AND deal_value = 0"
    ).fetchone()[0]
    future_dates = cur.execute(
        """
        SELECT COUNT(*) FROM sequences
        WHERE date(started_at) > date('now')
           OR date(last_touch_at) > date('now')
           OR (opportunity_created_at IS NOT NULL AND date(opportunity_created_at) > date('now'))
           OR (closed_at IS NOT NULL AND date(closed_at) > date('now'))
        """
    ).fetchone()[0]
    null_opp_for_non_converted = cur.execute(
        "SELECT COUNT(*) FROM sequences WHERE converted_to_opp = 0 AND opportunity_created_at IS NOT NULL"
    ).fetchone()[0]
    invalid_closed = cur.execute(
        """
        SELECT COUNT(*) FROM sequences
        WHERE status IN ('Open', 'No Reply', 'Replied - No Opp') AND closed_at IS NOT NULL
        """
    ).fetchone()[0]

    assert total_leads == LEAD_COUNT, f"Expected {LEAD_COUNT} leads, got {total_leads}"
    assert total_sequences == LEAD_COUNT, f"Expected {LEAD_COUNT} sequences, got {total_sequences}"
    assert orphaned == 0, f"Orphaned sequences detected: {orphaned}"
    assert no_sequence == 0, f"Leads with no sequence: {no_sequence}"
    assert null_lead_ids == 0, f"Null lead IDs: {null_lead_ids}"
    assert conv_deal_zero == 0, "Converted records with deal=0 found"
    assert won_deal_zero == 0, "Closed Won with deal=0 found"
    assert future_dates == 0, "Future dates found"
    assert null_opp_for_non_converted == 0, "Non-converted with opportunity_created_at found"
    assert invalid_closed == 0, "Invalid closed_at values found"

    tier_rows = cur.execute(
        "SELECT icp_tier, COUNT(*) * 1.0 / ? FROM leads GROUP BY icp_tier ORDER BY icp_tier",
        (LEAD_COUNT,),
    ).fetchall()
    reply_t1 = cur.execute(
        """
        SELECT AVG(replied) FROM leads l
        JOIN sequences s ON l.lead_id = s.lead_id
        WHERE l.icp_tier = 'Tier 1'
        """
    ).fetchone()[0]
    reply_t3 = cur.execute(
        """
        SELECT AVG(replied) FROM leads l
        JOIN sequences s ON l.lead_id = s.lead_id
        WHERE l.icp_tier = 'Tier 3'
        """
    ).fetchone()[0]

    print(f"Total leads:              {total_leads}")
    print(f"Total sequences:          {total_sequences}")
    print(f"Orphaned sequences:       {orphaned}")
    print(f"Leads with no sequence:   {no_sequence}")
    print(f"Null lead_ids:            {null_lead_ids}")
    print(
        "Tier distribution:        "
        + ", ".join([f"{tier} {pct * 100:.1f}%" for tier, pct in tier_rows])
    )
    print(f"Reply rate Tier 1:        {reply_t1:.2%}")
    print(f"Reply rate Tier 3:        {reply_t3:.2%}")
    print(f"Converted with deal=0:    {conv_deal_zero}")
    print(f"Closed Won with deal=0:   {won_deal_zero}")
    print(f"Dates in future:          {future_dates}")


def generate_mock_data() -> None:
    random.seed(SEED)
    fake = Faker()
    Faker.seed(SEED)

    schema_path = Path(__file__).resolve().parent / "schema.sql"
    schema_sql = schema_path.read_text(encoding="utf-8")
    owners = [fake.name() for _ in range(OWNER_POOL_SIZE)]
    leads = [_generate_lead(fake, owners) for _ in range(LEAD_COUNT)]
    sequences = [_generate_sequence(lead) for lead in leads]

    with sqlite3.connect(DB_PATH) as conn:
        conn.executescript(schema_sql)
        conn.executemany(
            """
            INSERT INTO leads (
                lead_id, company_name, icp_tier, persona, source, industry,
                employee_count, annual_revenue, region, owner_name, created_at
            ) VALUES (
                :lead_id, :company_name, :icp_tier, :persona, :source, :industry,
                :employee_count, :annual_revenue, :region, :owner_name, :created_at
            )
            """,
            leads,
        )
        conn.executemany(
            """
            INSERT INTO sequences (
                sequence_id, lead_id, sequence_name, step_count, replied,
                converted_to_opp, deal_value, status, started_at, last_touch_at,
                opportunity_created_at, closed_at
            ) VALUES (
                :sequence_id, :lead_id, :sequence_name, :step_count, :replied,
                :converted_to_opp, :deal_value, :status, :started_at, :last_touch_at,
                :opportunity_created_at, :closed_at
            )
            """,
            sequences,
        )
        _quality_checks(conn)


if __name__ == "__main__":
    generate_mock_data()
