"""
M4 - AI Component: Block Arrival Time Anomaly Detector

Bitcoin blocks should arrive following an exponential distribution,
since each hash attempt is independent (memoryless Poisson process).
The expected mean inter-block time is 600 seconds (10 minutes).

This module detects blocks whose arrival time deviates significantly
from the expected exponential distribution using two methods:
  1. Z-score on log-transformed inter-block times
  2. Exponential distribution CDF threshold (p-value based)

Evaluation metrics: precision, recall, F1 (vs a simple threshold baseline).
"""

import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from scipy import stats

from api.blockchain_client import get_recent_blocks


@st.cache_data(ttl=120)
def fetch_blocks_for_ai(n: int = 25):
    return get_recent_blocks(n=n)


def compute_inter_times(blocks: list[dict]) -> pd.DataFrame:
    """Compute inter-block times in seconds from a list of blocks."""
    sorted_blocks = sorted(blocks, key=lambda b: b["timestamp"])
    rows = []
    for i in range(1, len(sorted_blocks)):
        prev = sorted_blocks[i - 1]
        curr = sorted_blocks[i]
        delta = curr["timestamp"] - prev["timestamp"]
        rows.append({
            "height": curr["height"],
            "timestamp": datetime.datetime.utcfromtimestamp(curr["timestamp"]).strftime("%H:%M:%S UTC"),
            "inter_time_s": delta,
            "inter_time_min": round(delta / 60, 2),
        })
    return pd.DataFrame(rows)


def detect_anomalies(df: pd.DataFrame, z_threshold: float = 2.0) -> pd.DataFrame:
    """
    Detect anomalous inter-block times using two methods:

    Method 1 - Z-score on log-transformed times:
      Bitcoin inter-block times follow Exp(lambda=1/600).
      Taking log makes the distribution more symmetric.
      Blocks with |z-score| > threshold are flagged.

    Method 2 - Exponential CDF p-value:
      Under H0 (exponential with mean=600s), compute the probability
      of seeing a value as extreme as observed.
      Blocks in the top or bottom 5% are flagged.
    """
    MEAN_EXPECTED = 600  # seconds

    # Method 1: Z-score on log-transformed times
    log_times = np.log(df["inter_time_s"].clip(lower=1))
    z_scores = (log_times - log_times.mean()) / log_times.std()
    df["z_score"] = z_scores.round(3)
    df["anomaly_zscore"] = z_scores.abs() > z_threshold

    # Method 2: Exponential CDF p-value
    # P(X <= x) for exponential with mean 600s
    cdf_vals = stats.expon.cdf(df["inter_time_s"], scale=MEAN_EXPECTED)
    # Flag if in bottom 2.5% or top 2.5% (two-tailed, p < 0.05)
    df["p_value"] = (2 * np.minimum(cdf_vals, 1 - cdf_vals)).round(4)
    df["anomaly_pvalue"] = df["p_value"] < 0.05

    # Combined: flagged by both methods
    df["anomaly"] = df["anomaly_zscore"] & df["anomaly_pvalue"]

    return df


def evaluate_model(df: pd.DataFrame, z_threshold: float) -> dict:
    """
    Evaluate the anomaly detector against a simple baseline.
    Baseline: flag any block with inter_time > 20 min or < 1 min.
    """
    # Baseline predictions
    baseline = (df["inter_time_s"] > 1200) | (df["inter_time_s"] < 60)

    # Our model predictions
    model = df["anomaly"]

    # Ground truth: use p-value method alone as reference
    truth = df["anomaly_pvalue"]

    def metrics(preds, truth):
        tp = (preds & truth).sum()
        fp = (preds & ~truth).sum()
        fn = (~preds & truth).sum()
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1        = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        return {"Precision": round(precision, 3), "Recall": round(recall, 3), "F1": round(f1, 3)}

    return {
        "Our model (Z-score + p-value)": metrics(model, truth),
        "Baseline (simple threshold)":   metrics(baseline, truth),
    }


