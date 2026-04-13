import time
import random
from crypto_utils.sha3_utils import generate_id, sha3_hash
from crypto_utils.rsa_utils import generate_rsa_keypair, rsa_encrypt, rsa_decrypt
from blockchain.ledger import Blockchain
from config import VALID_ZONE_CODES, ENERGY_PROVIDERS, HARDWARE_FAILURE_PROBABILITY, RSA_KEY_BITS


class GridAuthority:

    def __init__(self):
        self.franchises = {}
        self.users = {}
        self.blockchain = Blockchain()
        self.rsa_keys = generate_rsa_keypair(RSA_KEY_BITS)

        print("[Grid] Grid Authority initialized.")
        print(f"[Grid] RSA Public Key: e={self.rsa_keys['public'][0]}, n={self.rsa_keys['public'][1]}")
        print(f"[Grid] Energy Providers: {', '.join(ENERGY_PROVIDERS.keys())}")

    def get_public_key(self) -> tuple:
        return self.rsa_keys["public"]

    def get_rsa_keys(self) -> dict:
        return self.rsa_keys

    def register_franchise(self, name: str, zone_code: str,
                           password: str, initial_balance: float) -> dict:
        if zone_code not in VALID_ZONE_CODES:
            return {"success": False, "error": f"Invalid zone code: {zone_code}. "
                    f"Valid codes: {VALID_ZONE_CODES}"}

        for fdata in self.franchises.values():
            if fdata["name"] == name and fdata["zone_code"] == zone_code:
                return {"success": False, "error": "Franchise already registered in this zone."}

        timestamp = time.time()
        fid = generate_id(name, password, timestamp)
        password_hash = sha3_hash(password)

        self.franchises[fid] = {
            "name": name,
            "zone_code": zone_code,
            "password_hash": password_hash,
            "balance": initial_balance,
            "fid": fid,
            "created_at": timestamp,
            "active": True,
        }

        provider = "Unknown"
        for p, zones in ENERGY_PROVIDERS.items():
            if zone_code in zones:
                provider = p
                break

        print(f"[Grid] Franchise registered: {name} | Zone: {zone_code} | "
              f"Provider: {provider} | FID: {fid}")

        return {
            "success": True,
            "fid": fid,
            "name": name,
            "zone_code": zone_code,
            "provider": provider,
            "balance": initial_balance,
        }

    def register_user(self, name: str, zone_code: str, password: str,
                      pin: str, mobile: str, initial_balance: float) -> dict:
        if zone_code not in VALID_ZONE_CODES:
            return {"success": False, "error": f"Invalid zone code: {zone_code}"}

        if len(pin) != 4 or not pin.isdigit():
            return {"success": False, "error": "PIN must be a 4-digit number."}

        for udata in self.users.values():
            if udata["name"] == name and udata["zone_code"] == zone_code:
                return {"success": False, "error": "User already registered in this zone."}

        timestamp = time.time()
        uid = generate_id(name, password, timestamp)
        password_hash = sha3_hash(password)
        pin_hash = sha3_hash(pin)

        vmid = sha3_hash(uid + mobile)[:16]

        self.users[uid] = {
            "name": name,
            "zone_code": zone_code,
            "password_hash": password_hash,
            "pin_hash": pin_hash,
            "mobile": mobile,
            "uid": uid,
            "vmid": vmid,
            "balance": initial_balance,
            "created_at": timestamp,
            "active": True,
        }

        print(f"[Grid] User registered: {name} | Zone: {zone_code} | "
              f"UID: {uid} | VMID: {vmid}")

        return {
            "success": True,
            "uid": uid,
            "vmid": vmid,
            "name": name,
            "zone_code": zone_code,
            "balance": initial_balance,
        }

    def process_transaction(self, fid: str, vmid: str, pin: str,
                            amount: float) -> dict:
        if fid not in self.franchises:
            return {"success": False, "error": "Franchise not found."}

        franchise = self.franchises[fid]
        if not franchise["active"]:
            return {"success": False, "error": "Franchise account is inactive."}

        user = None
        uid = None
        for u_id, u_data in self.users.items():
            if u_data["vmid"] == vmid:
                user = u_data
                uid = u_id
                break

        if user is None:
            return {"success": False, "error": "Invalid VMID. User not found."}

        if not user["active"]:
            return {"success": False, "error": "User account is inactive."}

        if sha3_hash(pin) != user["pin_hash"]:
            return {"success": False, "error": "Invalid PIN."}

        if user["balance"] < amount:
            return {"success": False,
                    "error": f"Insufficient balance. Available: ₹{user['balance']:.2f}, "
                             f"Required: ₹{amount:.2f}"}

        user["balance"] -= amount
        franchise["balance"] += amount

        block = self.blockchain.add_transaction(
            uid=uid,
            fid=fid,
            amount=amount,
            description=f"Charging session: {user['name']} at {franchise['name']}",
            dispute=False,
        )

        print(f"[Grid] Transaction successful: {user['name']} → {franchise['name']} "
              f"| ₹{amount:.2f} | Block #{block.index}")

        if random.random() < HARDWARE_FAILURE_PROBABILITY:
            print(f"[Grid] ⚠ HARDWARE FAILURE detected at {franchise['name']}!")
            print(f"[Grid] Initiating dispute/refund...")

            user["balance"] += amount
            franchise["balance"] -= amount

            refund_block = self.blockchain.add_transaction(
                uid=uid,
                fid=fid,
                amount=-amount,
                description=f"REFUND: Hardware failure at {franchise['name']}",
                dispute=True,
            )

            print(f"[Grid] Refund processed. Dispute Block #{refund_block.index}")

            return {
                "success": False,
                "error": "Hardware failure at charging station. Refund issued.",
                "refund": True,
                "block_index": block.index,
                "refund_block_index": refund_block.index,
                "user_balance": user["balance"],
            }

        return {
            "success": True,
            "block_index": block.index,
            "transaction_id": block.transaction_id,
            "user_balance": user["balance"],
            "franchise_balance": franchise["balance"],
            "user_name": user["name"],
            "franchise_name": franchise["name"],
        }

    def get_franchise(self, fid: str) -> dict:
        return self.franchises.get(fid)

    def get_user_by_vmid(self, vmid: str) -> dict:
        for uid, udata in self.users.items():
            if udata["vmid"] == vmid:
                return udata
        return None

    def display_balances(self):
        print(f"\n{'='*60}")
        print("  ACCOUNT BALANCES")
        print(f"{'='*60}")

        print("\n  Franchises:")
        if not self.franchises:
            print("    (none registered)")
        for fid, f in self.franchises.items():
            status = "Active" if f["active"] else "INACTIVE"
            print(f"    {f['name']} [{f['zone_code']}] — ₹{f['balance']:.2f} ({status})")

        print("\n  Users:")
        if not self.users:
            print("    (none registered)")
        for uid, u in self.users.items():
            status = "Active" if u["active"] else "INACTIVE"
            print(f"    {u['name']} [{u['zone_code']}] — ₹{u['balance']:.2f} ({status})")

        print(f"\n{'='*60}")
