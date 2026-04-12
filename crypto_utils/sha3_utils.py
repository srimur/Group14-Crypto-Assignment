import hashlib
import time


# Compute SHA-3 (Keccak-256) hex digest of a string
def sha3_hash(data: str) -> str:
    return hashlib.sha3_256(data.encode("utf-8")).hexdigest()


# Generate a 16-char hex ID from name, password, and timestamp
def generate_id(name: str, password: str, timestamp: float = None) -> str:
    if timestamp is None:
        timestamp = time.time()
    raw = f"{name}{timestamp}{password}"
    full_hash = sha3_hash(raw)
    return full_hash[:16]


# Generate a unique transaction ID by hashing UID + FID + timestamp + amount
def transaction_hash(uid: str, fid: str, timestamp: float, amount: float) -> str:
    raw = f"{uid}{fid}{timestamp}{amount}"
    return sha3_hash(raw)