def render() -> None:
    st.header("🤖 M4 — AI Component: Anomaly Detector")
    st.caption("Detecting abnormal Bitcoin block arrival times using statistical methods")

    st.info(
        "💡 **Why exponential?** Each hash attempt is independent, so the time until "
        "a valid block is found follows an exponential distribution with mean = 600s. "
        "Significant deviations may indicate mining pool behaviour, network issues, or luck."
    )

    # Controls
    col1, col2 = st.columns([1, 2])
    with col1:
        n_blocks = st.slider("Blocks to analyse", 10, 25, 20, key="m4_n")
        z_threshold = st.slider("Z-score threshold", 1.0, 3.0, 2.0, 0.1, key="m4_z",
                                help="Higher = fewer anomalies flagged")
    with col2:
        st.markdown("""
        **Model:** Z-score on log-transformed inter-block times + exponential CDF p-value test

        **Why this model?**
        - The exponential distribution is the theoretically correct baseline (Poisson process)
        - Log transform makes the distribution more symmetric for Z-score analysis
        - Using two independent tests reduces false positives
        - No training data needed — the model is based on the known distribution
        """)

    if "m4_loaded" not in st.session_state:
        st.session_state["m4_loaded"] = False

    if st.button("🔍 Run anomaly detection", key="m4_run"):
        fetch_blocks_for_ai.clear()
        st.session_state["m4_loaded"] = True

    if not st.session_state["m4_loaded"]:
        st.info("Click **Run anomaly detection** to start.")
        return

    with st.spinner("Fetching blocks and running detector..."):
        try:
            blocks = fetch_blocks_for_ai(n=n_blocks)
        except Exception as exc:
            st.error(f"Error fetching blocks: {exc}")
            return

    if len(blocks) < 3:
        st.warning("Not enough blocks to analyse.")
        return

    df = compute_inter_times(blocks)
    df = detect_anomalies(df, z_threshold=z_threshold)

    n_anomalies = df["anomaly"].sum()
    mean_time = df["inter_time_s"].mean()

    # ── SUMMARY METRICS ──────────────────────────────────────────────────────
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Blocks analysed", len(df))
    col2.metric("⚠️ Anomalies detected", int(n_anomalies))
    col3.metric("⏱️ Mean inter-block time", f"{mean_time:.0f}s ({mean_time/60:.1f} min)")
    col4.metric("🎯 Expected mean", "600s (10 min)")

    # ── INTER-BLOCK TIME CHART ────────────────────────────────────────────────
    st.divider()
    st.subheader("📊 Inter-block Times with Anomalies Highlighted")

    normal    = df[~df["anomaly"]]
    anomalous = df[df["anomaly"]]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=normal["height"].astype(str),
        y=normal["inter_time_s"] / 60,
        name="Normal",
        marker_color="#2ecc71",
    ))
    if not anomalous.empty:
        fig.add_trace(go.Bar(
            x=anomalous["height"].astype(str),
            y=anomalous["inter_time_s"] / 60,
            name="Anomaly",
            marker_color="#e74c3c",
        ))
    fig.add_hline(y=10, line_dash="dash", line_color="orange",
                  annotation_text="Target: 10 min", annotation_position="top right")
    fig.update_layout(
        title="Inter-block Times (red = anomaly detected)",
        xaxis_title="Block Height",
        yaxis_title="Time (minutes)",
        barmode="overlay",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── DISTRIBUTION PLOT ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("📈 Observed Distribution vs Theoretical Exponential")

    x_range = np.linspace(0, df["inter_time_s"].max() * 1.2, 300)
    exp_pdf  = stats.expon.pdf(x_range, scale=600)

    fig2 = go.Figure()
    fig2.add_trace(go.Histogram(
        x=df["inter_time_s"],
        histnorm="probability density",
        name="Observed",
        marker_color="rgba(247,147,26,0.6)",
        nbinsx=12,
    ))
    fig2.add_trace(go.Scatter(
        x=x_range,
        y=exp_pdf,
        mode="lines",
        name="Theoretical Exp(λ=1/600)",
        line=dict(color="white", dash="dash", width=2),
    ))
    fig2.update_layout(
        title="Observed inter-block times vs Exponential distribution (mean=600s)",
        xaxis_title="Inter-block time (seconds)",
        yaxis_title="Probability density",
    )
    st.plotly_chart(fig2, use_container_width=True)
    st.caption(
        "With only ~25 blocks the fit is approximate. Over thousands of blocks "
        "the distribution converges to Exp(λ=1/600) as predicted by Poisson process theory."
    )

    # ── RESULTS TABLE ─────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📋 Block-by-block Results")

    display_df = df[["height", "timestamp", "inter_time_min", "z_score", "p_value", "anomaly"]].copy()
    display_df.columns = ["Height", "Time (UTC)", "Inter-time (min)", "Z-score", "P-value", "Anomaly"]
    display_df["Anomaly"] = display_df["Anomaly"].map({True: "⚠️ YES", False: "✅ NO"})

    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # ── MODEL EVALUATION ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("📐 Model Evaluation")
    st.caption("Comparing our model vs a simple threshold baseline (flag if > 20 min or < 1 min)")

    eval_results = evaluate_model(df, z_threshold)
    eval_df = pd.DataFrame(eval_results).T.reset_index()
    eval_df.columns = ["Model", "Precision", "Recall", "F1"]
    st.dataframe(eval_df, use_container_width=True, hide_index=True)

    st.markdown("""
    **Metrics explained:**
    - **Precision** — of all flagged blocks, how many are truly anomalous
    - **Recall** — of all truly anomalous blocks, how many did we catch
    - **F1** — harmonic mean of precision and recall (overall performance)

    *Ground truth defined as: blocks in the bottom or top 2.5% of the exponential CDF (p < 0.05)*
    """)