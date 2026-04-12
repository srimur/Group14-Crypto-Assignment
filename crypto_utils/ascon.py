import os
import ascon

ASCON_KEY_SIZE = 16   # 128-bit key
ASCON_NONCE_SIZE = 16 # 128-bit nonce
ASCON_TAG_SIZE = 16   # 128-bit auth tag


# Encrypt plaintext with ASCON-128 AEAD, returns (ciphertext, tag)
def ascon_encrypt(key: bytes, nonce: bytes, plaintext: bytes,
                  associated_data: bytes = b"") -> tuple:
    assert len(key) == ASCON_KEY_SIZE, f"Key must be {ASCON_KEY_SIZE} bytes"
    assert len(nonce) == ASCON_NONCE_SIZE, f"Nonce must be {ASCON_NONCE_SIZE} bytes"

    ct_with_tag = ascon.encrypt(key, nonce, associated_data, plaintext)

    ciphertext = ct_with_tag[:len(plaintext)]
    tag = ct_with_tag[len(plaintext):]

    return ciphertext, tag


# Decrypt ciphertext with ASCON-128, raises ValueError on tag mismatch
def ascon_decrypt(key: bytes, nonce: bytes, ciphertext: bytes,
                  tag: bytes, associated_data: bytes = b"") -> bytes:
    assert len(key) == ASCON_KEY_SIZE
    assert len(nonce) == ASCON_NONCE_SIZE
    assert len(tag) == ASCON_TAG_SIZE

    ct_with_tag = ciphertext + tag
    plaintext = ascon.decrypt(key, nonce, associated_data, ct_with_tag)

    if plaintext is None:
        raise ValueError("ASCON: Authentication tag mismatch! Data may be tampered.")

    return plaintext


# Generate a random 128-bit nonce
def generate_nonce() -> bytes:
    return os.urandom(ASCON_NONCE_SIZE)
