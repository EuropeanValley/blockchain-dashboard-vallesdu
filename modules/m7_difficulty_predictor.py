"""
M7 - Second AI Approach: Difficulty Predictor

Predicts the next Bitcoin difficulty adjustment using a linear regression model
trained on historical difficulty data fetched in M3.

This complements M4 (anomaly detector) by addressing a different problem:
instead of detecting abnormal blocks, it forecasts future network behaviour.

Model: Linear Regression on time-indexed difficulty values
Evaluation: MAE, RMSE, and R² on a held-out test set (last 3 periods)
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split

from api.blockchain_client import get_difficulty_history


@st.cache_data(ttl=600)
def fetch_difficulty_for_m7():
    return get_difficulty_history(n_points=20)


def render() -> None:
    st.header("🔮 M7 — Second AI Approach: Difficulty Predictor")
    st.caption("Predicting the next Bitcoin difficulty adjustment using Linear Regression")

    st.info(
        "💡 **Why a second model?** M4 detects anomalies in block arrival times. "
        "This module takes a different approach — it uses the historical difficulty trend "
        "to predict what the next adjustment value will be. "
        "Both models use real blockchain data but solve different problems."
    )

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("""
        **Model:** Linear Regression on time-indexed difficulty values

        **Why Linear Regression?**
        - Bitcoin difficulty has shown a consistent long-term upward trend
        - The relationship between time and difficulty is approximately linear on a log scale
        - Simple, interpretable, and easy to evaluate — ideal for demonstrating understanding
        - Unlike LSTM or Prophet, no black-box components

        **Features:** adjustment period index (1, 2, 3, ...) as the only predictor

        **Target:** difficulty value at each adjustment point
        """)
    with col2:
        n_future = st.slider("Periods to predict ahead", 1, 5, 3, key="m7_future")

    if "m7_loaded" not in st.session_state:
        st.session_state["m7_loaded"] = False

    if st.button("📈 Run predictor", key="m7_run"):
        fetch_difficulty_for_m7.clear()
        st.session_state["m7_loaded"] = True

    if not st.session_state["m7_loaded"]:
        st.info("Click **Run predictor** to fetch data and train the model.")
        return

    with st.spinner("Fetching difficulty history and training model..."):
        try:
            values = fetch_difficulty_for_m7()
        except Exception as exc:
            st.error(f"Error fetching data: {exc}")
            return

    if len(values) < 6:
        st.warning("Not enough data points to train the model. Try again later.")
        return

    df = pd.DataFrame(values)
    df["Date"]          = pd.to_datetime(df["x"], unit="s")
    df["Difficulty (T)"] = df["y"] / 1e12
    df["Period"]        = np.arange(len(df))

    # Train/test split — last 3 points as test set
    split = len(df) - 3
    train = df.iloc[:split]
    test  = df.iloc[split:]

    X_train = train[["Period"]].values
    y_train = train["Difficulty (T)"].values
    X_test  = test[["Period"]].values
    y_test  = test["Difficulty (T)"].values

    model = LinearRegression()
    model.fit(X_train, y_train)

    # Predictions on test set
    y_pred = model.predict(X_test)

    # Future predictions
    last_period  = df["Period"].max()
    future_periods = np.arange(last_period + 1, last_period + 1 + n_future).reshape(-1, 1)
    future_preds   = model.predict(future_periods)

    last_date    = df["Date"].max()
    future_dates = [last_date + pd.Timedelta(weeks=2 * (i + 1)) for i in range(n_future)]

    # ── METRICS ──────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📐 Model Evaluation (test set = last 3 adjustment periods)")

    mae  = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2   = r2_score(y_test, y_pred)

    col1, col2, col3 = st.columns(3)
    col1.metric("MAE",  f"{mae:.2f} T",  help="Mean Absolute Error in Trillions of difficulty")
    col2.metric("RMSE", f"{rmse:.2f} T", help="Root Mean Squared Error")
    col3.metric("R²",   f"{r2:.3f}",     help="1.0 = perfect fit, 0.0 = no predictive power")

    st.caption(
        f"Model equation: `difficulty = {model.coef_[0]:.2f} × period + {model.intercept_:.2f}` (in Trillions). "
        f"R²={r2:.3f} means the model explains {r2*100:.1f}% of the variance in difficulty."
    )

    # ── CHART ─────────────────────────────────────────────────────────────────
    st.divider()
    st.subheader("📊 Historical Difficulty + Model Predictions")

    fig = go.Figure()

    # Training data
    fig.add_trace(go.Scatter(
        x=train["Date"], y=train["Difficulty (T)"],
        mode="lines+markers", name="Historical (train)",
        line=dict(color="#f7931a", width=2),
        marker=dict(size=7),
    ))

    # Test data (actual)
    fig.add_trace(go.Scatter(
        x=test["Date"], y=test["Difficulty (T)"],
        mode="lines+markers", name="Historical (test)",
        line=dict(color="#3498db", width=2),
        marker=dict(size=7),
    ))

    # Test predictions
    fig.add_trace(go.Scatter(
        x=test["Date"], y=y_pred,
        mode="lines+markers", name="Predicted (test)",
        line=dict(color="#e74c3c", width=2, dash="dash"),
        marker=dict(size=7, symbol="x"),
    ))

    # Future predictions
    fig.add_trace(go.Scatter(
        x=future_dates, y=future_preds,
        mode="lines+markers", name="Predicted (future)",
        line=dict(color="#2ecc71", width=2, dash="dot"),
        marker=dict(size=9, symbol="diamond"),
    ))

    fig.update_layout(
        title="Bitcoin Difficulty: Historical vs Linear Regression Predictions",
        xaxis_title="Date",
        yaxis_title="Difficulty (Trillions)",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.25),
    )
    st.plotly_chart(fig, use_container_width=True)

    # ── FUTURE PREDICTIONS TABLE ──────────────────────────────────────────────
    st.divider()
    st.subheader(f"🔮 Next {n_future} Predicted Adjustment(s)")

    future_rows = []
    for i, (date, pred) in enumerate(zip(future_dates, future_preds)):
        current = df["Difficulty (T)"].iloc[-1]
        change  = ((pred - current) / current) * 100
        future_rows.append({
            "Adjustment": f"Period +{i+1}",
            "Estimated Date": date.strftime("%Y-%m-%d"),
            "Predicted Difficulty (T)": f"{pred:.2f}",
            "Change vs current (%)": f"{change:+.1f}%",
        })

    st.dataframe(pd.DataFrame(future_rows), use_container_width=True, hide_index=True)

    # ── COMPARISON WITH M4 ────────────────────────────────────────────────────
    st.divider()
    st.subheader("🔄 Comparison with M4 (Anomaly Detector)")

    st.markdown("""
    | | M4 — Anomaly Detector | M7 — Difficulty Predictor |
    |---|---|---|
    | **Problem** | Detect abnormal block times | Forecast next difficulty value |
    | **Model** | Z-score + Exponential CDF | Linear Regression |
    | **Data** | Last ~25 inter-block times | Last ~20 difficulty adjustments |
    | **Output** | Anomaly flag per block | Predicted difficulty value |
    | **Evaluation** | Precision, Recall, F1 | MAE, RMSE, R² |
    | **Assumption** | Exponential distribution baseline | Linear trend in difficulty |
    | **Limitation** | Small sample size (~25 blocks) | Linear model may underfit accelerating growth |
    """)

    st.caption(
        "Both models complement each other: M4 monitors real-time mining behaviour, "
        "while M7 provides a longer-term forecast of network difficulty."
    )
