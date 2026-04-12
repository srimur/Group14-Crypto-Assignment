# Secure Centralized EV Charging Payment Gateway
## BITS F463 - Cryptography Term Project 2025-26

A functional centralized EV Charging Payment Gateway that simulates smart-grid transactions using **Post-Quantum Cryptography**, **Lightweight Cryptography (ASCON)**, and **Blockchain**.

---

## Team Members
- Srinath Murali
- Pranshu Maheshwari 
- Divyansh Nema
- Rajvee
- XYZ

*(Replace with actual names and IDs)*

---

## Project Overview

This system simulates a complete digital transaction system for purchasing EV charging time. It is designed as **three separate programs** representing three distinct physical entities:

| Entity | File | Port | Role |
|--------|------|------|------|
| Grid Authority Laptop | `grid_authority_app.py` | 5000 | Central server — registers entities, processes transactions, maintains blockchain |
| Charging Kiosk Terminal | `charging_kiosk_app.py` | 5001 | Station kiosk — encrypts FID with ASCON, generates QR codes, relays sessions to Grid |
| EV Owner Device | `user_device_app.py` | 5002 | User's phone/device — registers, scans QR codes, initiates charging sessions |

The three apps communicate over HTTP APIs, simulating real-world network communication between the entities.

### Cryptographic Components

| Component | Algorithm | Purpose |
|-----------|-----------|---------|
| Lightweight Crypto | ASCON-128 | Encrypt Franchise ID into Virtual FID, embedded in QR code |
| Hashing | SHA-3 (Keccak-256) | ID generation (UID/FID/VMID), transaction IDs, block hashing |
| Quantum Demo | Shor's Algorithm | Demonstrates RSA public-key vulnerability |
| Blockchain | Custom chain with SHA-3 | Immutable transaction ledger with dispute handling |

---

## Project Structure

```
BITSF463_Team_99/
├── README.md
├── MANUAL_DEMO_STEPS.md           # Step-by-step demo walkthrough with exact inputs
├── requirements.txt
├── config.py                      # Global configuration constants
├── grid_authority_app.py          # Entity 1: Grid Authority web app (port 5000)
├── charging_kiosk_app.py          # Entity 2: Charging Kiosk web app (port 5001)
├── user_device_app.py             # Entity 3: EV Owner Device web app (port 5002)
├── main.py                        # Standalone CLI application
├── crypto_utils/
│   ├── __init__.py
│   ├── ascon.py                   # ASCON-128 AEAD encrypt/decrypt
│   ├── sha3_utils.py              # SHA-3 (Keccak-256) hashing utilities
│   ├── rsa_utils.py               # RSA key generation & encryption
│   └── shor_simulation.py         # Shor's algorithm simulation
├── blockchain/
│   ├── __init__.py
│   └── ledger.py                  # Blockchain ledger with dispute handling
├── entities/
│   ├── __init__.py
│   ├── grid_authority.py          # Grid Authority entity class
│   ├── franchise.py               # Franchise entity class
│   ├── ev_owner.py                # EV Owner entity class
│   └── charging_kiosk.py          # Charging Kiosk entity class
├── qr_utils.py                    # QR code generation utilities
└── qr_codes/                      # Generated QR code images
```

---

## Prerequisites

- Python 3.9+
- pip

---

## Setup & Installation

```bash
# Navigate to the project directory
cd BITSF463_Team_99

# (Optional) Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

---

## How to Run (Three-Entity Web Apps)

Open **three separate terminals** and start the apps in this order:

**Terminal 1 — Grid Authority (start first):**
```bash
python grid_authority_app.py
```
Open http://127.0.0.1:5000

**Terminal 2 — Charging Kiosk:**
```bash
python charging_kiosk_app.py
```
Open http://127.0.0.1:5001

**Terminal 3 — EV Owner Device:**
```bash
python user_device_app.py
```
Open http://127.0.0.1:5002

### Typical Workflow

1. **Grid Authority (port 5000)** — Register a franchise (name, zone code, password, balance)
2. **User Device (port 5002)** — Register an EV owner (name, zone code, password, PIN, mobile, balance)
3. **Charging Kiosk (port 5001)** — Select the franchise and generate an ASCON-encrypted QR code (displayed on screen)
4. **User Device (port 5002)** — Select the QR session (or scan the QR code from the kiosk screen), pick your account, enter PIN and amount, and pay
5. **Grid Authority (port 5000)** — View the blockchain ledger to see the recorded transaction
6. **Grid Authority (port 5000)** — Check balances, validate blockchain integrity, run Shor's algorithm demo

### Data Flow

```
User Device (5002)  ──registers──>  Grid Authority (5000)
                                          │
