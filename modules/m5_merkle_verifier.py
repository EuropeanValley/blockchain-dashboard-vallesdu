"""
M5 - Merkle Proof Verifier

Picks a transaction from a block and verifies its Merkle proof step by step.
Each hash computation is shown explicitly.

Bitcoin's Merkle tree uses double SHA-256: SHA256(SHA256(data))
Leaf nodes are transaction IDs (txids) in little-endian byte order.
If the number of nodes at a level is odd, the last node is duplicated.
"""

import hashlib
import streamlit as st

from api.blockchain_client import get_latest_block, get_block, get_block_by_height, _get


@st.cache_data(ttl=120)
def fetch_block_txids(block_hash: str) -> list[str]:
    """Fetch all transaction IDs for a block."""
    response = _get(f"/block/{block_hash}/txids")
    return response.json()


@st.cache_data(ttl=120)
def fetch_block_for_m5(block_hash: str) -> dict:
    return get_block(block_hash)


def dsha256(data: bytes) -> bytes:
    """Double SHA-256 as used in Bitcoin."""
    return hashlib.sha256(hashlib.sha256(data).digest()).digest()


def merkle_hash_pair(left: str, right: str) -> str:
    """
    Combine two txids and compute their Merkle parent.
    Txids are reversed to internal byte order before hashing,
    then the result is reversed back for display.
    """
    left_bytes  = bytes.fromhex(left)[::-1]
    right_bytes = bytes.fromhex(right)[::-1]
    combined    = left_bytes + right_bytes
    result      = dsha256(combined)
    return result[::-1].hex()


def build_merkle_tree(txids: list[str]) -> list[list[str]]:
    """
    Build the full Merkle tree bottom-up.
    Returns a list of levels, from leaves (level 0) to root (last level).
    """
    levels = [txids[:]]
    current = txids[:]

    while len(current) > 1:
        if len(current) % 2 == 1:
            current.append(current[-1])  # duplicate last if odd

        next_level = []
        for i in range(0, len(current), 2):
            parent = merkle_hash_pair(current[i], current[i + 1])
            next_level.append(parent)
        levels.append(next_level)
        current = next_level

    return levels


def get_merkle_proof(txids: list[str], tx_index: int) -> list[dict]:
    """
    Generate the Merkle proof path for a transaction at tx_index.
    Returns list of steps with sibling hash and direction.
    """
    levels = build_merkle_tree(txids)
    proof  = []
    idx    = tx_index

    for level_num, level in enumerate(levels[:-1]):
        # Pad level if odd
        padded = level[:]
        if len(padded) % 2 == 1:
            padded.append(padded[-1])

        if idx % 2 == 0:
            sibling_idx = idx + 1
            direction   = "right"
        else:
            sibling_idx = idx - 1
            direction   = "left"

        sibling = padded[sibling_idx]
        proof.append({
            "level":    level_num,
            "current":  padded[idx],
            "sibling":  sibling,
            "direction": direction,
        })
        idx = idx // 2

    return proof


def verify_proof(txid: str, proof: list[dict], merkle_root: str) -> list[dict]:
    """
    Verify the proof step by step, returning each computation.
    """
    steps   = []
    current = txid

    for step in proof:
        sibling   = step["sibling"]
        direction = step["direction"]

        if direction == "right":
            left, right = current, sibling
        else:
            left, right = sibling, current

        parent = merkle_hash_pair(left, right)

        steps.append({
            "level":     step["level"],
            "left":      left,
            "right":     right,
            "computed":  parent,
            "direction": direction,
        })
        current = parent

    is_valid = current == merkle_root
    return steps, is_valid, current


