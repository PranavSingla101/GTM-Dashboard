import pandas as pd


def compute_kpis(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "total_leads": 0,
            "total_replies": 0,
            "reply_rate": 0.0,
            "total_opps": 0,
            "opp_rate": 0.0,
            "closed_won_count": 0,
            "win_rate": 0.0,
            "total_pipeline": 0,
            "lost_pipeline": 0,
            "closed_won_revenue": 0,
            "active_sequences": 0,
            "avg_deal_size": 0.0,
        }

    total_leads = int(df["lead_id"].nunique())
    total_replies = int(df["replied"].sum())
    total_opps = int(df["converted_to_opp"].sum())
    closed_won_count = int((df["status"] == "Closed Won").sum())
    closed_lost_count = int((df["status"] == "Closed Lost").sum())
    total_pipeline = int(df.loc[df["converted_to_opp"], "deal_value"].sum())
    lost_pipeline = int(df.loc[df["status"] == "Closed Lost", "deal_value"].sum())
    closed_won_revenue = int(df.loc[df["status"] == "Closed Won", "deal_value"].sum())
    active_sequences = int((df["status"] == "Open").sum())
    nonzero_converted = df.loc[df["converted_to_opp"] & (df["deal_value"] > 0), "deal_value"]
    avg_deal_size = float(nonzero_converted.mean()) if not nonzero_converted.empty else 0.0
    won_lost_total = closed_won_count + closed_lost_count

    return {
        "total_leads": total_leads,
        "total_replies": total_replies,
        "reply_rate": float(total_replies / total_leads) if total_leads else 0.0,
        "total_opps": total_opps,
        "opp_rate": float(total_opps / total_leads) if total_leads else 0.0,
        "closed_won_count": closed_won_count,
        "win_rate": float(closed_won_count / won_lost_total) if won_lost_total else 0.0,
        "total_pipeline": total_pipeline,
        "lost_pipeline": lost_pipeline,
        "closed_won_revenue": closed_won_revenue,
        "active_sequences": active_sequences,
        "avg_deal_size": avg_deal_size,
    }
