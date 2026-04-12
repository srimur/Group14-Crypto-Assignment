from crypto_utils.rsa_utils import rsa_encrypt, string_to_int
from crypto_utils.sha3_utils import sha3_hash


# Represents an EV driver who scans QR codes and initiates charging sessions
class EVOwner:

    def __init__(self, name: str, zone_code: str, password: str,
                 pin: str, mobile: str, initial_balance: float = 5000.0):
        self.name = name
        self.zone_code = zone_code
        self.password = password
        self.pin = pin
        self.mobile = mobile
        self.initial_balance = initial_balance
        self.uid = None
        self.vmid = None

    # Register this EV owner with the Grid Authority
    def register(self, grid) -> dict:
        result = grid.register_user(
            name=self.name,
            zone_code=self.zone_code,
            password=self.password,
            pin=self.pin,
            mobile=self.mobile,
            initial_balance=self.initial_balance,
        )
        if result["success"]:
            self.uid = result["uid"]
            self.vmid = result["vmid"]
            print(f"[User] '{self.name}' registered. UID: {self.uid} | VMID: {self.vmid}")
        else:
            print(f"[User] Registration failed: {result['error']}")
        return result

    # Scan QR, encrypt credentials with RSA, and send charging request via kiosk
    def initiate_session(self, qr_data: str, amount: float, kiosk, grid) -> dict:
        print(f"\n[User] {self.name} scanning QR code...")
        print(f"[User] Providing VMID: {self.vmid}")
        print(f"[User] Requesting charge: ₹{amount:.2f}")

        public_key = grid.get_public_key()
        e, n = public_key

        pin_int = int(self.pin) % n
        vmid_int = int(self.vmid, 16) % n

        encrypted_pin = rsa_encrypt(pin_int, public_key)
        encrypted_vmid = rsa_encrypt(vmid_int, public_key)

        print(f"[User] PIN encrypted with RSA: {encrypted_pin}")
        print(f"[User] VMID encrypted with RSA: {encrypted_vmid}")

        result = kiosk.process_session(
            qr_data=qr_data,
            vmid=self.vmid,
            pin=self.pin,
            amount=amount,
            grid=grid,
        )

        if result["success"]:
            print(f"[User] ✓ Charging session approved! "
                  f"Remaining balance: ₹{result['user_balance']:.2f}")
        elif result.get("refund"):
            print(f"[User] ⚠ Payment was made but hardware failed. "
                  f"Refund issued. Balance: ₹{result['user_balance']:.2f}")
        else:
            print(f"[User] ✗ Session denied: {result['error']}")

        return result

    def receive_confirmation(self, result: dict):
        if result["success"]:
            print(f"[User] Session status: APPROVED — Charging started.")
        else:
            print(f"[User] Session status: DENIED — {result.get('error', 'Unknown')}")
