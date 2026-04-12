import os
import time
from crypto_utils.ascon import ascon_encrypt, ascon_decrypt, generate_nonce
from crypto_utils.sha3_utils import sha3_hash
from config import ASCON_KEY, QR_CODE_DIR
from qr_utils import generate_qr_code, decode_qr_data


# Intermediary between EV Owner, Franchise, and Grid — handles QR encryption and session relay
class ChargingKiosk:

    def __init__(self):
        self.ascon_key = ASCON_KEY
        self.active_sessions = {}
        os.makedirs(QR_CODE_DIR, exist_ok=True)

        print("[Kiosk] Charging Kiosk initialized.")

    # Encrypt FID with ASCON-128 and generate a QR code containing the encrypted payload
    def generate_vfid_and_qr(self, fid: str, franchise_name: str = "") -> dict:
        nonce = generate_nonce()
        associated_data = f"EV-KIOSK-{int(time.time())}".encode("utf-8")

        plaintext = fid.encode("utf-8")
        ciphertext, tag = ascon_encrypt(
            key=self.ascon_key,
            nonce=nonce,
            plaintext=plaintext,
            associated_data=associated_data,
        )

        session_id = nonce.hex()
        self.active_sessions[session_id] = {
            "fid": fid,
            "nonce": nonce,
            "tag": tag,
            "ciphertext": ciphertext,
            "associated_data": associated_data,
            "timestamp": time.time(),
        }

        qr_payload = (
            f"{session_id}|"
            f"{ciphertext.hex()}|"
            f"{tag.hex()}|"
            f"{associated_data.hex()}"
        )

        safe_name = franchise_name.replace(" ", "_") if franchise_name else fid[:8]
        qr_path = os.path.join(QR_CODE_DIR, f"kiosk_{safe_name}.png")
        generate_qr_code(qr_payload, qr_path)

        print(f"\n[Kiosk] ASCON Encryption Details:")
        print(f"  FID (plaintext) : {fid}")
        print(f"  Nonce           : {nonce.hex()}")
        print(f"  Ciphertext      : {ciphertext.hex()}")
        print(f"  Auth Tag        : {tag.hex()}")
        print(f"  QR Code saved   : {qr_path}")

        return {
            "qr_data": qr_payload,
            "qr_path": qr_path,
            "session_id": session_id,
            "vfid": ciphertext.hex(),
        }

    # Decrypt QR payload to recover the original Franchise ID
    def decrypt_qr(self, qr_data: str) -> str:
        try:
            parts = qr_data.split("|")
            if len(parts) != 4:
                print("[Kiosk] Invalid QR data format.")
                return None

            session_id = parts[0]
            ciphertext = bytes.fromhex(parts[1])
            tag = bytes.fromhex(parts[2])
            associated_data = bytes.fromhex(parts[3])

            if session_id not in self.active_sessions:
                print("[Kiosk] Unknown session. QR may be expired or invalid.")
                return None

            session = self.active_sessions[session_id]
            nonce = session["nonce"]

            plaintext = ascon_decrypt(
                key=self.ascon_key,
                nonce=nonce,
                ciphertext=ciphertext,
                tag=tag,
                associated_data=associated_data,
            )

            fid = plaintext.decode("utf-8")
            print(f"[Kiosk] QR decrypted. FID recovered: {fid}")
            return fid

        except ValueError as e:
            print(f"[Kiosk] ASCON decryption failed: {e}")
            return None
        except Exception as e:
            print(f"[Kiosk] QR decryption error: {e}")
            return None

    # Decrypt QR, forward auth request to Grid, and relay the result
    def process_session(self, qr_data: str, vmid: str, pin: str,
                        amount: float, grid) -> dict:
        print(f"\n[Kiosk] Processing charging session...")
        print(f"[Kiosk] VMID: {vmid} | Amount: ₹{amount:.2f}")

        fid = self.decrypt_qr(qr_data)
        if fid is None:
            return {"success": False, "error": "Failed to decrypt QR code."}

        print(f"[Kiosk] Sending auth request to Grid Authority...")
        result = grid.process_transaction(
            fid=fid,
            vmid=vmid,
            pin=pin,
            amount=amount,
        )

        if result["success"]:
            print(f"[Kiosk] ✓ Grid approved. Notifying user and franchise.")
        elif result.get("refund"):
            print(f"[Kiosk] ⚠ Hardware failure! Refund processed.")
        else:
            print(f"[Kiosk] ✗ Grid rejected: {result['error']}")

        return result