def render() -> None:
    st.header("🌿 M5 — Merkle Proof Verifier")
    st.caption("Verify that a transaction belongs to a block using its Merkle proof")

    st.info(
        "💡 **What is a Merkle proof?** Instead of downloading all transactions in a block, "
        "you only need a small set of hashes (the proof path) to verify that a specific "
        "transaction is included. This is the foundation of SPV (Simplified Payment Verification)."
    )

    # Block selection
    st.subheader("1️⃣ Select a block")
    col1, col2 = st.columns([1, 2])
    with col1:
        use_latest = st.button("Load latest block", key="m5_latest")
    with col2:
        custom_hash = st.text_input("Or enter a block hash:", placeholder="000000000000...", key="m5_hash")

    if "m5_block_hash" not in st.session_state:
        st.session_state["m5_block_hash"] = None
    if "m5_txids" not in st.session_state:
        st.session_state["m5_txids"] = None

    if use_latest:
        with st.spinner("Fetching latest block..."):
            try:
                block = get_latest_block()
                st.session_state["m5_block_hash"] = block["id"]
                st.session_state["m5_txids"] = None
            except Exception as exc:
                st.error(f"Error: {exc}")
                return
    elif custom_hash.strip():
        st.session_state["m5_block_hash"] = custom_hash.strip()
        st.session_state["m5_txids"] = None

    block_hash = st.session_state["m5_block_hash"]
    if not block_hash:
        st.info("Select a block to begin.")
        return

    # Load txids
    if st.session_state["m5_txids"] is None:
        with st.spinner("Fetching transaction list..."):
            try:
                block  = fetch_block_for_m5(block_hash)
                txids  = fetch_block_txids(block_hash)
                st.session_state["m5_txids"]       = txids
                st.session_state["m5_merkle_root"] = block["merkle_root"]
                st.session_state["m5_height"]      = block["height"]
            except Exception as exc:
                st.error(f"Error fetching transactions: {exc}")
                return

    txids       = st.session_state["m5_txids"]
    merkle_root = st.session_state["m5_merkle_root"]
    height      = st.session_state["m5_height"]

    st.success(f"Block **{height}** loaded — **{len(txids)}** transactions")
    st.markdown(f"**Merkle Root (from header):** `{merkle_root}`")

    # Transaction selection
    st.divider()
    st.subheader("2️⃣ Select a transaction")

    tx_index = st.number_input(
        f"Transaction index (0 to {len(txids)-1}):",
        min_value=0, max_value=len(txids)-1, value=0, key="m5_txidx"
    )
    selected_txid = txids[tx_index]
    st.markdown(f"**Selected txid:** `{selected_txid}`")

    if not st.button("🔍 Verify Merkle proof", key="m5_verify"):
        return

    # Build and verify proof
    st.divider()
    st.subheader("3️⃣ Merkle proof — step by step")
    st.caption(
        "Each step combines the current hash with its sibling and computes SHA256(SHA256(left+right)). "
        "The final result must match the Merkle root stored in the block header."
    )

    with st.spinner("Computing proof..."):
        proof = get_merkle_proof(txids, tx_index)
        steps, is_valid, computed_root = verify_proof(selected_txid, proof, merkle_root)

    if not steps:
        st.info("This is the only transaction in the block — it IS the Merkle root.")
        if selected_txid == merkle_root or selected_txid[::-1] == merkle_root:
            st.success("✅ Transaction matches Merkle root directly.")
        return

    for i, step in enumerate(steps):
        with st.expander(f"Step {i+1} — Level {step['level']} → {step['level']+1}", expanded=True):
            st.markdown(f"""
| | Hash |
|---|---|
| **Left** | `{step['left'][:32]}...` |
| **Right** | `{step['right'][:32]}...` |
| **→ SHA256(SHA256(left + right))** | `{step['computed'][:32]}...` |
            """)
            if step["direction"] == "right":
                st.caption("Our hash is on the LEFT, sibling is on the RIGHT")
            else:
                st.caption("Sibling is on the LEFT, our hash is on the RIGHT")

    # Final result
    st.divider()
    st.subheader("4️⃣ Result")

    col1, col2 = st.columns(2)
    col1.markdown(f"**Computed root:**\n`{computed_root}`")
    col2.markdown(f"**Expected root (header):**\n`{merkle_root}`")

    if is_valid:
        st.success(
            f"✅ **Proof valid** — transaction `{selected_txid[:16]}...` "
            f"is confirmed to be in block {height}."
        )
    else:
        st.error("❌ Proof invalid — computed root does not match block header.")

    st.info(
        f"💡 Only **{len(steps)} hashes** were needed to verify this transaction "
        f"out of **{len(txids)} total** in the block. "
        f"That is log₂({len(txids)}) ≈ {len(steps)} steps — this is the power of Merkle trees."
    )
