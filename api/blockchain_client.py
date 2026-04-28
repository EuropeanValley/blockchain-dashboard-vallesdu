"""
Blockchain API client.

Uses blockstream.info as primary API with mempool.space as fallback.
Both provide identical endpoints for Bitcoin data.
"""

import time
import requests

BLOCKSTREAM = "https://blockstream.info/api"
MEMPOOL     = "https://mempool.space/api"


def _get(path: str) -> requests.Response:
    """GET request with automatic fallback to mempool.space."""
    try:
        r = requests.get(f"{BLOCKSTREAM}{path}", timeout=10)
        r.raise_for_status()
        return r
    except Exception:
        r = requests.get(f"{MEMPOOL}{path}", timeout=10)
        r.raise_for_status()
        return r


def get_latest_block_hash() -> str:
    return _get("/blocks/tip/hash").text.strip()


def get_latest_block() -> dict:
    return get_block(get_latest_block_hash())


def get_block(block_hash: str) -> dict:
    return _get(f"/block/{block_hash}").json()


def get_block_by_height(height: int) -> dict:
    block_hash = _get(f"/block-height/{height}").text.strip()
    return get_block(block_hash)


def get_block_raw_header(block_hash: str) -> bytes:
    return bytes.fromhex(_get(f"/block/{block_hash}/header").text.strip())


def get_recent_blocks(n: int = 15) -> list[dict]:
    return _get("/blocks").json()[:n]


def get_difficulty_history(n_points: int = 12) -> list[dict]:
    """Builds difficulty history from adjustment blocks (every 2016 blocks)."""
    latest = get_latest_block()
    tip_height = latest["height"]
    last_adjustment = (tip_height // 2016) * 2016

    values = []
    for i in range(n_points):
        height = last_adjustment - (i * 2016)
        if height < 0:
            break
        try:
            block = get_block_by_height(height)
            values.append({"x": block["timestamp"], "y": block["difficulty"]})
            time.sleep(0.3)
        except Exception:
            continue

    return list(reversed(values))


def get_blocks_around_adjustment(n_periods: int = 8) -> list[dict]:
    """Returns blocks at each difficulty adjustment point."""
    latest = get_latest_block()
    tip_height = latest["height"]
    last_adjustment = (tip_height // 2016) * 2016

    blocks = []
    for i in range(n_periods):
        height = last_adjustment - (i * 2016)
        if height < 0:
            break
        try:
            block = get_block_by_height(height)
            blocks.append(block)
            time.sleep(0.3)
        except Exception:
            continue

    return list(reversed(blocks))


if __name__ == "__main__":
    block = get_latest_block()
    print("block height:", block["height"])
    print("hash:        ", block["id"])
    print("difficulty:  ", block["difficulty"])
    print("nonce:       ", block["nonce"])
    print("n_tx:        ", block["tx_count"])