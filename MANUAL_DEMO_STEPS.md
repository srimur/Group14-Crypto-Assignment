# Manual Demo Steps — EV Charging Payment Gateway (Three-Entity Setup)

The system is split into three separate programs simulating the distinct entities:

| Entity                  | File                    | Port | URL                   | Color  |
| ----------------------- | ----------------------- | ---- | --------------------- | ------ |
| Grid Authority Laptop   | `grid_authority_app.py` | 5000 | http://localhost:5000 | Blue   |
| Charging Kiosk Terminal | `charging_kiosk_app.py` | 5001 | http://localhost:5001 | Green  |
| EV Owner Device         | `user_device_app.py`    | 5002 | http://localhost:5002 | Purple |

---

## Starting the System

Open **three separate terminals** and run one command in each:

**Terminal 1 — Grid Authority (start this first):**

```
python grid_authority_app.py
```

**Terminal 2 — Charging Kiosk:**

```
python charging_kiosk_app.py
```

**Terminal 3 — User Device:**

```
python user_device_app.py
```

Then open three browser tabs, one for each URL.

---

## Step 1: Register a Franchise (Grid Authority — port 5000)

Open http://localhost:5000 in the browser.

Go to the **Register Franchise** tab and fill in:

| Field           | Example Input    |
| --------------- | ---------------- |
| Franchise Name  | `Tata EV Hub`    |
| Zone Code       | `TP-NORTH`       |
| Password        | `tata@secure123` |
| Initial Balance | `50000`          |

Click **Register Franchise**.

Valid zone codes:

- Tata Power: `TP-NORTH`, `TP-SOUTH`, `TP-WEST`
- Adani: `AD-NORTH`, `AD-SOUTH`, `AD-EAST`
- ChargePoint: `CP-ZONE1`, `CP-ZONE2`, `CP-ZONE3`

**What to check:** Green success message showing the generated FID.

Register a second franchise too (e.g. `Adani ChargeZone` / `AD-SOUTH` / `adani@pass456` / `75000`).

---

## Step 2: Register an EV Owner (User Device — port 5002)

Open http://localhost:5002 in the browser.

Go to the **Register** tab and fill in:

| Field           | Example Input |
| --------------- | ------------- |
| Name            | `Arjun Mehta` |
| Zone Code       | `TP-NORTH`    |
| Password        | `arjun@pw1`   |
| 4-digit PIN     | `1234`        |
| Mobile Number   | `9876543210`  |
| Initial Balance | `3000`        |

Click **Register with Grid**.

**What to check:** Green success message showing UID and VMID. The device stores this user locally.

Go to the **My Account** tab to see the registered user and their balance.

Register a second user too (e.g. `Priya Sharma` / `AD-SOUTH` / `priya@pw2` / `5678` / `9123456789` / `5000`).

---

## Step 3: Generate a QR Code (Charging Kiosk — port 5001)

Open http://localhost:5001 in the browser.

In the **Generate QR Code** panel:

1. Select a franchise from the dropdown (fetched from Grid Authority)
2. Click **Encrypt FID & Generate QR**

**What to check:**

- Success message showing the session ID and encrypted VFID
- The **Active QR Sessions** table on the right updates with the new session
- In the terminal, ASCON encryption details are printed (nonce, ciphertext, auth tag)
- A QR code image is saved in the `qr_codes/` folder

Repeat for each franchise you registered.

---

## Step 4: Initiate a Charging Session (User Device — port 5002)

Go back to http://localhost:5002 and click the **Charge** tab.

1. **QR Session** — Select the franchise QR session (fetched from Kiosk). Click Refresh if it's empty.
2. **Select Your Account** — Pick the user you registered
3. **PIN** — Enter the PIN from registration (e.g. `1234`)
4. **Amount** — Enter charging amount (e.g. `500`)

Click **Pay & Start Charging**.

**What to check (successful transaction):**

- Green success message with block number, transaction ID, and remaining balance
- In Kiosk terminal: QR decryption via ASCON, forwarding to Grid
- In Grid terminal: Transaction processing and blockchain recording

### Test: Wrong PIN

Repeat but enter `0000` as PIN.

**What to check:** Red error "Invalid PIN."

### Test: Insufficient Balance

Repeat with an amount higher than the user's balance (e.g. `10000`).

**What to check:** Red error "Insufficient balance."

---

## Step 5: View the Blockchain (Grid Authority — port 5000)

Go to http://localhost:5000 and click the **Blockchain** tab.

Click **Refresh** to load the latest blocks.

**What to check:**

- Genesis block (Block #0) plus one block per successful transaction
- Each block shows transaction ID, timestamp, amount, previous hash, and block hash
- If a hardware failure occurred (10% random chance), a DISPUTE/REFUND block appears

Click **Validate Integrity** to verify the chain.

**What to check:** "Blockchain integrity verified. All blocks are valid."

---

## Step 6: View Balances (Grid Authority — port 5000)

Click the **Balances** tab and click **Refresh**.

**What to check:**

- User balance decreased by the charged amount (e.g. Arjun: 3000 - 500 = 2500)
- Franchise balance increased by the charged amount (e.g. Tata: 50000 + 500 = 50500)

Also check the **My Account** tab on the User Device (port 5002) — the balance should match.

---

## Step 7: Shor's Algorithm (Grid Authority — port 5000)

Click the **Shor's Attack** tab.

Click **Run Shor's Algorithm**.

**What to check:**

- RSA public key (e, n) displayed
- Factors found by Shor's algorithm
- Private key recovered and matched against original
- "RSA broken!" warning confirming the quantum vulnerability

---

## Step 8: Check Registered Entities (Grid Authority — port 5000)

Click the **Registered Entities** tab.

**What to check:** All franchises and users you registered are listed with their IDs and status.

---

## Data Flow Summary

```
User Device (5002)  ──registers──>  Grid Authority (5000)
                                          |
Kiosk (5001)  ──fetches franchises──>  Grid Authority (5000)
Kiosk (5001)  ──encrypts FID with ASCON, generates QR──>  (local)
                                          |
User Device (5002)  ──scans QR, sends to──>  Kiosk (5001)
                                          |
Kiosk (5001)  ──decrypts QR, forwards──>  Grid Authority (5000)
                                          |
Grid Authority  ──validates PIN, transfers funds, records block──>  Blockchain
```

---

## Quick Walkthrough (Minimum Steps)

1. Start all three apps in separate terminals
2. **Grid (5000):** Register franchise — Tata EV Hub / TP-NORTH / tata@secure123 / 50000
3. **Device (5002):** Register user — Arjun Mehta / TP-NORTH / arjun@pw1 / 1234 / 9876543210 / 3000
4. **Kiosk (5001):** Generate QR for Tata EV Hub
5. **Device (5002):** Charge tab — Select QR, select Arjun, PIN 1234, amount 500
6. **Grid (5000):** Blockchain tab — See the new transaction block
7. **Grid (5000):** Balances tab — Arjun: 2500, Tata: 50500
8. **Device (5002):** Try wrong PIN (0000) — see rejection
9. **Grid (5000):** Validate Integrity — should pass
10. **Grid (5000):** Run Shor's Algorithm — see RSA broken
