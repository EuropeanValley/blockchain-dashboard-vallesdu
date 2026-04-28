"""
M2 - Block Header Analyzer

Displays the 80-byte structure of a Bitcoin block header and verifies
the Proof of Work locally using Python's hashlib.
"""

import hashlib
import struct
import datetime

import streamlit as st

from api.blockchain_client import get_latest_block, get_block, get_block_raw_header
from modules.m1_pow_monitor import bits_to_target, count_leading_zero_bits


def parse_header(raw: bytes) -> dict:
    """
    Parses the 80 raw bytes of a Bitcoin block header.
    Structure:
      4  bytes - version       (little-endian int32)
      32 bytes - prev_hash     (little-endian, display reversed)
      32 bytes - merkle_root   (little-endian, display reversed)
      4  bytes - timestamp     (little-endian uint32)
      4  bytes - bits          (little-endian uint32)
      4  bytes - nonce         (little-endian uint32)
    """
    version     = struct.unpack_from("<I", raw,  0)[0]
    prev_hash   = raw[4:36][::-1].hex()
    merkle_root = raw[36:68][::-1].hex()
    timestamp   = struct.unpack_from("<I", raw, 68)[0]
    bits        = struct.unpack_from("<I", raw, 72)[0]
    nonce       = struct.unpack_from("<I", raw, 76)[0]
    return {"version": version, "prev_hash": prev_hash, "merkle_root": merkle_root,
            "timestamp": timestamp, "bits": bits, "nonce": nonce}


def verify_pow(raw_header: bytes) -> tuple[str, bool, int]:
    """Computes SHA256(SHA256(header)) and checks it against the target."""
    first    = hashlib.sha256(raw_header).digest()
    second   = hashlib.sha256(first).digest()
    hash_hex = second[::-1].hex()
    fields   = parse_header(raw_header)
    target   = bits_to_target(fields["bits"])
    is_valid = int(hash_hex, 16) < target
    leading  = count_leading_zero_bits(hash_hex)
    return hash_hex, is_valid, leading


def render() -> None:
    st.header("🔬 M2 — Block Header Analyzer")
    st.caption("Inspect the 80-byte header structure and verify Proof of Work locally")

    if "m2_selected_hash" not in st.session_state:
        st.session_state["m2_selected_hash"] = None

    col_a, col_b = st.columns([1, 2])
    with col_a:
        use_latest = st.button("Load latest block", key="m2_latest")
    with col_b:
        custom_hash = st.text_input("Or enter a block hash:", placeholder="000000000000000000...", key="m2_custom")

    if use_latest:
        with st.spinner("Fetching latest block..."):
            try:
                latest = get_latest_block()
                st.session_state["m2_selected_hash"] = latest["id"]
            except Exception as exc:
                st.error(f"Error fetching latest block: {exc}")
                return
    elif custom_hash.strip():
        st.session_state["m2_selected_hash"] = custom_hash.strip()

    block_hash = st.session_state["m2_selected_hash"]

    if not block_hash:
        st.info("Click **Load latest block** or enter a block hash to begin.")
        return

    with st.spinner("Fetching block header..."):
        try:
            block      = get_block(block_hash)
            raw_header = get_block_raw_header(block_hash)
        except Exception as exc:
            st.error(f"Error fetching block: {exc}")
            return

    fields = parse_header(raw_header)
    computed_hash, is_valid, leading_zeros = verify_pow(raw_header)
    target = bits_to_target(fields["bits"])

    st.divider()
    st.subheader("📋 80-byte Header Fields")
    st.caption("Hashes are shown in reversed byte order (Bitcoin display convention).")

    readable_time = datetime.datetime.utcfromtimestamp(fields["timestamp"]).strftime("%Y-%m-%d %H:%M:%S UTC")

    rows = [
        ("Version",      str(fields["version"]),                        "4 bytes",  "Block version number"),
        ("Prev. Hash",   fields["prev_hash"][:32] + "...",              "32 bytes", "Hash of the previous block"),
        ("Merkle Root",  fields["merkle_root"][:32] + "...",            "32 bytes", "Root of the transaction Merkle tree"),
        ("Timestamp",    f"{fields['timestamp']}  ({readable_time})",   "4 bytes",  "Unix time when block was mined"),
        ("Bits",         f"0x{fields['bits']:08x}  ({fields['bits']})", "4 bytes",  "Compact encoding of the PoW target"),
        ("Nonce",        str(fields["nonce"]),                          "4 bytes",  "Value miners iterate to find a valid hash"),
    ]

    for label, col in zip(["Field", "Value", "Size", "Notes"], st.columns([1.5, 3, 1, 3])):
        col.markdown(f"**{label}**")
    st.divider()
    for row in rows:
        for cell, col in zip(row, st.columns([1.5, 3, 1, 3])):
            col.write(cell)

    st.divider()
    st.subheader("🎯 bits → 256-bit Target Threshold")
    exponent    = (fields["bits"] >> 24) & 0xFF
    coefficient = fields["bits"] & 0x00FFFFFF
    st.markdown(f"""
The **bits** field `0x{fields['bits']:08x}` encodes the target in compact form:
- **Exponent** (first byte): `{exponent}`
- **Coefficient** (last 3 bytes): `0x{coefficient:06x}`
- **Formula:** `target = 0x{coefficient:06x} × 2^(8 × ({exponent} − 3))`

**Target (hex):**
```
{hex(target)}
```
Any block hash below this value is a valid Proof of Work.
    """)

    st.divider()
    st.subheader("✅ Local Proof of Work Verification (hashlib)")
    st.code(
        "import hashlib\n"
        "digest1   = hashlib.sha256(raw_header).digest()\n"
        "digest2   = hashlib.sha256(digest1).digest()\n"
        "block_hash = digest2[::-1].hex()  # reverse bytes for display",
        language="python",
    )

    col1, col2 = st.columns(2)
    col1.metric("🔢 Leading zero bits", f"{leading_zeros}")
    col2.metric("✅ PoW Valid?", "YES" if is_valid else "NO")

    if is_valid:
        st.success("**Hash < Target** — Proof of Work verified locally ✅")
    else:
        st.error("**Hash ≥ Target** — Proof of Work INVALID ❌")

    st.markdown(f"""
**Computed hash:**
```
{computed_hash}
```
**Target:**
```
{hex(target)}
```
**hash < target?** → **{'TRUE ✅' if is_valid else 'FALSE ❌'}**
    """)

    st.info(
        f"💡 The hash has **{leading_zeros} leading zero bits**. "
        "Each extra zero bit doubles the expected mining effort — "
        "this is the cryptographic guarantee behind Bitcoin's security."
    )