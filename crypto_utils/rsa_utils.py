import random
from sympy import isprime, mod_inverse


def _generate_prime(bits: int) -> int:
    while True:
        candidate = random.getrandbits(bits)
        candidate |= (1 << (bits - 1)) | 1
        if isprime(candidate):
            return candidate


def generate_rsa_keypair(bits: int = 20) -> dict:
    half = bits // 2
    p = _generate_prime(half)
    q = _generate_prime(half)
    while q == p:
        q = _generate_prime(half)

    n = p * q
    phi = (p - 1) * (q - 1)

    e = 65537
    if e >= phi:
        e = 3
    while phi % e == 0:
        e += 2

    d = mod_inverse(e, phi)

    return {
        "public": (e, n),
        "private": (d, n),
        "p": p,
        "q": q,
    }


def rsa_encrypt(plaintext_int: int, public_key: tuple) -> int:
    e, n = public_key
    if plaintext_int >= n:
        raise ValueError(f"Plaintext integer {plaintext_int} must be < n={n}")
    return pow(plaintext_int, e, n)


def rsa_decrypt(ciphertext_int: int, private_key: tuple) -> int:
    d, n = private_key
    return pow(ciphertext_int, d, n)


def string_to_int(s: str) -> int:
    return int.from_bytes(s.encode("utf-8"), "big")


def int_to_string(i: int) -> str:
    length = (i.bit_length() + 7) // 8
    return i.to_bytes(length, "big").decode("utf-8")
