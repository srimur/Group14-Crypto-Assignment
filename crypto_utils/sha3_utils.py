import hashlib
import time


def sha3_hash(data: str) -> str:
    return hashlib.sha3_256(data.encode("utf-8")).hexdigest()


def generate_id(name: str, password: str, timestamp: float = None) -> str:
    if timestamp is None:
        timestamp = time.time()
    raw = f"{name}{timestamp}{password}"
    full_hash = sha3_hash(raw)
    return full_hash[:16]


def transaction_hash(uid: str, fid: str, timestamp: float, amount: float) -> str:
    raw = f"{uid}{fid}{timestamp}{amount}"
    return sha3_hash(raw)
