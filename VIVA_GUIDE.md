# Viva Preparation Guide

---

## ASCON-128

ASCON is the NIST Lightweight Cryptography standard selected in 2023. It is an AEAD cipher (Authenticated Encryption with Associated Data) built on a sponge construction with a 320-bit internal state.

The 320-bit state is divided into rate (64 bits) and capacity (256 bits). Data is absorbed into the rate portion and permuted. The permutation (called p) consists of three operations repeated over rounds: addition of a round constant, a 5-bit S-box applied to every bit-slice of the state, and a linear diffusion layer that mixes bits within each 64-bit word. Initialization uses 12 rounds (p^12), intermediate blocks use 6 rounds (p^6), and finalization uses 12 rounds again.

Encryption: the key and nonce are loaded into the state, then p^12 is applied. The plaintext is XORed with the rate portion to produce ciphertext. After all plaintext blocks, the key is XORed into the state again and p^12 is applied to squeeze out the 128-bit authentication tag.

The tag authenticates both the ciphertext and the associated data (unencrypted metadata). If even one bit of ciphertext or associated data is modified, the tag verification fails on decryption.

**In our project:** the kiosk encrypts the 16-digit FID using ASCON-128 with a fresh random 128-bit nonce per session. The ciphertext, tag, and associated data are encoded into the QR code. The same kiosk decrypts it later using the stored nonce. The associated data includes the kiosk identifier and timestamp.

**Why ASCON over AES-GCM:** ASCON has smaller gate count in hardware, lower power draw, and built-in side-channel resistance. For an embedded kiosk this matters. AES-GCM requires both AES and GHASH — ASCON does authenticated encryption natively in a single primitive.

**Nonce reuse:** if you reuse a nonce with the same key, XORing two ciphertexts cancels out the keystream and leaks plaintext information. Our code generates a fresh `os.urandom(16)` nonce per QR session, so this never happens.

---

## SHA-3 (Keccak-256)

SHA-3 is based on the Keccak sponge function, standardized as FIPS 202 in 2015. It is structurally different from SHA-2 (which uses Merkle-Damgard).

The sponge has a 1600-bit state (5x5 matrix of 64-bit words). For Keccak-256, rate r = 1088 bits and capacity c = 512 bits. The Keccak-f[1600] permutation has 24 rounds, each consisting of five steps: theta (column parity mixing), rho (bitwise rotation), pi (lane rearrangement), chi (nonlinear row mixing using x XOR (NOT y AND z)), and iota (round constant addition to break symmetry).

Absorb phase: input is padded (pad10*1) and split into r-bit blocks. Each block is XORed into the rate portion and Keccak-f is applied. Squeeze phase: r bits are read as output and Keccak-f is applied again if more output is needed. For a 256-bit digest, one squeeze is enough.

