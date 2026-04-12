import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from entities.grid_authority import GridAuthority
from entities.franchise import Franchise
from entities.ev_owner import EVOwner
from entities.charging_kiosk import ChargingKiosk
from crypto_utils.shor_simulation import demo_shor_attack
from config import ENERGY_PROVIDERS, VALID_ZONE_CODES


def print_banner():
    print("\n" + "=" * 60)
    print("  SECURE CENTRALIZED EV CHARGING PAYMENT GATEWAY")
    print("  Post-Quantum & Lightweight Cryptography")
    print("  BITS F463 — Cryptography Term Project 2025-26")
    print("=" * 60)


def print_menu():
    print("\n" + "-" * 50)
    print("  MAIN MENU")
    print("-" * 50)
    print("  1. Register Franchise")
    print("  2. Register EV Owner")
    print("  3. Generate QR Code (Kiosk)")
    print("  4. Initiate Charging Session (EV Owner)")
    print("  5. View Blockchain Ledger")
    print("  6. View Account Balances")
    print("  7. Demonstrate Shor's Algorithm (Quantum Attack)")
    print("  8. Validate Blockchain Integrity")
    print("  9. Run Full Demo (Auto)")
    print("  0. Exit")
    print("-" * 50)


def print_zones():
    print("\n  Available Energy Providers & Zones:")
    for provider, zones in ENERGY_PROVIDERS.items():
        print(f"    {provider}: {', '.join(zones)}")


# Prompt user for franchise details and register with the grid
def register_franchise_interactive(grid):
    print("\n--- Register Franchise ---")
    print_zones()
    name = input("  Franchise name: ").strip()
    zone = input("  Zone code: ").strip()
    password = input("  Password: ").strip()
    try:
        balance = float(input("  Initial balance (₹): ").strip())
    except ValueError:
        balance = 10000.0
        print(f"  (Using default balance: ₹{balance})")

    franchise = Franchise(name, zone, password, balance)
    result = franchise.register(grid)
    return franchise if result["success"] else None


# Prompt user for EV owner details and register with the grid
def register_user_interactive(grid):
    print("\n--- Register EV Owner ---")
    print_zones()
    name = input("  Name: ").strip()
    zone = input("  Zone code: ").strip()
    password = input("  Password: ").strip()
    pin = input("  4-digit PIN: ").strip()
    mobile = input("  Mobile number: ").strip()
    try:
        balance = float(input("  Initial balance (₹): ").strip())
    except ValueError:
        balance = 5000.0
        print(f"  (Using default balance: ₹{balance})")

    user = EVOwner(name, zone, password, pin, mobile, balance)
    result = user.register(grid)
    return user if result["success"] else None


# Let user pick a franchise and generate an ASCON-encrypted QR code for it
def generate_qr_interactive(kiosk, grid):
    print("\n--- Generate QR Code ---")

    if not grid.franchises:
        print("  No franchises registered. Register one first.")
        return None

    print("  Registered Franchises:")
    fid_list = list(grid.franchises.keys())
    for i, fid in enumerate(fid_list):
        f = grid.franchises[fid]
        print(f"    [{i+1}] {f['name']} ({f['zone_code']}) — FID: {fid}")

    try:
        choice = int(input("  Select franchise number: ").strip()) - 1
        fid = fid_list[choice]
    except (ValueError, IndexError):
        print("  Invalid selection.")
        return None

    franchise = grid.franchises[fid]
    result = kiosk.generate_vfid_and_qr(fid, franchise["name"])
    print(f"\n  ✓ QR code generated: {result['qr_path']}")
    print(f"  VFID (encrypted): {result['vfid']}")
    return result


# Walk the user through selecting a QR session, user, and amount to charge
def initiate_session_interactive(kiosk, grid, qr_sessions):
    print("\n--- Initiate Charging Session ---")

    if not qr_sessions:
        print("  No QR codes generated. Generate one first (Option 3).")
        return None

    if not grid.users:
        print("  No users registered. Register one first (Option 2).")
        return None

    print("  Available QR Sessions:")
    session_list = list(qr_sessions.items())
    for i, (sid, sdata) in enumerate(session_list):
        fid = kiosk.active_sessions.get(sdata["session_id"], {}).get("fid", "?")
        fname = grid.franchises.get(fid, {}).get("name", "Unknown")
        print(f"    [{i+1}] Franchise: {fname} (Session: {sdata['session_id'][:16]}...)")

    try:
        qr_choice = int(input("  Select QR session: ").strip()) - 1
        qr_data = session_list[qr_choice][1]["qr_data"]
    except (ValueError, IndexError):
        print("  Invalid selection.")
        return None

    print("\n  Registered Users:")
    uid_list = list(grid.users.keys())
    for i, uid in enumerate(uid_list):
        u = grid.users[uid]
        print(f"    [{i+1}] {u['name']} — VMID: {u['vmid']} — Balance: ₹{u['balance']:.2f}")

    try:
        user_choice = int(input("  Select user: ").strip()) - 1
        uid = uid_list[user_choice]
    except (ValueError, IndexError):
        print("  Invalid selection.")
        return None

    user_data = grid.users[uid]
    pin = input(f"  Enter PIN for {user_data['name']}: ").strip()
    try:
        amount = float(input("  Charging amount (₹): ").strip())
    except ValueError:
        print("  Invalid amount.")
        return None

    ev_owner = EVOwner(
        user_data["name"], user_data["zone_code"], "",
        pin, user_data["mobile"]
    )
    ev_owner.uid = uid
    ev_owner.vmid = user_data["vmid"]

    result = ev_owner.initiate_session(qr_data, amount, kiosk, grid)
    return result


