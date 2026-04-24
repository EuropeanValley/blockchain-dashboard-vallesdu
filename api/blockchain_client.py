"""
Blockchain API client.

Provides helper functions to fetch blockchain data from public APIs.
- Blockstream (blockstream.info/api): block data, headers, transactions
- Blockchain.info (blockchain.info/api): difficulty history, stats
"""

import requests

BLOCKSTREAM_URL = "https://blockstream.info/api"
BLOCKCHAIN_INFO_URL = "https://blockchain.info"


# ─── FUNCIONES BÁSICAS DE BLOQUES ───────────────────────────────────────────

def get_latest_block_hash() -> str:
    """Devuelve el hash del último bloque de Bitcoin."""
    response = requests.get(f"{BLOCKSTREAM_URL}/blocks/tip/hash", timeout=10)
    response.raise_for_status()
    return response.text.strip()


def get_latest_block() -> dict:
    """Devuelve los datos completos del último bloque."""
    block_hash = get_latest_block_hash()
    return get_block(block_hash)


def get_block(block_hash: str) -> dict:
    """Devuelve los datos completos de un bloque dado su hash."""
    response = requests.get(f"{BLOCKSTREAM_URL}/block/{block_hash}", timeout=10)
    response.raise_for_status()
    return response.json()


def get_block_by_height(height: int) -> dict:
    """Devuelve los datos de un bloque dado su altura."""
    response = requests.get(f"{BLOCKSTREAM_URL}/block-height/{height}", timeout=10)
    response.raise_for_status()
    block_hash = response.text.strip()
    return get_block(block_hash)


def get_block_raw_header(block_hash: str) -> bytes:
    """Devuelve los 80 bytes crudos del header de un bloque (para M2)."""
    response = requests.get(f"{BLOCKSTREAM_URL}/block/{block_hash}/header", timeout=10)
    response.raise_for_status()
    return bytes.fromhex(response.text.strip())


# ─── FUNCIONES PARA M1: PROOF OF WORK MONITOR ───────────────────────────────

def get_recent_blocks(n: int = 15) -> list[dict]:
    """Devuelve los últimos n bloques (máximo 25 por limitación de la API)."""
    response = requests.get(f"{BLOCKSTREAM_URL}/blocks", timeout=10)
    response.raise_for_status()
    all_blocks = response.json()
    return all_blocks[:n]


# ─── FUNCIONES PARA M3: DIFFICULTY HISTORY ──────────────────────────────────

def get_difficulty_history(n_points: int = 50) -> list[dict]:
    """
    Devuelve el historial de dificultad de Bitcoin.
    Usa blockchain.info que tiene este endpoint directamente.
    Devuelve lista de {x: timestamp_unix, y: difficulty}.
    """
    response = requests.get(
        f"{BLOCKCHAIN_INFO_URL}/charts/difficulty",
        params={"format": "json", "timespan": "2years", "sampled": "true"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    values = data.get("values", [])
    return values[-n_points:]


def get_blocks_around_adjustment(n_periods: int = 5) -> list[dict]:
    """
    Devuelve bloques en los puntos de ajuste de dificultad.
    Cada período = 2016 bloques.
    """
    latest = get_latest_block()
    tip_height = latest["height"]
    last_adjustment = (tip_height // 2016) * 2016

    adjustment_blocks = []
    for i in range(n_periods):
        height = last_adjustment - (i * 2016)
        if height < 0:
            break
        try:
            block = get_block_by_height(height)
            adjustment_blocks.append(block)
        except Exception:
            continue

    return list(reversed(adjustment_blocks))


# ─── SCRIPT DE PRUEBA ────────────────────────────────────────────────────────

if __name__ == "__main__":
    block = get_latest_block()

    print("block height:", block["height"])
    print("hash:        ", block["id"])
    print("difficulty:  ", block["difficulty"])
    print("nonce:       ", block["nonce"])
    print("n_tx:        ", block["tx_count"])

    # Los primeros ceros del hash muestran que el minero encontró
    # un hash por debajo del target — eso es la Proof of Work.
    # El campo bits codifica ese target en formato compacto (256 bits).
    print("\nLeading zeros en el hash:")
    print(bin(int(block["id"], 16))[2:].zfill(256)[:20], "...")