Security properties we rely on:
- Pre-image resistance: given H(x), can't find x. This protects stored PIN hashes and password hashes.
- Second pre-image resistance: given x, can't find x' != x with H(x) = H(x'). Ensures nobody can forge a different input that produces the same ID.
- Collision resistance: can't find any x, x' with H(x) = H(x'). With 256-bit output, birthday attack needs ~2^128 operations.

**In our project:** we use SHA-3 for FID = SHA3(name + timestamp + password)[:16hex], UID same way, VMID = SHA3(UID + mobile)[:16hex], PIN storage as SHA3(pin), password storage as SHA3(password), transaction IDs as SHA3(UID + FID + timestamp + amount), and block hashing as SHA3(JSON of block contents).

**Why truncate to 16 hex chars (64 bits)?** These are identifiers, not security-critical hashes. 64 bits gives 2^64 possible values — collision probability is negligible at our scale (a few hundred registrations at most).

---

## RSA

We generate RSA keys as follows: pick two random primes p and q (each ~10 bits for our demo), compute n = p*q and phi(n) = (p-1)(q-1). The public exponent e is 65537 (standard choice, it's prime and has low Hamming weight for fast exponentiation). If e >= phi, we fall back to e=3 and increment. The private exponent d = e^(-1) mod phi, computed using the extended Euclidean algorithm (via sympy's mod_inverse).

Encryption: c = m^e mod n. Decryption: m = c^d mod n. This works because m^(ed) = m^(1 + k*phi) = m * (m^phi)^k = m * 1^k = m (mod n) by Euler's theorem.

Security rests on the assumption that factoring n into p and q is computationally hard. Best classical algorithm is the General Number Field Sieve, which is sub-exponential but still infeasible for n > 2048 bits.

**In our project:** the Grid generates an RSA keypair at startup. The user device encrypts PIN and VMID with the Grid's public key before sending. The Grid decrypts with the private key. We use 20-bit keys so Shor's simulation can factor them.

**Why 20 bits is fine for demo:** we only need to show that Shor's can recover d from (e, n). The math is identical regardless of key size — only the runtime changes.

---

## Shor's Algorithm

Shor's algorithm factors an integer N in O((log N)^3) time on a quantum computer. Classical factoring is sub-exponential; Shor's makes it polynomial.

The algorithm:
1. Pick random a where 1 < a < N
2. Compute gcd(a, N). If it's not 1, we got lucky and found a factor directly.
3. Find the order r of a mod N, i.e., the smallest r such that a^r = 1 mod N. **This is the quantum step.**
4. If r is odd, go back to step 1 with a new a.
5. If r is even, compute x = a^(r/2) mod N. If x = N-1, go back to step 1.
6. Compute gcd(x+1, N) and gcd(x-1, N). At least one of these is a non-trivial factor of N.

**The quantum part (step 3):** create a register in superposition |0> + |1> + ... + |N-1>, compute f(x) = a^x mod N into a second register, measure the second register to collapse it to some value, then apply the Quantum Fourier Transform to the first register. The QFT converts the periodic structure of f(x) into peaks at multiples of N/r in the frequency domain. Measuring gives a value close to k*N/r for some k, from which r can be extracted using continued fractions.

**Our classical simulation:** we can't do the quantum part, so we brute-force the order by computing a^1, a^2, a^3, ... mod N until we hit 1. This takes O(r) time which can be up to O(N), making it exponential in the number of bits. That's why we need small N (20 bits).

**After factoring:** once we have p and q, we compute phi = (p-1)(q-1), then d = e^(-1) mod phi using the extended Euclidean algorithm. Now we have the private key. We verify by encrypting a test message with e and decrypting with the recovered d.

**What this demonstrates:** any data encrypted with RSA (like the user's PIN and VMID in our system) is vulnerable to a quantum attacker who can factor the public modulus. Post-quantum alternatives like lattice-based cryptography (CRYSTALS-Kyber) or code-based cryptography are needed.

---

## Blockchain

Our blockchain is a centralized append-only ledger maintained by the Grid Authority.

Each block contains:
- index (sequential)
- timestamp (time.time())
- transaction_data dict (uid, fid, amount, description, dispute flag)
- transaction_id = SHA3(uid + fid + timestamp + amount)
- previous_hash = hash of the previous block
- hash = SHA3(JSON dump of all block fields, sorted keys)

The genesis block (block #0) has zeroed UID/FID, amount 0, and previous_hash of 64 zeros.

**Chain validation:** for each block i from 1 to end:
- Recompute block i's hash from its contents. If it doesn't match the stored hash, the block was tampered.
- Check that block i's previous_hash equals block (i-1)'s hash. If not, the chain linkage is broken.

If both checks pass for every block, the chain is valid.

**Dispute/refund handling:** if hardware fails after payment (we simulate 10% probability), we don't modify or delete the payment block. We add a new block with negative amount and dispute=True. Both blocks remain on the chain permanently — the original charge and the refund. Balances are reversed in the Grid's in-memory ledger.

**Why centralized, not distributed:** the problem statement specifies a centralized payment gateway. The Grid is the single authority. There's no mining, no consensus mechanism, no distributed nodes. The blockchain here provides immutability and auditability, not decentralization.

---

## Design Assumptions

1. Cross-zone charging is allowed. A user registered under any provider can charge at any franchise. This matches how real payment networks operate.

2. Hardware failure is simulated with a 10% random probability after each successful payment. In reality this would come from the kiosk's hardware status.

3. RSA key size is 20 bits. This is only for the Shor's demo. The actual FID encryption uses ASCON-128 which is quantum-resistant (symmetric crypto is not broken by Shor's — Grover's algorithm only halves the effective key length, so 128-bit ASCON still provides 64-bit security against quantum).

4. The ASCON key is shared between all kiosks and stored in config.py. In production this would be securely provisioned per-kiosk using a key management system.

5. All state is in-memory. Restarting any app clears its data. This is fine for a demo.

6. PINs are exactly 4 digits, validated during registration.

7. Duplicate check: same (name + zone_code) pair is rejected for both franchises and users.

8. Account closure: we have an `active` flag on each franchise and user. If set to False, transactions involving that entity are rejected. We don't have a UI to deactivate accounts, but the code handles it.

9. Nonces are never reused. Each QR generation creates a fresh random nonce via os.urandom(16).

10. QR sessions are ephemeral. If the kiosk restarts, old QR codes become invalid because the session data (including the nonce) is lost.

---

## Implementation Details Worth Knowing

**ASCON library call:** `ascon.encrypt(key, nonce, associated_data, plaintext)` returns ciphertext concatenated with the 16-byte tag. We split them: `ct = result[:len(plaintext)]`, `tag = result[len(plaintext):]`. For decryption, we concatenate them back and call `ascon.decrypt(key, nonce, associated_data, ct+tag)`. If the tag doesn't verify, it returns None and we raise ValueError.

**QR data format:** `session_id|ciphertext_hex|tag_hex|associated_data_hex` — pipe-separated, all hex-encoded. Session ID is the nonce in hex (32 chars for 16 bytes).

**Inter-app communication:** the three Flask apps talk using the `requests` library over HTTP to 127.0.0.1. The Kiosk calls Grid's `/api/franchises` and `/api/process_transaction`. The User Device calls Grid's `/api/register_user` and `/api/providers`, and Kiosk's `/api/qr_sessions` and `/api/process_session`. All requests use JSON bodies.

**RSA in the transaction flow:** the user device encrypts PIN and VMID with RSA before sending. This is printed to console as a demonstration. The actual transaction processing on the Grid uses the plaintext PIN (hashed and compared). The RSA encryption here is to show that this step is what Shor's algorithm would attack.

**Block hash computation:** `json.dumps({all fields}, sort_keys=True)` then SHA3 of that string. The sort_keys ensures deterministic JSON output regardless of dict insertion order.

**Modular inverse for RSA:** we use sympy's `mod_inverse(e, phi)` which implements the extended Euclidean algorithm. This computes d such that e*d = 1 mod phi.

**Prime generation:** `random.getrandbits(bits)`, then set the MSB and LSB (`candidate |= (1 << (bits-1)) | 1`) to ensure correct bit-length and oddness, then test with sympy's `isprime()`.