Kiosk (5001)  ──fetches franchises──>  Grid Authority (5000)
Kiosk (5001)  ──encrypts FID with ASCON, generates QR──>  (local)
                                          │
User Device (5002)  ──scans QR, sends to──>  Kiosk (5001)
                                          │
Kiosk (5001)  ──decrypts QR, forwards──>  Grid Authority (5000)
                                          │
Grid Authority  ──validates, transfers funds, records──>  Blockchain
```

### QR Code Scanning

The User Device supports two ways to provide the QR session:
- **Dropdown selection** — Pick a session from the list (fetched from the Kiosk)
- **QR code scan** — Take a photo of the QR code displayed on the Kiosk screen (works on mobile and desktop)

### Mobile Access

To access the User Device app from a mobile phone (for QR scanning):
1. Ensure your phone and laptop are on the same WiFi network
2. Find your laptop's IP address (`ipconfig` on Windows)
3. Open `http://<laptop-ip>:5002` on your phone's browser

---

## CLI Application (Standalone)

A standalone CLI is also available that runs all entities in a single process:

```bash
python main.py
```

This provides an interactive menu for registration, QR generation, charging sessions, blockchain viewing, balance checking, Shor's algorithm demo, and a full automated demo.

---

## Design Assumptions & Edge Cases Handled

1. **Cross-Zone Charging**: Users can charge at any franchise regardless of energy provider or zone.
2. **Insufficient Balance**: Transaction is rejected if the user's balance is less than the requested amount.
3. **Invalid PIN**: Transaction is rejected; the user is notified.
4. **Invalid VMID**: Transaction is rejected if VMID doesn't match any registered user.
5. **Invalid Franchise (QR)**: If the decrypted FID from QR doesn't match a registered franchise, the session is denied.
6. **Duplicate Registration**: Franchise/User names within the same zone cannot be duplicated.
7. **Hardware Failure Simulation**: After a successful payment, there is a 10% simulated chance of hardware failure. If this occurs, a **dispute/refund block** is appended to the blockchain and funds are reversed.
8. **Account Closure Mid-Session**: If a franchise or user account is marked inactive during processing, the transaction is rejected.
9. **Blockchain Tampering Detection**: Any modification to a block invalidates the chain from that point onward.

---

## Cryptographic Details

### ASCON-128 (Lightweight Cryptography)
- Used to encrypt the Franchise ID (FID) into a Virtual Franchise ID (VFID).
- The VFID is embedded in the QR code displayed on the kiosk.
- ASCON provides authenticated encryption with associated data (AEAD).
- A fresh random nonce is generated per session to ensure each VFID is unique.

### SHA-3 (Keccak-256)
- Used to generate 16-digit hexadecimal IDs for franchises (FID) and users (UID).
- Input: name + timestamp + password → SHA-3 hash → first 16 hex digits.
- VMID is derived as SHA-3(UID + mobile number), truncated to 16 hex characters.
- Also used for transaction IDs and blockchain block hashing.

### RSA + Shor's Algorithm
- RSA is used to encrypt the EV Owner's PIN and VMID during transmission to the Grid.
- Shor's algorithm is simulated to factor the RSA modulus, recovering the private key and demonstrating the vulnerability of classical public-key cryptography.
- Small RSA key sizes (20 bits) are used so the classical simulation completes in reasonable time.

### Blockchain
- Each valid transaction creates a new block containing: Transaction ID, Previous Block Hash, Timestamp, transaction details, and a Dispute/Refund flag.
- The genesis block is created when the Grid Authority initializes.
- Chain integrity can be validated at any time by verifying hashes and linkages.

---

## References

- [ASCON Lightweight Cryptography](https://ascon.iaik.tugraz.at/)
- [NIST SHA-3 Standard (FIPS 202)](https://csrc.nist.gov/publications/detail/fips/202/final)
- [Shor's Algorithm Explained](https://en.wikipedia.org/wiki/Shor%27s_algorithm)
- [Blockchain Fundamentals](https://en.wikipedia.org/wiki/Blockchain)
