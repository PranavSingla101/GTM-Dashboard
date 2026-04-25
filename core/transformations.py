from datetime import date

import pandas as pd

from db.connection import execute_query


def load_joined_data() -> pd.DataFrame:
    sql = """
    SELECT
        l.lead_id,
        l.company_name,
        l.icp_tier,
        l.persona,
        l.source,
        l.industry,
        l.employee_count,
        l.annual_revenue,
        l.region,
        l.owner_name,
        l.created_at,
        s.sequence_id,
        s.sequence_name,
        s.step_count,
        s.replied,
        s.converted_to_opp,
        s.deal_value,
        s.status,
        s.started_at,
        s.last_touch_at,
        s.opportunity_created_at,
        s.closed_at
    FROM leads l
    LEFT JOIN sequences s ON l.lead_id = s.lead_id
    """
    df = execute_query(sql)
    if df.empty:
        return df
    df["replied"] = df["replied"].fillna(0).astype(int).astype(bool)
    df["converted_to_opp"] = df["converted_to_opp"].fillna(0).astype(int).astype(bool)
    for c in ["created_at", "started_at", "last_touch_at", "opportunity_created_at", "closed_at"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    return df


def apply_filters(
    df: pd.DataFrame,
    tiers: list[str],
    sources: list[str],
    personas: list[str],
    date_start: date,
    date_end: date,
) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    mask = (
        df["icp_tier"].isin(tiers)
        & df["source"].isin(sources)
        & df["persona"].isin(personas)
        & (df["created_at"].dt.date >= date_start)
        & (df["created_at"].dt.date <= date_end)
    )
    return df.loc[mask].copy()


def prepare_funnel_data(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"Total Leads": 0, "Replied": 0, "Opportunity": 0, "Closed Won": 0}
    return {
        "Total Leads": int(df["lead_id"].nunique()),
        "Replied": int(df["replied"].sum()),
        "Opportunity": int(df["converted_to_opp"].sum()),
        "Closed Won": int((df["status"] == "Closed Won").sum()),
    }


def prepare_persona_win_rates(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["persona", "won", "lost", "win_rate"])
    g = df.groupby("persona", as_index=False).agg(
        won=("status", lambda s: (s == "Closed Won").sum()),
        lost=("status", lambda s: (s == "Closed Lost").sum()),
    )
    g = g[(g["won"] + g["lost"]) > 0].copy()
    if g.empty:
        return pd.DataFrame(columns=["persona", "won", "lost", "win_rate"])
    g["win_rate"] = (g["won"] / (g["won"] + g["lost"])).round(4)
    return g.sort_values("win_rate", ascending=True).reset_index(drop=True)


def prepare_pipeline_by_tier(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["icp_tier", "pipeline_value"])
    out = (
        df[df["converted_to_opp"]]
        .groupby("icp_tier", as_index=False)["deal_value"]
        .sum()
        .rename(columns={"deal_value": "pipeline_value"})
    )
    return out


def prepare_lost_pipeline_by_tier(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["icp_tier", "lost_pipeline_value"])
    out = (
        df[df["status"] == "Closed Lost"]
        .groupby("icp_tier", as_index=False)["deal_value"]
        .sum()
        .rename(columns={"deal_value": "lost_pipeline_value"})
    )
    return out


def prepare_revenue_by_source(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["source", "closed_won_revenue"])
    out = (
        df[df["status"] == "Closed Won"]
        .groupby("source", as_index=False)["deal_value"]
        .sum()
        .rename(columns={"deal_value": "closed_won_revenue"})
    )
    return out


def prepare_reply_rate_by_source(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["source", "reply_rate"])
    out = df.groupby("source", as_index=False).agg(
        leads=("lead_id", "count"), replied=("replied", "sum")
    )
    out["reply_rate"] = (out["replied"] / out["leads"]).round(4)
    return out[["source", "reply_rate"]]


def prepare_opp_rate_by_tier(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["icp_tier", "opp_conversion_rate"])
    out = df.groupby("icp_tier", as_index=False).agg(
        leads=("lead_id", "count"), opps=("converted_to_opp", "sum")
    )
    out["opp_conversion_rate"] = (out["opps"] / out["leads"]).round(4)
    return out[["icp_tier", "opp_conversion_rate"]]


def prepare_recent_records(df: pd.DataFrame, n: int = 50) -> pd.DataFrame:
    cols = [
        "created_at",
        "company_name",
        "icp_tier",
        "persona",
        "source",
        "replied",
        "converted_to_opp",
        "status",
        "deal_value",
    ]
    if df.empty:
        return pd.DataFrame(columns=cols)
    return df.sort_values("created_at", ascending=False)[cols].head(n).reset_index(drop=True)
