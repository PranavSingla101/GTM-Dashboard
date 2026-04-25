import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.metrics import compute_kpis
from core.transformations import (
    apply_filters,
    load_joined_data,
    prepare_funnel_data,
    prepare_opp_rate_by_tier,
    prepare_persona_win_rates,
    prepare_pipeline_by_tier,
    prepare_recent_records,
    prepare_reply_rate_by_source,
    prepare_revenue_by_source,
)

st.set_page_config(
    page_title="GTM RevOps Dashboard",
    page_icon="bar_chart",
    layout="wide",
    initial_sidebar_state="expanded",
)


def fmt_currency(value: float) -> str:
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if value >= 1_000:
        return f"${value / 1_000:.0f}K"
    return f"${value:.0f}"


@st.cache_data(ttl=60)
def get_data() -> pd.DataFrame:
    return load_joined_data()


def bar_layout(title: str) -> dict:
    return dict(
        title=title,
        paper_bgcolor="#000000",
        plot_bgcolor="#1C1C1E",
        font=dict(color="#FFFFFF"),
        showlegend=False,
        margin=dict(l=10, r=10, t=40, b=20),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="#2C2C2E"),
    )


def main() -> None:
    df = get_data()
    st.sidebar.title("Filters")

    all_tiers = ["Tier 1", "Tier 2", "Tier 3"]
    selected_tiers = st.sidebar.multiselect("ICP Tier", all_tiers, default=all_tiers)

    all_sources = ["Outbound", "Inbound", "Referral", "Event"]
    selected_sources = st.sidebar.multiselect("Lead Source", all_sources, default=all_sources)

    all_personas = sorted(df["persona"].dropna().unique().tolist()) if not df.empty else []
    selected_personas = st.sidebar.multiselect("Persona", all_personas, default=all_personas)

    if not df.empty:
        min_date = df["created_at"].min().date()
        max_date = df["created_at"].max().date()
    else:
        today = pd.Timestamp.today().date()
        min_date = today
        max_date = today

    date_start, date_end = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if st.sidebar.button("Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    filtered_df = apply_filters(
        df,
        selected_tiers,
        selected_sources,
        selected_personas,
        date_start,
        date_end,
    )
    st.sidebar.caption(f"{len(filtered_df)} records matching filters")

    st.title("GTM RevOps Dashboard")
    st.caption("GTM pipeline performance - refreshes every 60s")

    if filtered_df.empty:
        st.warning("No records match the selected filters.")
        return

    kpis = compute_kpis(filtered_df)
    funnel = prepare_funnel_data(filtered_df)
    persona_df = prepare_persona_win_rates(filtered_df)
    pipeline_tier_df = prepare_pipeline_by_tier(filtered_df)
    revenue_source_df = prepare_revenue_by_source(filtered_df)
    reply_source_df = prepare_reply_rate_by_source(filtered_df)
    opp_tier_df = prepare_opp_rate_by_tier(filtered_df)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Total Opp Pipeline", fmt_currency(kpis["total_pipeline"]))
    col2.metric("Closed-Won Revenue", fmt_currency(kpis["closed_won_revenue"]))
    col3.metric("Win Rate", f"{kpis['win_rate'] * 100:.1f}%")
    col4.metric("Reply Rate", f"{kpis['reply_rate'] * 100:.1f}%")
    col5.metric("Active Sequences", f"{kpis['active_sequences']}")
    col6.metric("Avg Deal Size", fmt_currency(kpis["avg_deal_size"]))
    st.caption(f"Lost Pipeline: {fmt_currency(kpis['lost_pipeline'])}")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        fig = go.Figure(
            go.Funnel(
                y=["Total Leads", "Replied", "Opportunity", "Closed Won"],
                x=[
                    funnel["Total Leads"],
                    funnel["Replied"],
                    funnel["Opportunity"],
                    funnel["Closed Won"],
                ],
                textinfo="value+percent initial",
                marker=dict(color=["#0A84FF", "#30A0FF", "#30D158", "#FFD60A"]),
                connector=dict(line=dict(color="#636366", width=1)),
            )
        )
        fig.update_layout(
            title="GTM Funnel",
            paper_bgcolor="#000000",
            plot_bgcolor="#000000",
            font=dict(color="#FFFFFF"),
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        fig = go.Figure(
            go.Bar(
                y=persona_df["persona"],
                x=persona_df["win_rate"],
                orientation="h",
                marker=dict(color="#0A84FF"),
                text=[f"{v * 100:.1f}%" for v in persona_df["win_rate"]],
                textposition="outside",
            )
        )
        fig.update_layout(
            title="Win Rate by Persona",
            xaxis=dict(tickformat=".0%", showgrid=False),
            yaxis=dict(showgrid=False),
            paper_bgcolor="#000000",
            plot_bgcolor="#1C1C1E",
            font=dict(color="#FFFFFF"),
            margin=dict(l=20, r=40, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        fig = go.Figure(
            go.Bar(
                x=pipeline_tier_df["icp_tier"],
                y=pipeline_tier_df["pipeline_value"],
                marker_color="#0A84FF",
            )
        )
        fig.update_layout(**bar_layout("Pipeline by ICP Tier"))
        fig.update_yaxes(tickprefix="$", tickformat=".2s")
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = go.Figure(
            go.Bar(
                x=revenue_source_df["source"],
                y=revenue_source_df["closed_won_revenue"],
                marker_color="#30D158",
            )
        )
        fig.update_layout(**bar_layout("Closed-Won Revenue by Source"))
        fig.update_yaxes(tickprefix="$", tickformat=".2s")
        st.plotly_chart(fig, use_container_width=True)

    with c3:
        fig = go.Figure(
            go.Bar(
                x=reply_source_df["source"],
                y=reply_source_df["reply_rate"],
                marker_color="#0A84FF",
            )
        )
        fig.update_layout(**bar_layout("Reply Rate by Source"))
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

    with c4:
        fig = go.Figure(
            go.Bar(
                x=opp_tier_df["icp_tier"],
                y=opp_tier_df["opp_conversion_rate"],
                marker_color="#FFD60A",
            )
        )
        fig.update_layout(**bar_layout("Opp Conversion Rate by Tier"))
        fig.update_yaxes(tickformat=".0%")
        st.plotly_chart(fig, use_container_width=True)

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
        },
    )


if __name__ == "__main__":
    main()
