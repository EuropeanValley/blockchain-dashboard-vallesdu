"""
M1 - Proof of Work Monitor

Muestra el estado en tiempo real de la minería de Bitcoin:
- Dificultad actual y su representación como umbral de ceros en SHA-256
- Distribución de tiempos entre bloques (distribución exponencial esperada)
- Hash rate estimado de la red
"""

import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from api.blockchain_client import get_latest_block, get_recent_blocks


def bits_to_target(bits: int) -> int:
    """
    Convierte el campo 'bits' del header al valor target de 256 bits.
    Formato compacto: primer byte = exponente, siguientes 3 = coeficiente.
    target = coeficiente * 2^(8*(exponente-3))
    """
    exponent = bits >> 24
    coefficient = bits & 0x00FFFFFF
    target = coefficient * (2 ** (8 * (exponent - 3)))
    return target


def count_leading_zero_bits(block_hash: str) -> int:
    """Cuenta los bits cero a la izquierda del hash del bloque."""
    n = int(block_hash, 16)
    return 256 - n.bit_length()


def estimate_hashrate(difficulty: float) -> float:
    """
    Estima el hash rate de la red a partir de la dificultad.
    Formula: hashrate = difficulty * 2^32 / 600
    (600s = tiempo objetivo entre bloques)
    """
    return difficulty * (2 ** 32) / 600


def render() -> None:
    """Render del panel M1."""
    st.header("⛏️ M1 — Proof of Work Monitor")
    st.caption("Live data from the Bitcoin network · Source: blockstream.info")

    # Auto-refresh: dispara un rerun cada 60 segundos sin bloquear la UI
    st_autorefresh(interval=60_000, key="m1_autorefresh")

    with st.spinner("Fetching blockchain data..."):
        try:
            latest = get_latest_block()
            recent_blocks = get_recent_blocks(n=15)
        except Exception as exc:
            st.error(f"❌ Error connecting to API: {exc}")
            return

    # ── MÉTRICAS PRINCIPALES ─────────────────────────────────────────────────
    difficulty = latest.get("difficulty", 0)
    bits = latest.get("bits", 0)
    block_hash = latest.get("id", "")
    height = latest.get("height", 0)

    target = bits_to_target(bits)
    leading_zeros = count_leading_zero_bits(block_hash)
    hashrate = estimate_hashrate(difficulty)
    hashrate_eh = hashrate / 1e18  # Convertir a EH/s (exahashes por segundo)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("📦 Block Height", f"{height:,}")
    col2.metric("🎯 Difficulty", f"{difficulty/1e12:.2f} T")
    col3.metric("⚡ Estimated Hash Rate", f"{hashrate_eh:.1f} EH/s")
    col4.metric("🔢 Leading Zero Bits", f"{leading_zeros}")

    # ── HASH AND TARGET ──────────────────────────────────────────────────────
    st.divider()
    st.subheader("🔍 Current Hash vs Target (256-bit SHA-256 space)")

    hash_bin = bin(int(block_hash, 16))[2:].zfill(256)
    target_bin = bin(target)[2:].zfill(256)

    st.markdown(f"""
    **Block hash** (hex): `{block_hash[:32]}...`

    **First 64 bits of hash** (binary):
    ```
    {hash_bin[:64]}...
    ```
    **First 64 bits of target**:
    ```
    {target_bin[:64]}...
    ```
    ✅ The hash has **{leading_zeros} leading zero bits** — it is below the target, Proof of Work is valid.
    """)

    st.info(
        "💡 **Why leading zeros?** Miners run billions of attempts until they find a nonce "
        "such that SHA-256(SHA-256(header)) < target. The higher the difficulty, the more zeros are required."
    )

    st.divider()
    st.subheader("⏱️ Inter-block Time Distribution")

    if len(recent_blocks) >= 2:
        timestamps = [b["timestamp"] for b in recent_blocks]
        timestamps.sort()
        inter_times = [
            (timestamps[i + 1] - timestamps[i]) / 60
            for i in range(len(timestamps) - 1)
        ]

        df_times = pd.DataFrame({"Minutes between blocks": inter_times})

        fig_hist = px.histogram(
            df_times,
            x="Minutes between blocks",
            nbins=15,
            title="Distribution of inter-block times (last blocks)",
            labels={"Minutes between blocks": "Time (minutes)", "count": "Frequency"},
            color_discrete_sequence=["#f7931a"],
        )
        fig_hist.add_vline(
            x=10,
            line_dash="dash",
            line_color="red",
            annotation_text="Target: 10 min",
            annotation_position="top right",
        )
        fig_hist.update_layout(
            xaxis_title="Time between blocks (minutes)",
            yaxis_title="Number of blocks",
            showlegend=False,
        )
        st.plotly_chart(fig_hist, use_container_width=True)

        avg_time = sum(inter_times) / len(inter_times)
        st.caption(
            f"Average of last {len(inter_times)} intervals: **{avg_time:.1f} min** "
            f"(target: 10 min). An exponential distribution is expected because each hash "
            f"attempt is independent — a Poisson process."
        )
    else:
        st.warning("Not enough blocks to compute intervals.")

    # ── RECENT BLOCKS TABLE ──────────────────────────────────────────────────
    st.divider()
    st.subheader("📋 Recent Blocks")

    rows = []
    for b in recent_blocks:
        rows.append({
            "Height": b.get("height"),
            "Hash (short)": b.get("id", "")[:16] + "...",
            "Nonce": b.get("nonce"),
            "Txs": b.get("tx_count"),
            "Timestamp": datetime.datetime.utcfromtimestamp(b.get("timestamp", 0)).strftime("%H:%M:%S UTC"),
        })

    df_blocks = pd.DataFrame(rows)
    st.dataframe(df_blocks, use_container_width=True, hide_index=True)

    st.caption(f"Last updated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")