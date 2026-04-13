# Secure Centralized EV Charging Payment Gateway
## BITS F463 - Cryptography Term Project 2025-26

## Team Members
<<<<<<< HEAD
- Member 1 (ID: XXXXXXXX)
- Member 2 (ID: XXXXXXXX)
- Member 3 (ID: XXXXXXXX)

## What this project is
=======
- 
>>>>>>> e3271f8b98d2cf06673f2d8fd6b2068d64ba0e06

We built an EV charging payment system that uses ASCON for encrypting franchise data, SHA-3 for hashing, RSA to show how public key encryption works during credential transmission, and Shor's algorithm to show how quantum computers can break that RSA. All transactions are recorded on a blockchain.

The system runs as 3 separate Flask apps (simulating 3 physical devices):
- **Grid Authority** (port 5000) - the central server, handles registration, transaction processing, blockchain
- **Charging Kiosk** (port 5001) - the machine at the station, encrypts FID with ASCON, generates QR codes
- **User Device** (port 5002) - the EV owner's phone, registers users, scans QR, initiates payments

They talk to each other over HTTP using the `requests` library.

## How to run

You need Python 3.9+ and pip.

```
pip install -r requirements.txt
```

Then open 3 terminals:

```
python grid_authority_app.py     # start this first, runs on port 5000
python charging_kiosk_app.py     # port 5001
python user_device_app.py        # port 5002
```

Open http://127.0.0.1:5000, http://127.0.0.1:5001, http://127.0.0.1:5002 in your browser.

Grid Authority has to be running before the other two because they call its APIs.

There's also a standalone CLI version: `python main.py`

See `MANUAL_DEMO_STEPS.md` for a full demo walkthrough with exact inputs.

## Project structure

```
BITSF463_Team_99/
|-- config.py                    - all constants (ASCON key, RSA bits, timeout, etc)
|-- grid_authority_app.py        - Grid Authority web app
|-- charging_kiosk_app.py        - Charging Kiosk web app
|-- user_device_app.py           - User Device web app
|-- main.py                      - CLI version
|-- crypto_utils/
|   |-- ascon.py                 - ASCON-128 encrypt/decrypt wrapper
|   |-- sha3_utils.py            - SHA-3 hashing (IDs, passwords, transactions)
|   |-- rsa_utils.py             - RSA keygen, encrypt, decrypt
|   |-- shor_simulation.py       - classical simulation of Shor's algorithm
|-- blockchain/
|   |-- ledger.py                - Block and Blockchain classes
|-- entities/
|   |-- grid_authority.py        - GridAuthority class (registration, transaction logic)
|   |-- franchise.py             - Franchise class
|   |-- ev_owner.py              - EVOwner class
|   |-- charging_kiosk.py        - ChargingKiosk class (ASCON encryption, QR gen)
|-- qr_utils.py                  - QR code image generation
|-- qr_codes/                    - generated QR images go here
```

## Transaction flow

1. Franchise registers with the Grid (gets a FID = SHA3 hash of name+timestamp+password, truncated to 16 hex chars)
2. User registers with the Grid (gets UID and VMID, PIN is stored as SHA3 hash)
3. Kiosk encrypts the FID using ASCON-128 with a random nonce, puts the ciphertext + tag into a QR code
4. User scans the QR code, enters their PIN and amount on their device
5. Device sends the QR data + VMID + PIN + amount to the Kiosk
6. Kiosk decrypts the QR using ASCON (recovers the FID), then forwards everything to the Grid
7. Grid checks: does this VMID exist? is the account active? does SHA3(pin) match? is balance enough?
8. If yes, deducts from user, credits franchise, creates a new block on the blockchain
9. Response goes back: Grid -> Kiosk -> User Device

If hardware fails after payment (we simulate this randomly at 10%), the transaction is reversed and a dispute block is added to the chain.

## How we use each algorithm

### ASCON-128
We use the `ascon` Python library. The kiosk encrypts the franchise ID before putting it in the QR code. ASCON gives us authenticated encryption - so if someone tampers with the QR data, the tag verification will fail and decryption is rejected.

- Key: 128-bit, stored in config.py
- Nonce: 128-bit, randomly generated per session using os.urandom(16)
- The QR contains: session_id | ciphertext_hex | tag_hex | associated_data_hex

We picked ASCON because it's the NIST lightweight crypto standard and it's meant for IoT/embedded devices like a charging kiosk.

### SHA-3 (Keccak-256)
We use Python's `hashlib.sha3_256`. It's used everywhere:
- FID = SHA3(name + timestamp + password)[:16] (first 16 hex chars)
- UID = same thing for users
- VMID = SHA3(UID + mobile)[:16]
- PIN stored as SHA3(pin), never plaintext
- Transaction ID = SHA3(uid + fid + timestamp + amount)
- Each blockchain block hash = SHA3(json dump of block data)

