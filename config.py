from pathlib import Path

DB_PATH = str((Path(__file__).resolve().parent / "revops_pipeline.db").resolve())

ICP_TIERS = ["Tier 1", "Tier 2", "Tier 3"]
TIER_WEIGHTS = [0.20, 0.30, 0.50]

PERSONAS = [
    "VP of Sales",
    "VP of Marketing",
    "Chief Revenue Officer",
    "Chief Financial Officer",
    "Head of Revenue Operations",
    "Director of Sales Operations",
    "CEO",
]

SOURCES = ["Outbound", "Inbound", "Referral", "Event"]
SOURCE_WEIGHTS = [0.50, 0.20, 0.20, 0.10]

INDUSTRIES = [
    "SaaS",
    "Fintech",
    "Healthcare Tech",
    "E-commerce",
    "Logistics",
    "Cybersecurity",
    "HR Tech",
]

REGIONS = ["North America", "Europe", "APAC", "LATAM", "MENA"]

SOURCE_TO_SEQUENCES = {
    "Outbound": ["Q2 Outbound Cold", "ABM Campaign"],
    "Inbound": ["Inbound Follow-up"],
    "Referral": ["Executive Referral", "Partner Sourced"],
    "Event": ["Event Follow-up"],
}

REPLY_RATE = {"Tier 1": 0.40, "Tier 2": 0.20, "Tier 3": 0.08}
CONV_RATE = {"Tier 1": 0.50, "Tier 2": 0.30, "Tier 3": 0.15}
STATUS_WEIGHTS = {"Closed Won": 0.30, "Closed Lost": 0.50, "Open": 0.20}

DEAL_RANGE = {
    "Tier 1": (50_000, 180_000),
    "Tier 2": (20_000, 100_000),
    "Tier 3": (5_000, 50_000),
}

EMPLOYEE_RANGE = {"Tier 1": (500, 5000), "Tier 2": (100, 499), "Tier 3": (10, 99)}
REVENUE_RANGE = {
    "Tier 1": (50_000_000, 500_000_000),
    "Tier 2": (10_000_000, 49_000_000),
    "Tier 3": (1_000_000, 9_000_000),
}

OUTLIER_PROB = 0.03
OUTLIER_MULTIPLIER_RANGE = (1.5, 3.0)
LEAD_COUNT = 750
OWNER_POOL_SIZE = 15
SEED = 42
