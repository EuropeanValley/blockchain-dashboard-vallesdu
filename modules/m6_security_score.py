"""
M6 - Security Score

Estimates the cost (in USD/hour) of a 51% attack on Bitcoin based on live
hash rate data, and visualises how confirmation depth reduces attack probability
following Nakamoto (2008), Section 11.
"""

import numpy as np
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import get_latest_block


@st.cache_data(ttl=300)
def fetch_latest_for_m6():
    return get_latest_block()


def bits_to_target(bits: int) -> int:
    exponent    = bits >> 24
    coefficient = bits & 0x00FFFFFF
    return coefficient * (2 ** (8 * (exponent - 3)))


def estimate_hashrate(difficulty: float) -> float:
    """Estimate network hash rate from difficulty. hashrate = difficulty * 2^32 / 600"""
    return difficulty * (2 ** 32) / 600


def attacker_success_prob(q: float, z: int) -> float:
    """
    Probability that an attacker with hash fraction q catches up from z blocks behind.
    From Nakamoto (2008), Section 11:

        P = 1 - sum_{k=0}^{z} (lambda^k * e^-lambda / k!) * (1 - (q/p)^(z-k))

    where lambda = z * (q/p), p = 1 - q
    """
    if q >= 0.5:
        return 1.0
    p      = 1.0 - q
    lam    = z * (q / p)
    total  = 0.0
    for k in range(z + 1):
        poisson = (lam ** k) * np.exp(-lam) / np.math.factorial(k)
        total  += poisson * (1.0 - (q / p) ** (z - k))
    return max(0.0, 1.0 - total)


def render() -> None:
    st.header("🛡️ M6 — Security Score")
    st.caption("Cost of a 51% attack and confirmation depth security · Based on Nakamoto (2008) §11")

    st.info(
        "💡 **What is a 51% attack?** If an attacker controls more than half of Bitcoin's "
        "hash rate, they can rewrite recent blocks and double-spend transactions. "
        "The cost of such an attack depends on the current network hash rate and hardware prices."
    )

    with st.spinner("Fetching network data..."):
        try:
            block = fetch_latest_for_m6()
        except Exception as exc:
            st.error(f"Error fetching data: {exc}")
            return

    difficulty = block["difficulty"]
    hashrate   = estimate_hashrate(difficulty)
    hashrate_eh = hashrate / 1e18  # EH/s

    # ── HARDWARE ASSUMPTIONS ─────────────────────────────────────────────────
    st.divider()
    st.subheader("⚙️ Hardware Assumptions")
    st.caption("Adjust these values to model different attack scenarios.")

    col1, col2 = st.columns(2)
    with col1:
        asic_hashrate_th = st.number_input(
            "ASIC hash rate (TH/s per unit)", value=335.0, step=10.0, key="m6_asic_hr",
            help="e.g. Bitmain Antminer S21 Pro ≈ 335 TH/s"
        )
        asic_power_w = st.number_input(
            "ASIC power consumption (W)", value=3000.0, step=100.0, key="m6_asic_w"
        )
    with col2:
        asic_price_usd = st.number_input(
            "ASIC unit price (USD)", value=3500.0, step=100.0, key="m6_asic_price"
        )
        electricity_kwh = st.number_input(
            "Electricity cost (USD/kWh)", value=0.07, step=0.01, key="m6_elec"
        )

    # ── ATTACK COST CALCULATION ───────────────────────────────────────────────
    st.divider()
    st.subheader("💰 Estimated 51% Attack Cost")

    # Attacker needs 51% of network hash rate
    attack_hashrate    = hashrate * 0.51
    attack_hashrate_th = attack_hashrate / 1e12

    units_needed       = attack_hashrate_th / asic_hashrate_th
    hardware_cost      = units_needed * asic_price_usd
    power_total_kw     = units_needed * asic_power_w / 1000
    electricity_per_h  = power_total_kw * electricity_kwh
    total_cost_per_h   = electricity_per_h  # operational cost per hour

    col1, col2, col3 = st.columns(3)
    col1.metric("🌐 Network hash rate", f"{hashrate_eh:.1f} EH/s")
    col2.metric("⚔️ Attack hash rate needed (51%)", f"{attack_hashrate/1e18:.1f} EH/s")
    col3.metric("🖥️ ASICs needed", f"{units_needed:,.0f} units")

    col4, col5, col6 = st.columns(3)
    col4.metric("🏭 Hardware cost", f"${hardware_cost/1e9:.2f}B")
    col5.metric("⚡ Power needed", f"{power_total_kw/1e6:.2f} TW")
    col6.metric("💸 Electricity cost/hour", f"${electricity_per_h:,.0f}")

    st.markdown(f"""
    > To perform a 51% attack today, an attacker would need to purchase approximately
    > **{units_needed:,.0f} ASIC miners** at a hardware cost of **${hardware_cost/1e9:.2f} billion**,
    > consuming **{power_total_kw/1e3:.0f} MW** of electricity at
    > **${electricity_per_h:,.0f}/hour** in operational costs.
    """)

    st.caption(
        "⚠️ This assumes the attacker buys all hardware at market price. "
        "In practice, acquiring this much hardware would drive prices up significantly. "
        "Reference: Antminer S21 Pro (335 TH/s, ~3 kW, ~$3,500)."
    )

    # ── CONFIRMATION DEPTH CHART ──────────────────────────────────────────────
    st.divider()
    st.subheader("📉 Attack Success Probability vs Confirmation Depth")
    st.caption("Following Nakamoto (2008), Section 11 — Poisson approximation")

    attacker_fractions = [0.10, 0.20, 0.30, 0.40, 0.49]
    confirmations      = list(range(1, 31))

    fig = go.Figure()
    colors = ["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#8e44ad"]

    for q, color in zip(attacker_fractions, colors):
        probs = [attacker_success_prob(q, z) * 100 for z in confirmations]
        fig.add_trace(go.Scatter(
            x=confirmations,
            y=probs,
            mode="lines+markers",
            name=f"Attacker = {int(q*100)}% hash rate",
            line=dict(color=color, width=2),
        ))

    fig.update_layout(
        title="Probability of successful attack vs number of confirmations",
        xaxis_title="Number of confirmations (blocks)",
        yaxis_title="Attack success probability (%)",
        yaxis=dict(range=[0, 100]),
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.25),
    )
    st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "A merchant waiting for 6 confirmations faces near-zero risk even from an attacker "
        "with 30% of hash rate. This is why 6 confirmations is the standard for large transactions."
    )

    # ── CONFIRMATION TABLE ────────────────────────────────────────────────────
    st.divider()
    st.subheader("📋 Success Probability Table")

    q_custom = st.slider(
        "Attacker hash rate fraction", 0.01, 0.49, 0.10, 0.01,
        format="%g", key="m6_q",
        help="Fraction of total network hash rate controlled by attacker"
    )

    rows = []
    for z in [1, 2, 3, 6, 10, 20, 30]:
        prob = attacker_success_prob(q_custom, z) * 100
        rows.append({
            "Confirmations": z,
            "Attack success probability (%)": f"{prob:.4f}%",
            "Risk level": "🔴 High" if prob > 5 else ("🟡 Medium" if prob > 0.1 else "🟢 Low"),
        })

    import pandas as pd
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