### RSA
We generate small RSA keys (20-bit modulus) at Grid startup. The user device encrypts PIN and VMID with the Grid's public key before sending. This is mainly to demonstrate what Shor's algorithm attacks.

We use 20-bit keys because the classical simulation of Shor's needs to brute-force the period finding, and that would take forever with real-sized keys. The algorithm itself is the same regardless of key size.

### Shor's Algorithm
Our simulation does this:
1. Takes the RSA modulus n
2. Picks random a, checks if gcd(a,n) gives a factor directly
3. Finds the order r of a mod n (smallest r where a^r = 1 mod n) - this is the quantum step, we just brute force it
4. If r is even, computes gcd(a^(r/2) ± 1, n) to get factors p and q
5. From p and q, computes phi = (p-1)(q-1), then recovers private key d = modular inverse of e mod phi
6. Verifies by encrypting and decrypting a test message

On a real quantum computer, step 3 would use quantum Fourier transform and run in polynomial time. Our brute force is exponential, which is why we need tiny keys.

### Blockchain
Simple append-only chain. Each block has: index, timestamp, transaction data, transaction ID (SHA3 hash), previous block hash, current block hash, and a dispute flag.

Validation checks two things for every block:
- recompute the hash from contents and compare with stored hash (catches tampering)
- check that previous_hash matches the actual hash of the block before it (catches insertion/deletion)

Genesis block is created when Grid starts, with zeroed fields.

## Assumptions we made

1. **Cross-zone charging is allowed.** A Tata Power user can charge at an Adani station. We decided this because real payment networks work across providers (like how any UPI app works at any merchant). The Grid doesn't check if user and franchise zones match.

2. **QR sessions are single-use.** Once a QR is used for a transaction, it can't be reused. This prevents replay attacks where someone photographs a QR and uses it again. If the transaction fails due to wrong PIN or low balance, the session is NOT consumed and the user can retry.

3. **QR sessions expire after 5 minutes (configurable in config.py).** After 5 min the kiosk rejects the QR. This limits the attack window if a QR code is leaked.

4. **Hardware failure is simulated at 10% probability.** After a successful payment, there's a random chance the charger fails. When this happens, funds are reversed and a dispute/refund block is added to the blockchain.

5. **PINs and passwords are never stored in plaintext.** We only store SHA3 hashes. During a transaction, we hash the entered PIN and compare hashes.

6. **RSA keys are 20 bits.** The classical simulation of Shor's needs to brute-force the period finding step, which is exponential. With 20-bit keys it runs in milliseconds. The algorithm and math are the same as with larger keys.

7. **All kiosks share one ASCON key.** Stored in config.py. In a real multi-kiosk deployment each kiosk would have its own key.

8. **Duplicate names in the same zone are rejected.** Two franchises can't have the same name in the same zone. Different zones can have same name though.

9. **Account deactivation is handled in code but not in the UI.** Each user/franchise has an `active` flag. If it's False, transactions are rejected. The logic is there but we didn't add a UI button for it.

10. **The blockchain is centralized.** Only the Grid Authority maintains it. No mining, no consensus, no distributed nodes. The problem statement says "centralized" so we kept it that way. The blockchain gives us tamper detection and audit trail.

11. **Nonces are never reused.** Each QR generation uses a fresh random nonce from os.urandom(16). Reusing a nonce with ASCON would break encryption security.

12. **Grid must start first.** The kiosk and device apps need the Grid to be running. If Grid is down they show error messages.

## Edge cases we handle

- **Not enough balance** - rejected, shows how much you have vs how much you need
- **Wrong PIN** - rejected, but the QR session stays valid so you can try again
- **VMID not found** - rejected
- **Tampered QR** - ASCON tag verification fails, transaction blocked
- **Expired QR** - kiosk checks timestamp, rejects if over 5 min old
- **QR already used** - kiosk checks the used flag, rejects
- **Unknown/invalid QR session** - session ID not found, rejected
- **Duplicate registration** - same name+zone combo rejected for both franchises and users
- **Inactive account** - if the active flag is False, transaction rejected
- **Hardware failure after payment** - funds reversed, dispute block added to blockchain
- **Blockchain tampered** - validate_chain() catches it by recomputing hashes
- **Grid or Kiosk offline** - connection errors caught, user sees a message instead of a crash
- **Bad zone code** - checked against VALID_ZONE_CODES during registration
- **PIN not 4 digits** - validated during registration

## Dependencies

- `ascon` - ASCON-128 encryption
- `qrcode[pil]` + `Pillow` - QR code generation
- `sympy` - prime checking and modular inverse for RSA
- `flask` - web framework
- `requests` - HTTP calls between the three apps

## References

- ASCON: https://ascon.iaik.tugraz.at/
- SHA-3 (FIPS 202): https://csrc.nist.gov/publications/detail/fips/202/final
- Shor's Algorithm: https://en.wikipedia.org/wiki/Shor%27s_algorithm
- Blockchain: https://en.wikipedia.org/wiki/Blockchain
