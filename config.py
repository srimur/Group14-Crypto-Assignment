# Energy providers and their zone codes
ENERGY_PROVIDERS = {
    "Tata Power": ["TP-NORTH", "TP-SOUTH", "TP-WEST"],
    "Adani": ["AD-NORTH", "AD-SOUTH", "AD-EAST"],
    "ChargePoint": ["CP-ZONE1", "CP-ZONE2", "CP-ZONE3"],
}

VALID_ZONE_CODES = []
for provider, zones in ENERGY_PROVIDERS.items():
    VALID_ZONE_CODES.extend(zones)

# ASCON-128 symmetric key (128-bit)
ASCON_KEY = bytes.fromhex("000102030405060708090a0b0c0d0e0f")
ASCON_NONCE_SIZE = 16

# Small key size so Shor's simulation can factor it in reasonable time
RSA_KEY_BITS = 20

# Price per kWh in ₹
ENERGY_RATE = 12.0

# Probability of simulated hardware failure for dispute handling
HARDWARE_FAILURE_PROBABILITY = 0.1

QR_CODE_DIR = "qr_codes"
