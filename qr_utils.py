import os

try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("[QR] Warning: qrcode library not installed. "
          "QR images won't be generated. Install with: pip install qrcode[pil]")



def generate_qr_code(data: str, filepath: str) -> str:
    if not QR_AVAILABLE:
        print(f"[QR] QR library not available. Data: {data[:50]}...")
        txt_path = filepath.replace(".png", ".txt")
        with open(txt_path, "w") as f:
            f.write(data)
        print(f"[QR] Saved QR data as text: {txt_path}")
        return txt_path

    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        img.save(filepath)
        return filepath

    except Exception as e:
        print(f"[QR] Error generating QR code: {e}")
        txt_path = filepath.replace(".png", ".txt")
        with open(txt_path, "w") as f:
            f.write(data)
        return txt_path



def decode_qr_data(qr_data: str) -> dict:
    try:
        parts = qr_data.split("|")
        if len(parts) != 4:
            return None
        return {
            "session_id": parts[0],
            "ciphertext_hex": parts[1],
            "tag_hex": parts[2],
            "associated_data_hex": parts[3],
        }
    except Exception:
        return None
