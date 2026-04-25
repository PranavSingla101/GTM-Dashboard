import argparse
import random
import sys
import uuid
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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


def append_live_leads(count: int) -> list[str]:
    random.seed(SEED + 101)
    fake = Faker()
    Faker.seed(SEED + 101)
    owners = [fake.name() for _ in range(OWNER_POOL_SIZE)]
    inserted_ids: list[str] = []

    with get_conn() as conn:
        for _ in range(count):
            tier = random.choices(ICP_TIERS, weights=TIER_WEIGHTS, k=1)[0]
            source = random.choices(SOURCES, weights=SOURCE_WEIGHTS, k=1)[0]
            lead_id = str(uuid.uuid4())
            step_count = random.randint(1, 8)
            replied = random.random() < REPLY_RATE[tier]
            converted = replied and random.random() < CONV_RATE[tier]
            status = _status(replied, converted)

            created = date.today() - timedelta(days=random.randint(0, 90))
            started = min(date.today(), created + timedelta(days=random.randint(0, 3)))
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
                    fake.company(),
                    tier,
                    random.choice(PERSONAS),
                    source,
                    random.choice(INDUSTRIES),
                    random.randint(*EMPLOYEE_RANGE[tier]),
                    random.randint(*REVENUE_RANGE[tier]),
                    random.choice(REGIONS),
                    random.choice(owners),
                    created.isoformat(),
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
                    str(uuid.uuid4()),
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
            inserted_ids.append(lead_id)
    return inserted_ids


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=1)
    args = parser.parse_args()
    ids = append_live_leads(args.count)
    print("Inserted lead_ids:")
    for lead_id in ids:
        print(lead_id)