# Run end-to-end automated demo: register, generate QRs, transact, validate
def run_full_demo(grid, kiosk):
    print("\n" + "=" * 60)
    print("  RUNNING FULL AUTOMATED DEMO")
    print("=" * 60)

    print("\n\n▶ STEP 1: Registering Franchises...")
    print("-" * 40)

    f1 = Franchise("Tata EV Hub", "TP-NORTH", "tata@secure123", 50000.0)
    f1.register(grid)

    f2 = Franchise("Adani ChargeZone", "AD-SOUTH", "adani@pass456", 75000.0)
    f2.register(grid)

    f3 = Franchise("ChargePoint Express", "CP-ZONE1", "cp@key789", 60000.0)
    f3.register(grid)

    print("\n\n▶ STEP 2: Registering EV Owners...")
    print("-" * 40)

    u1 = EVOwner("Arjun Mehta", "TP-NORTH", "arjun@pw1", "1234", "9876543210", 3000.0)
    u1.register(grid)

    u2 = EVOwner("Priya Sharma", "AD-SOUTH", "priya@pw2", "5678", "9123456789", 5000.0)
    u2.register(grid)

    u3 = EVOwner("Rahul Verma", "CP-ZONE1", "rahul@pw3", "9999", "9988776655", 1500.0)
    u3.register(grid)

    print("\n\n▶ STEP 3: Generating QR Codes at Kiosks...")
    print("-" * 40)

    qr1 = kiosk.generate_vfid_and_qr(f1.fid, f1.name)
    qr2 = kiosk.generate_vfid_and_qr(f2.fid, f2.name)
    qr3 = kiosk.generate_vfid_and_qr(f3.fid, f3.name)

    print("\n\n▶ STEP 4: Initiating Charging Sessions...")
    print("-" * 40)

    print("\n--- Session 1: Arjun at Tata EV Hub ---")
    r1 = u1.initiate_session(qr1["qr_data"], 500.0, kiosk, grid)

    print("\n--- Session 2: Priya at Adani ChargeZone ---")
    r2 = u2.initiate_session(qr2["qr_data"], 800.0, kiosk, grid)

    print("\n--- Session 3: Rahul at ChargePoint (₹2000, balance ₹1500) ---")
    r3 = u3.initiate_session(qr3["qr_data"], 2000.0, kiosk, grid)

    print("\n--- Session 4: Arjun with wrong PIN ---")
    u1_wrong = EVOwner("Arjun Mehta", "TP-NORTH", "", "0000", "9876543210")
    u1_wrong.uid = u1.uid
    u1_wrong.vmid = u1.vmid
    r4 = u1_wrong.initiate_session(qr1["qr_data"], 100.0, kiosk, grid)

    print("\n--- Session 5: Rahul at ChargePoint (₹500) ---")
    r5 = u3.initiate_session(qr3["qr_data"], 500.0, kiosk, grid)

    print("\n\n▶ STEP 5: Blockchain Ledger")
    print("-" * 40)
    grid.blockchain.display_chain()

    print("\n\n▶ STEP 6: Account Balances")
    print("-" * 40)
    grid.display_balances()

    print("\n\n▶ STEP 7: Blockchain Validation")
    print("-" * 40)
    is_valid, msg = grid.blockchain.validate_chain()
    print(f"  {msg}")

    print("\n\n▶ STEP 8: Quantum Attack — Shor's Algorithm")
    print("-" * 40)
    demo_shor_attack(grid.get_rsa_keys())

    print("\n" + "=" * 60)
    print("  DEMO COMPLETE")
    print("=" * 60)


def main():
    print_banner()

    grid = GridAuthority()
    kiosk = ChargingKiosk()
    qr_sessions = {}
    franchises = []
    users = []

    while True:
        print_menu()
        choice = input("  Enter choice: ").strip()

        if choice == "1":
            f = register_franchise_interactive(grid)
            if f:
                franchises.append(f)

        elif choice == "2":
            u = register_user_interactive(grid)
            if u:
                users.append(u)

        elif choice == "3":
            result = generate_qr_interactive(kiosk, grid)
            if result:
                qr_sessions[result["session_id"]] = result

        elif choice == "4":
            initiate_session_interactive(kiosk, grid, qr_sessions)

        elif choice == "5":
            grid.blockchain.display_chain()

        elif choice == "6":
            grid.display_balances()

        elif choice == "7":
            print("\n--- Shor's Algorithm Demonstration ---")
            demo_shor_attack(grid.get_rsa_keys())

        elif choice == "8":
            is_valid, msg = grid.blockchain.validate_chain()
            print(f"\n  Blockchain Validation: {msg}")

        elif choice == "9":
            run_full_demo(grid, kiosk)

        elif choice == "0":
            print("\n  Goodbye!")
            break

        else:
            print("  Invalid choice. Try again.")


if __name__ == "__main__":
    main()
