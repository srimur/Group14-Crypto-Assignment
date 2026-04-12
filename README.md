# Secure Centralized EV Charging Payment Gateway
## BITS F463 - Cryptography Term Project 2025-26

A functional centralized EV Charging Payment Gateway that simulates smart-grid transactions using **Post-Quantum Cryptography**, **Lightweight Cryptography (ASCON)**, and **Blockchain**.

---

## Team Members
- Member 1 (ID: XXXXXXXX)
- Member 2 (ID: XXXXXXXX)
- Member 3 (ID: XXXXXXXX)

*(Replace with actual names and IDs)*

---

## Project Overview

This system simulates a complete digital transaction system for purchasing EV charging time. It consists of three interacting entities:

1. **Charging Kiosk** — Central processing machine at the EV charging station. Encrypts franchise information using ASCON lightweight cryptography and generates QR codes.
2. **User Device (EV Owner)** — Initiates charging sessions by scanning QR codes and providing payment details (VMID, PIN, amount).
3. **Grid Authority** — Central banking terminal that manages registration, validates credentials, processes transactions, and maintains the blockchain ledger.

### Cryptographic Components

| Component | Algorithm | Purpose |
|-----------|-----------|---------|
| Lightweight Crypto | ASCON-128 | Encrypt Franchise ID → Virtual FID, QR code encryption |
| Hashing | SHA-3 (Keccak-256) | ID generation (UID/FID), transaction IDs, block hashing |
| Quantum Demo | Shor's Algorithm | Demonstrates RSA public-key vulnerability |
| Blockchain | Custom chain with SHA-3 | Immutable transaction ledger with dispute handling |

---

## Project Structure

```
BITSF463_Team_99/
├── README.md
├── requirements.txt
├── config.py                  # Global configuration constants
├── crypto_utils/
│   ├── __init__.py
│   ├── ascon.py               # ASCON-128 AEAD implementation
│   ├── sha3_utils.py          # SHA-3 (Keccak-256) hashing utilities
│   ├── rsa_utils.py           # RSA key generation & encryption
│   └── shor_simulation.py     # Shor's algorithm simulation
├── blockchain/
│   ├── __init__.py
│   └── ledger.py              # Blockchain ledger with dispute handling
├── entities/
│   ├── __init__.py
│   ├── grid_authority.py      # Grid Authority entity
│   ├── franchise.py           # Franchise entity
│   ├── ev_owner.py            # EV Owner entity
│   └── charging_kiosk.py      # Charging Kiosk entity
├── qr_utils.py                # QR code generation and scanning
├── main.py                    # Main interactive CLI application
└── web_app.py                 # Optional: Flask Web UI add-on
```

---

## Prerequisites

- Python 3.9+
- pip

---

## Setup & Installation

```bash
# 1. Navigate to the project directory
cd BITSF463_Team_99

# 2. (Optional) Create a virtual environment
python3 -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r requirements.txt
```

---

## How to Run

```bash
python main.py
```

This launches an interactive CLI menu with the following options:

```
========================================
  EV Charging Payment Gateway
========================================
1. Register Franchise
2. Register EV Owner
3. Generate QR Code (Kiosk)
4. Initiate Charging Session (EV Owner)
5. View Blockchain Ledger
6. View Account Balances
7. Demonstrate Shor's Algorithm (Quantum Attack)
8. Validate Blockchain Integrity
9. Exit
========================================
```

### Typical Workflow

1. **Register a Franchise** (Option 1) — Provide franchise name, zone code, password, initial balance.
2. **Register an EV Owner** (Option 2) — Provide name, zone code, password, PIN, mobile number, initial balance.
3. **Generate QR Code** (Option 3) — The kiosk encrypts the Franchise ID using ASCON and produces a QR code.
4. **Initiate Charging Session** (Option 4) — The EV Owner scans the QR, enters VMID, PIN, and amount. The system processes the transaction end-to-end.
5. **View Blockchain Ledger** (Option 5) — Inspect all recorded transaction blocks.
6. **View Balances** (Option 6) — Check franchise and user account balances.
7. **Shor's Algorithm Demo** (Option 7) — Demonstrates how quantum computing can break RSA encryption.
8. **Validate Blockchain** (Option 8) — Verify chain integrity.
9. **Run Full Demo** (Option 9) — Runs an automated end-to-end demonstration with sample data.

---

## Web UI (Optional Add-on)

A browser-based interface is also available as an optional add-on. It reuses the same backend code and provides a visual way to interact with all three entities.

```bash
# Install Flask (if not already installed)
pip install flask

# Run the web server
python web_app.py
```

Then open **http://localhost:5000** in your browser. The Web UI provides tabs for:
- **Registration** — Register franchises and EV owners via forms
- **Kiosk & QR** — Generate QR codes with ASCON encryption
- **Charging Session** — Process payments through the full transaction flow
- **Blockchain** — View and validate the ledger visually
- **Balances** — Check all account balances
- **Shor's Attack** — Run the quantum attack demo with visual results
- **Run Full Demo** — One-click automated demo with a step-by-step log

> Note: The Web UI is entirely optional. The primary deliverable is the CLI (`main.py`).

---

## Design Assumptions & Edge Cases Handled

1. **Insufficient Balance**: Transaction is rejected if the user's balance is less than the requested amount.
2. **Invalid PIN**: Transaction is rejected; the user is notified.
3. **Invalid VMID**: Transaction is rejected if VMID doesn't match any registered user.
4. **Invalid Franchise (QR)**: If the decrypted FID from QR doesn't match a registered franchise, the session is denied.
5. **Duplicate Registration**: Franchise/User names within the same zone cannot be duplicated.
6. **Hardware Failure Simulation**: After a successful payment, there is a simulated chance of hardware failure. If this occurs, a **dispute/refund block** is appended to the blockchain and funds are reversed.
7. **Account Closure Mid-Session**: If a franchise or user account is marked inactive during processing, the transaction is rejected.
8. **Blockchain Tampering Detection**: Any modification to a block invalidates the chain from that point onward.

---

## Cryptographic Details

### ASCON-128 (Lightweight Cryptography)
- Used to encrypt the Franchise ID (FID) into a Virtual Franchise ID (VFID).
- The VFID is embedded in the QR code displayed on the kiosk.
- ASCON provides authenticated encryption with associated data (AEAD).
- Key and nonce are derived from the kiosk's session parameters.

### SHA-3 (Keccak-256)
- Used to generate 16-digit hexadecimal IDs for franchises (FID) and users (UID).
- Input: name + timestamp + password → SHA-3 hash → first 16 hex digits.
- Also used for transaction IDs and blockchain block hashing.

### RSA + Shor's Algorithm
- RSA is used to encrypt the EV Owner's PIN and VMID during transmission.
- Shor's algorithm is simulated to factor the RSA modulus, demonstrating the vulnerability.
- For demonstration purposes, small RSA key sizes (16-20 bits) are used so that the classical simulation of Shor's algorithm completes in reasonable time.

### Blockchain
- Each valid transaction creates a new block containing: Transaction ID, Previous Block Hash, Timestamp, transaction details, and a Dispute/Refund flag.
- The genesis block is created when the Grid Authority initializes.
- Chain integrity can be validated at any time.

---

## References

- [ASCON Lightweight Cryptography](https://ascon.iaik.tugraz.at/)
- [NIST SHA-3 Standard (FIPS 202)](https://csrc.nist.gov/publications/detail/fips/202/final)
- [Shor's Algorithm Explained](https://en.wikipedia.org/wiki/Shor%27s_algorithm)
- [Blockchain Fundamentals](https://en.wikipedia.org/wiki/Blockchain)
