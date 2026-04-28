"""
M3 - Difficulty History

Plots the evolution of Bitcoin mining difficulty over time:
- Difficulty value over the last adjustment periods
- Each difficulty adjustment event marked on the chart (every 2016 blocks)
- Ratio between actual block time and the 600-second target per period

The adjustment formula (Nakamoto 2008):
    new_difficulty = old_difficulty x (actual_time / expected_time)
    expected_time  = 2016 blocks x 600 seconds = 1,209,600 seconds
"""

import datetime

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import get_difficulty_history, get_blocks_around_adjustment


@st.cache_data(ttl=600)
def fetch_difficulty_history():
    return get_difficulty_history(n_points=12)


@st.cache_data(ttl=600)
def fetch_adjustment_blocks():
    return get_blocks_around_adjustment(n_periods=8)


def render() -> None:
    st.header("📈 M3 — Difficulty History")
    st.caption("Evolution of Bitcoin mining difficulty · Source: blockstream.info / mempool.space")

    st.info(
        "💡 **How difficulty adjustments work:** Every 2016 blocks (~2 weeks), Bitcoin "
        "automatically adjusts the mining difficulty so that blocks keep arriving every "
        "~10 minutes on average. If miners are too fast, difficulty goes up. If too slow, it goes down. "
        "Formula: `new_difficulty = old_difficulty × (actual_time / 1,209,600s)`"
    )

    # Only fetch data when the user clicks the button
    if "m3_data_loaded" not in st.session_state:
        st.session_state["m3_data_loaded"] = False

    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("📊 Load charts", key="m3_load"):
            fetch_difficulty_history.clear()
            fetch_adjustment_blocks.clear()
            st.session_state["m3_data_loaded"] = True
    with col2:
        if st.session_state["m3_data_loaded"]:
            st.success("Data loaded · Next refresh only when you click the button again")

    if not st.session_state["m3_data_loaded"]:
        st.info("Click **Load charts** to fetch data. This takes ~15 seconds.")
        return

    with st.spinner("Fetching difficulty history... (~15 seconds)"):
        try:
            values = fetch_difficulty_history()
        except Exception as exc:
            st.error(f"Error fetching difficulty history: {exc}")
            return

    df = pd.DataFrame(values)
    df["Date"] = pd.to_datetime(df["x"], unit="s")
    df["Difficulty (T)"] = df["y"] / 1e12

    # ── DIFFICULTY CHART ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("📊 Difficulty Over Time")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["Date"],
        y=df["Difficulty (T)"],
        mode="lines+markers",
        name="Difficulty",
        line=dict(color="#f7931a", width=2),
        marker=dict(color="red", size=8, symbol="diamond"),
        fill="tozeroy",
        fillcolor="rgba(247,147,26,0.1)",
    ))
    fig.update_layout(
        title="Bitcoin Mining Difficulty (last adjustment periods)",
        xaxis_title="Date",
        yaxis_title="Difficulty (Trillions)",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption("🔴 Each point marks a difficulty adjustment event (every ~2016 blocks ≈ 2 weeks).")

    # ── RATIO CHART ───────────────────────────────────────────────────────────
    st.divider()
    st.subheader("⏱️ Actual Block Time vs Target per Adjustment Period")

    with st.spinner("Fetching adjustment block data..."):
        try:
            adj_blocks = fetch_adjustment_blocks()
        except Exception as exc:
            st.warning(f"Could not fetch adjustment blocks: {exc}")
            adj_blocks = []

    if len(adj_blocks) >= 2:
        TARGET_TIME = 2016 * 600

        rows = []
        for i in range(1, len(adj_blocks)):
            prev = adj_blocks[i - 1]
            curr = adj_blocks[i]
            actual_time = curr["timestamp"] - prev["timestamp"]
            ratio = actual_time / TARGET_TIME
            date = datetime.datetime.utcfromtimestamp(curr["timestamp"]).strftime("%Y-%m-%d")
            rows.append({
                "Adjustment Date": date,
                "Height": curr["height"],
                "Actual Time (days)": round(actual_time / 86400, 1),
                "Target Time (days)": 14.0,
                "Ratio (actual/target)": round(ratio, 3),
                "Difficulty (T)": round(curr["difficulty"] / 1e12, 2),
            })

        df_adj = pd.DataFrame(rows)
        colors = ["#e74c3c" if r > 1 else "#2ecc71" for r in df_adj["Ratio (actual/target)"]]

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(
            x=df_adj["Adjustment Date"],
            y=df_adj["Ratio (actual/target)"],
            marker_color=colors,
            text=[f"{r:.3f}" for r in df_adj["Ratio (actual/target)"]],
            textposition="outside",
        ))
        fig2.add_hline(
            y=1.0,
            line_dash="dash",
            line_color="white",
            annotation_text="Target = 1.0 (perfect 10 min/block)",
            annotation_position="top right",
        )
        fig2.update_layout(
            title="Block Time Ratio per Adjustment Period",
            xaxis_title="Adjustment Date",
            yaxis_title="Ratio (actual / target)",
            showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)
        st.caption(
            "🟢 Green = miners were slower than target → difficulty decreases. "
            "🔴 Red = miners were faster than target → difficulty increases."
        )

        st.subheader("📋 Adjustment Period Summary")
        st.dataframe(df_adj, use_container_width=True, hide_index=True)
    else:
        st.warning("Not enough adjustment block data to compute ratios.")