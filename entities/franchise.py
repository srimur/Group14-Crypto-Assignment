class Franchise:

    def __init__(self, name: str, zone_code: str, password: str,
                 initial_balance: float = 10000.0):
        self.name = name
        self.zone_code = zone_code
        self.password = password
        self.initial_balance = initial_balance
        self.fid = None

    def register(self, grid) -> dict:
        result = grid.register_franchise(
            name=self.name,
            zone_code=self.zone_code,
            password=self.password,
            initial_balance=self.initial_balance,
        )
        if result["success"]:
            self.fid = result["fid"]
            print(f"[Franchise] '{self.name}' registered. FID: {self.fid}")
        else:
            print(f"[Franchise] Registration failed: {result['error']}")
        return result

    def receive_confirmation(self, result: dict):
        if result["success"]:
            print(f"[Franchise] ✓ Payment received from {result['user_name']}. "
                  f"New balance: ₹{result['franchise_balance']:.2f}")
            print(f"[Franchise] Unlocking charging cable...")
        elif result.get("refund"):
            print(f"[Franchise] ⚠ Hardware failure! Refund issued. "
                  f"Transaction voided.")
        else:
            print(f"[Franchise] ✗ Transaction failed: {result['error']}")
