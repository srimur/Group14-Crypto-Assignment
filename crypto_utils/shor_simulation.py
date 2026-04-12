import random
import math
import time


# Euclidean GCD
def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


# Find smallest r such that a^r ≡ 1 (mod N) — classical stand-in for quantum period-finding
def _classical_order_finding(a: int, N: int) -> int:
    r = 1
    current = a % N
    while current != 1:
        current = (current * a) % N
        r += 1
        if r > N:
            return -1
    return r


# Classical simulation of Shor's algorithm to factor N into (p, q)
def shor_factor(N: int, verbose: bool = True) -> tuple:
    if verbose:
        print(f"\n{'='*60}")
        print(f"  SHOR'S ALGORITHM — Factoring N = {N}")
        print(f"{'='*60}")

    if N % 2 == 0:
        if verbose:
            print(f"  N is even. Factors: (2, {N // 2})")
        return (2, N // 2)

    for b in range(2, int(math.log2(N)) + 1):
        a = round(N ** (1.0 / b))
        for candidate in [a - 1, a, a + 1]:
            if candidate > 1 and candidate ** b == N:
                if verbose:
                    print(f"  N is a perfect power: {candidate}^{b}")
                return (candidate, N // candidate)

    max_attempts = 20
    for attempt in range(1, max_attempts + 1):
        a = random.randint(2, N - 1)
        if verbose:
            print(f"\n  Attempt {attempt}: Chose random a = {a}")

        g = _gcd(a, N)
        if 1 < g < N:
            if verbose:
                print(f"  Lucky! gcd({a}, {N}) = {g}")
                print(f"  Factors: ({g}, {N // g})")
            return (g, N // g)

        if verbose:
            print(f"  gcd({a}, {N}) = {g} (trivial)")
            print(f"  Finding order of {a} mod {N} (quantum period-finding)...")

        r = _classical_order_finding(a, N)
        if verbose:
            print(f"  Order r = {r}")

        if r == -1 or r % 2 != 0:
            if verbose:
                print(f"  r is {'not found' if r == -1 else 'odd'}, retrying...")
            continue

        x = pow(a, r // 2, N)
        if x == N - 1:
            if verbose:
                print(f"  a^(r/2) ≡ -1 (mod N), retrying...")
            continue

        p = _gcd(x + 1, N)
        q = _gcd(x - 1, N)

        if p == 1 or p == N:
            p = q
        if q == 1 or q == N:
            q = p

        if 1 < p < N and 1 < q < N and p * q == N:
            if verbose:
                print(f"  SUCCESS! a^(r/2) mod N = {x}")
                print(f"  gcd({x}+1, {N}) = {p}")
                print(f"  gcd({x}-1, {N}) = {q}")
                print(f"\n  ✓ Factors of {N}: ({p}, {q})")
            return (p, q)

        if verbose:
            print(f"  Factors not useful: ({p}, {q}), retrying...")

    if verbose:
        print(f"\n  ✗ Failed to factor {N} after {max_attempts} attempts.")
    return (N, 1)


# Run Shor's algorithm on an RSA key and attempt to recover the private key
def demo_shor_attack(rsa_keys: dict):
    e, n = rsa_keys["public"]
    d, _ = rsa_keys["private"]
    real_p = rsa_keys["p"]
    real_q = rsa_keys["q"]

    print("\n" + "=" * 60)
    print("  QUANTUM ATTACK DEMONSTRATION")
    print("  Simulating Shor's Algorithm on RSA")
    print("=" * 60)
    print(f"\n  RSA Public Key:")
    print(f"    e = {e}")
    print(f"    n = {n}")
    print(f"\n  Known (secret) primes: p={real_p}, q={real_q}")
    print(f"\n  Attacker knows only (e, n). Attempting to factor n...")

    start_time = time.time()
    p_found, q_found = shor_factor(n, verbose=True)
    elapsed = time.time() - start_time

    print(f"\n  Time elapsed: {elapsed:.4f} seconds")

    if p_found * q_found == n and p_found != 1 and q_found != 1:
        phi = (p_found - 1) * (q_found - 1)
        try:
            from sympy import mod_inverse
            d_recovered = mod_inverse(e, phi)
            print(f"\n  ✓ Private key recovered!")
            print(f"    d (original)  = {d}")
            print(f"    d (recovered) = {d_recovered}")
            print(f"    Match: {d == d_recovered}")

            test_message = 42
            ciphertext = pow(test_message, e, n)
            decrypted = pow(ciphertext, d_recovered, n)
            print(f"\n  Decryption test:")
            print(f"    Original message:  {test_message}")
            print(f"    Encrypted:         {ciphertext}")
            print(f"    Decrypted (attack): {decrypted}")
            print(f"    Attack successful: {test_message == decrypted}")
        except Exception as ex:
            print(f"\n  Key recovery failed: {ex}")
    else:
        print(f"\n  ✗ Could not factor n. Attack failed for this attempt.")

    print("\n" + "=" * 60)
    print("  CONCLUSION: RSA is vulnerable to quantum attacks.")
    print("  Post-quantum algorithms (e.g., lattice-based) are needed.")
    print("=" * 60)
